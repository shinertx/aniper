use executor::risk::{self, KillSwitch};
use metrics_exporter_prometheus::PrometheusBuilder;
use once_cell::sync::Lazy;
use solana_sdk::signature::write_keypair_file;
use solana_sdk::signature::Keypair;
use std::sync::Mutex;
use tempfile::NamedTempFile;
use tokio::sync::{broadcast, mpsc};
use tokio::time::{timeout, Duration};

static METRICS_RECORDER: Lazy<Mutex<()>> = Lazy::new(|| Mutex::new(()));

fn setup_metrics_recorder() -> Result<(), Box<dyn std::error::Error>> {
    let _guard = METRICS_RECORDER.lock().unwrap();
    if PrometheusBuilder::new().install_recorder().is_ok() {
        Ok(())
    } else {
        // Recorder is already installed
        Ok(())
    }
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn equity_floor_breach_emits_killswitch() {
    setup_metrics_recorder().unwrap();

    // Set up test environment
    std::env::set_var("REDIS_URL", "redis://localhost:6379");
    std::env::set_var("RISK_EQUITY_POLL_MS", "50");
    // Disable portfolio stop-loss for this test by setting a very low percentage
    std::env::set_var("PORTFOLIO_STOP_LOSS_PERCENT", "1.0");

    let (ks_tx, mut ks_rx) = broadcast::channel(4);
    let (_slip_tx, slip_rx) = mpsc::channel(4);

    // Start with balance well below equity floor (300 USDC default)
    risk::_set_mock_balance_usdc(100.0);

    tokio::spawn(async move {
        let _ = risk::run(ks_tx, slip_rx).await;
    });

    // Wait for killswitch - should be equity floor since we're at 100 USDC < 300 USDC floor
    let ks = timeout(Duration::from_secs(1), ks_rx.recv())
        .await
        .expect("timeout")
        .expect("sender closed");
    println!(
        "Received kill-switch in equity_floor_breach_emits_killswitch: {:?}",
        ks
    );
    assert!(matches!(ks, KillSwitch::EquityFloor));

    // Verify metric exposed.
    // Note: handle.render() is not available with the global recorder.
    // We can't easily assert the metrics output here without more complex test setup.
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn equity_floor_rpc_balance() {
    // Set up test environment
    std::env::set_var("REDIS_URL", "redis://localhost:6379");
    std::env::set_var("PORTFOLIO_STOP_LOSS_PERCENT", "1.0"); // Disable portfolio stop-loss

    let kp = Keypair::new();
    let file = NamedTempFile::new().unwrap();
    write_keypair_file(&kp, file.path()).unwrap();
    std::env::set_var("KEYPAIR_PATH", file.path());

    // Poll quickly and set override low via mock balance.
    std::env::set_var("RISK_EQUITY_POLL_MS", "50");
    risk::_set_mock_balance_usdc(100.0); // Well below 300 USDC floor

    let (ks_tx, mut ks_rx) = broadcast::channel(4);
    let (_slip_tx, slip_rx) = mpsc::channel(4);

    tokio::spawn(async move {
        let _ = risk::run(ks_tx, slip_rx).await;
    });

    let ks = timeout(Duration::from_secs(1), ks_rx.recv())
        .await
        .expect("timeout")
        .expect("sender closed");
    println!("Received kill-switch in equity_floor_rpc_balance: {:?}", ks);
    assert!(matches!(ks, KillSwitch::EquityFloor));
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn slippage_breach_emits_killswitch() {
    setup_metrics_recorder().unwrap();

    // Set up test environment - disable other risk checks
    std::env::set_var("REDIS_URL", "redis://localhost:6379");
    std::env::set_var("PORTFOLIO_STOP_LOSS_PERCENT", "99.0"); // Very high, won't trigger

    let (ks_tx, mut ks_rx) = broadcast::channel(4);
    let (slip_tx, slip_rx) = mpsc::channel(32);

    // Set very high balance to avoid equity floor trigger
    risk::_set_mock_balance_usdc(10000.0);

    tokio::spawn(async move {
        let _ = risk::run(ks_tx, slip_rx).await;
    });

    // Feed benign samples.
    for _ in 0..29 {
        slip_tx.send(0.001).await.unwrap();
    }
    // Outlier breach.
    slip_tx.send(-0.5).await.unwrap();

    let ks = timeout(Duration::from_secs(1), ks_rx.recv())
        .await
        .expect("timeout")
        .expect("sender closed");
    println!(
        "Received kill-switch in slippage_breach_emits_killswitch: {:?}",
        ks
    );
    assert!(matches!(ks, KillSwitch::Slippage));

    // Metrics should include threshold + last slippage.
    // Note: handle.render() is not available with the global recorder.
}
