// --- Risk Management Guards -------------------------------------------------
//
// 1. Equity Floor – kill-switch if account equity drops below a Redis-configured
//    threshold (default 300 USDC).
// 2. Slippage Sentinel – kill-switch if realised trade slippage breaches an
//    adaptive tail threshold based on a 20-period EMA of volatility.
// 3. Portfolio Stop-Loss - kill-switch if total portfolio value drops by a
//    configured percentage from its peak.
// ---------------------------------------------------------------------------

use anyhow::{anyhow, Context, Result};
use once_cell::sync::Lazy;
use solana_client::rpc_client::RpcClient;
use solana_sdk::signature::read_keypair_file;
use solana_sdk::signer::Signer;
use std::sync::atomic::{AtomicU64, Ordering};
use tokio::sync::{broadcast::Sender, mpsc::Receiver};
use tokio::time::{sleep, Duration};
use tracing::info;

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
    let url = std::env::var("REDIS_URL")
        .with_context(|| "REDIS_URL not set – refusing to start (risk module)")
        .unwrap();

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
    info!(target = "startup", "Initializing risk module...");
    // Ensure REDIS_URL is set, otherwise refuse to start.
    let _redis_url = std::env::var("REDIS_URL")
        .with_context(|| "REDIS_URL not set – refusing to start (risk module)")?;

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
                        tracing::info!(
                            target = "risk",
                            "Initialized portfolio peak equity at {:.2} USDC",
                            peak_equity
                        );
                    } else {
                        peak_equity = peak_equity.max(bal);
                    }

                    let stop_loss_level = peak_equity * (1.0 - (stop_loss_percent / 100.0));

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

// Equity Floor --------------------------------------------------------------
// ---------------------------------------------------------------------------
async fn redis_get_equity_floor_usdc() -> Result<f64> {
    Ok(redis_f64("risk:equity_floor_usdc").await.unwrap_or(300.0))
}

pub async fn equity_floor_check(tx: Sender<KillSwitch>) -> Result<()> {
    let floor = redis_get_equity_floor_usdc().await?;
    let balance = get_balance_usdc().await?;
    set_risk_equity_usdc(balance);

    if balance < floor {
        tx.send(KillSwitch::EquityFloor)?;
        return Err(anyhow!("Equity floor breached: {} < {}", balance, floor));
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Slippage Sentinel ---------------------------------------------------------
// ---------------------------------------------------------------------------

/// Fetches the dynamic slippage threshold from Redis.
/// Defaults to a conservative 25% if not set.
async fn redis_get_slippage_threshold() -> Result<f64> {
    Ok(redis_f64("risk:slippage_threshold_percent")
        .await
        .unwrap_or(25.0))
}

/// The core slippage check.
///
/// # Arguments
/// * `realised_slippage` - The slippage observed in a completed trade.
/// * `tx` - The broadcast channel to send a kill-switch signal on.
pub async fn slippage_check(realised_slippage: f64, tx: Sender<KillSwitch>) -> Result<()> {
    set_risk_last_slippage(realised_slippage);
    let threshold = redis_get_slippage_threshold().await?;
    set_risk_slippage_threshold(threshold);

    if realised_slippage > threshold {
        tx.send(KillSwitch::Slippage)?;
        return Err(anyhow!(
            "Slippage threshold breached: {} > {}",
            realised_slippage,
            threshold
        ));
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Portfolio Stop-Loss -------------------------------------------------------
// ---------------------------------------------------------------------------

/// Fetches the portfolio stop-loss percentage from Redis.
/// Defaults to 20% if not set.
async fn redis_get_portfolio_stop_loss_percent() -> Result<f64> {
    Ok(redis_f64("risk:portfolio_stop_loss_percent")
        .await
        .unwrap_or(20.0))
}

/// The core portfolio stop-loss check.
///
/// # Arguments
/// * `tx` - The broadcast channel to send a kill-switch signal on.
pub async fn portfolio_stop_loss_check(tx: Sender<KillSwitch>) -> Result<()> {
    let stop_loss_percent = redis_get_portfolio_stop_loss_percent().await?;
    set_risk_portfolio_stop_loss(stop_loss_percent);

    // TODO: This needs to track historical portfolio value.
    // For now, we'll just use the current balance as a placeholder.
    let current_value = get_balance_usdc().await?;
    let peak_value = f64::max(current_value, 0.0); // Placeholder

    if current_value < peak_value * (1.0 - stop_loss_percent / 100.0) {
        tx.send(KillSwitch::PortfolioStopLoss)?;
        return Err(anyhow!(
            "Portfolio stop-loss breached: {} < {} * (1 - {})",
            current_value,
            peak_value,
            stop_loss_percent
        ));
    }

    Ok(())
}
