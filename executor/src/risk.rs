// --- Risk Management Guards -------------------------------------------------
//
// 1. Equity Floor – kill-switch if account equity drops below a Redis-configured
//    threshold (default 300 USDC).
// 2. Slippage Sentinel – kill-switch if realised trade slippage breaches an
//    adaptive tail threshold based on a 20-period EMA of volatility.
// 3. Portfolio Stop-Loss - kill-switch if total portfolio value drops by a
//    configured percentage from its peak.
// ---------------------------------------------------------------------------

use anyhow::{anyhow, Result};
use once_cell::sync::Lazy;
use solana_client::rpc_client::RpcClient;
use solana_sdk::signature::read_keypair_file;
use solana_sdk::signer::Signer;
use std::sync::atomic::{AtomicU64, Ordering};
use tokio::sync::{broadcast::Sender, mpsc::Receiver};
use tokio::time::{sleep, Duration};

use crate::metrics::{
    set_risk_equity_usdc, set_risk_last_slippage, set_risk_portfolio_stop_loss,
    set_risk_slippage_threshold,
};

const LAMPORTS_PER_USDC: f64 = 1_000_000.0;

/// Returns the RPC URL to use (defaults to Solana devnet).
/// Temporary fix: Added better fallback handling for CLI scenarios.
fn rpc_url() -> String {
    // Try multiple environment variables for compatibility
    std::env::var("SOLANA_RPC_URL")
        .or_else(|_| std::env::var("SOLANA_URL"))
        .or_else(|_| std::env::var("RPC_URL"))
        .unwrap_or_else(|_| {
            // Check if we're running in test/local mode
            if std::env::var("RUST_TEST").is_ok() || std::env::var("CARGO_PKG_NAME").is_ok() {
                "http://127.0.0.1:8899".to_string()
            } else {
                "https://api.devnet.solana.com".to_string()
            }
        })
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum KillSwitch {
    EquityFloor,
    Slippage,
    PortfolioStopLoss,
}

// ---------------------------------------------------------------------------
// Balance mocking (unit-tests) ----------------------------------------------
// ---------------------------------------------------------------------------
static BALANCE_OVERRIDE_CENTS: Lazy<AtomicU64> = Lazy::new(|| AtomicU64::new(u64::MAX));

/// Inject a deterministic balance for tests.  Value is cleared only on
/// process exit which is fine for our short-lived test harness.
pub fn _set_mock_balance_usdc(usdc: f64) {
    BALANCE_OVERRIDE_CENTS.store((usdc * 100.0) as u64, Ordering::Relaxed);
}

pub async fn get_balance_usdc() -> Result<f64> {
    // Test override takes priority.
    if let Some(v) = {
        let raw = BALANCE_OVERRIDE_CENTS.load(Ordering::Relaxed);
        (raw != u64::MAX).then(|| raw as f64 / 100.0)
    } {
        return Ok(v);
    }

    // Fallback to on-chain balance via RPC.
    let path = std::env::var("KEYPAIR_PATH").map_err(|_| anyhow!("KEYPAIR_PATH not set"))?;

    let rpc_url = rpc_url();
    let lamports = tokio::task::spawn_blocking(move || {
        let kp = read_keypair_file(path).map_err(|e| anyhow!(e.to_string()))?;
        let rpc = RpcClient::new(rpc_url);
        rpc.get_balance(&kp.pubkey())
            .map_err(|e| anyhow!(e.to_string()))
    })
    .await??;

    Ok(lamports as f64 / LAMPORTS_PER_USDC)
}

// ---------------------------------------------------------------------------
// Redis helpers -------------------------------------------------------------
// ---------------------------------------------------------------------------

async fn redis_f64(key: &str) -> Option<f64> {
    let url = std::env::var("REDIS_URL").unwrap_or_else(|_| {
        panic!("REDIS_URL not set – refusing to start (risk module)");
    });

    if let Ok(client) = redis::Client::open(url) {
        if let Ok(mut conn) = client.get_async_connection().await {
            let res: redis::RedisResult<Option<String>> = redis::Cmd::new()
                .arg("GET")
                .arg(key)
                .query_async(&mut conn)
                .await;
            if let Ok(Some(s)) = res {
                return s.parse::<f64>().ok();
            }
        }
    }
    None
}

// ---------------------------------------------------------------------------
// Public entry-point --------------------------------------------------------
// ---------------------------------------------------------------------------

/// Spawns the equity-floor and slippage sentinels.  Returns immediately – the
/// inner tasks run for the lifetime of the executor process.
pub async fn run(kill_tx: Sender<KillSwitch>, mut slippage_rx: Receiver<f64>) -> Result<()> {
    let poll_ms: u64 = std::env::var("RISK_EQUITY_POLL_MS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(5000); // Poll every 5 seconds

    //--------------------------------------------------
    // Equity-floor guard
    //--------------------------------------------------
    let kill_tx_eq = kill_tx.clone();
    tokio::spawn(async move {
        let mut floor = redis_f64("risk:equity_floor").await.unwrap_or(300.0);

        loop {
            match get_balance_usdc().await {
                Ok(bal) => {
                    set_risk_equity_usdc(bal);
                    if bal < floor {
                        let _ = kill_tx_eq.send(KillSwitch::EquityFloor);
                    }
                }
                Err(e) => {
                    tracing::warn!(target = "risk", "balance fetch error (equity floor): {e}");
                }
            }

            // Opportunistically refresh floor each tick.
            if let Some(f) = redis_f64("risk:equity_floor").await {
                floor = f;
            }

            sleep(Duration::from_millis(poll_ms)).await;
        }
    });

    //--------------------------------------------------
    // Portfolio Stop-Loss guard
    //--------------------------------------------------
    let kill_tx_sl = kill_tx.clone();
    tokio::spawn(async move {
        let stop_loss_percent = std::env::var("PORTFOLIO_STOP_LOSS_PERCENT")
            .ok()
            .and_then(|v| v.parse::<f64>().ok())
            .unwrap_or(25.0); // Default to 25%

        let mut peak_equity: f64 = 0.0;
        let mut initialized = false;

        loop {
            match get_balance_usdc().await {
                Ok(bal) => {
                    if !initialized {
                        peak_equity = bal;
                        initialized = true;
                        tracing::info!(target = "risk", "Initialized portfolio peak equity at {:.2} USDC", peak_equity);
                    } else {
                        peak_equity = peak_equity.max(bal);
                    }

                    let stop_loss_level =
                        peak_equity * (1.0 - (stop_loss_percent / 100.0));

                    set_risk_portfolio_stop_loss(stop_loss_level);

                    if bal < stop_loss_level {
                        tracing::error!(
                            target = "risk",
                            "PORTFOLIO STOP-LOSS TRIGGERED! Current equity {:.2} < stop-loss level {:.2} (peak: {:.2})",
                            bal, stop_loss_level, peak_equity
                        );
                        let _ = kill_tx_sl.send(KillSwitch::PortfolioStopLoss);
                        // Stop this task after triggering
                        break;
                    }
                }
                Err(e) => {
                    tracing::warn!(target = "risk", "balance fetch error (stop-loss): {e}");
                }
            }
            sleep(Duration::from_millis(poll_ms)).await;
        }
    });

    //--------------------------------------------------
    // Slippage sentinel
    //--------------------------------------------------
    tokio::spawn(async move {
        // EMA parameters – 20-period, centred around the last ~20 trades.
        const N: f64 = 20.0;
        let alpha = 2.0 / (N + 1.0);

        let mut ema = 0.0_f64;
        let mut ema2 = 0.0_f64;
        let mut initialised = false;
        let mut sample_count: usize = 0;
        let mut k = redis_f64("risk:slip_k").await.unwrap_or(2.0);

        while let Some(slip) = slippage_rx.recv().await {
            // Update EMAs.
            if !initialised {
                ema = slip;
                ema2 = slip * slip;
                initialised = true;
            } else {
                ema = alpha * slip + (1.0 - alpha) * ema;
                ema2 = alpha * slip * slip + (1.0 - alpha) * ema2;
            }

            sample_count += 1;

            let var = (ema2 - ema * ema).max(0.0);
            let std_dev = var.sqrt();

            if let Some(new_k) = redis_f64("risk:slip_k").await {
                k = new_k;
            }
            let threshold = k * std_dev;

            // Emit Prometheus metrics.
            set_risk_slippage_threshold(threshold);
            set_risk_last_slippage(slip);

            // Breach condition (tail event) – only enforce once we have
            // collected a minimal history to avoid triggering on the very
            // first trade.
            if sample_count >= 5 && slip < -threshold && threshold > 0.0 {
                let _ = kill_tx.send(KillSwitch::Slippage);
            }
        }
    });

    Ok(())
}
