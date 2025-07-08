// --- Risk Management Guards -------------------------------------------------
//
// 1. Equity Floor – kill-switch if account equity drops below a Redis-configured
//    threshold (default 300 USDC).
// 2. Slippage Sentinel – kill-switch if realised trade slippage breaches an
//    adaptive tail threshold based on a 20-period EMA of volatility.
// ---------------------------------------------------------------------------

use anyhow::Result;
use once_cell::sync::Lazy;
use std::sync::atomic::{AtomicU64, Ordering};
use tokio::sync::{broadcast::Sender, mpsc::Receiver};
use tokio::time::{sleep, Duration};

use crate::metrics::{set_risk_equity_usdc, set_risk_last_slippage, set_risk_slippage_threshold};

#[derive(Debug, Clone)]
pub enum KillSwitch {
    EquityFloor,
    Slippage,
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

async fn get_balance_usdc() -> Result<f64> {
    // Test override takes priority.
    if let Some(v) = {
        let raw = BALANCE_OVERRIDE_CENTS.load(Ordering::Relaxed);
        (raw != u64::MAX).then(|| raw as f64 / 100.0)
    } {
        return Ok(v);
    }

    // TODO: wire real balance endpoint (broker API / on-chain view).
    Ok(1_000.0) // stub – well above default equity floor
}

// ---------------------------------------------------------------------------
// Redis helpers -------------------------------------------------------------
// ---------------------------------------------------------------------------

async fn redis_f64(key: &str) -> Option<f64> {
    let url = std::env::var("REDIS_URL").unwrap_or_else(|_| "redis://127.0.0.1/".into());
    if let Ok(client) = redis::Client::open(url) {
        if let Ok(mut conn) = client.get_async_connection().await {
            let res: redis::RedisResult<Option<String>> =
                redis::Cmd::new().arg("GET").arg(key).query_async(&mut conn).await;
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
    //--------------------------------------------------
    // Equity-floor guard
    //--------------------------------------------------
    let kill_tx_eq = kill_tx.clone();
    tokio::spawn(async move {
        let poll_ms: u64 = std::env::var("RISK_EQUITY_POLL_MS")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(60_000);

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
                    tracing::warn!(target = "risk", "balance fetch error: {e}");
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
    // Slippage sentinel
    //--------------------------------------------------
    tokio::spawn(async move {
        // EMA parameters – 20-period, centred around the last ~20 trades.
        const N: f64 = 20.0;
        let alpha = 2.0 / (N + 1.0);

        let mut ema = 0.0_f64;
        let mut ema2 = 0.0_f64;
        let mut initialised = false;
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

            let var = (ema2 - ema * ema).max(0.0);
            let std_dev = var.sqrt();

            if let Some(new_k) = redis_f64("risk:slip_k").await {
                k = new_k;
            }
            let threshold = k * std_dev;

            // Emit Prometheus metrics.
            set_risk_slippage_threshold(threshold);
            set_risk_last_slippage(slip);

            // Breach condition (tail event).
            if slip < -threshold && threshold > 0.0 {
                let _ = kill_tx.send(KillSwitch::Slippage);
            }
        }
    });

    Ok(())
}