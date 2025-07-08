use executor::risk::{self, KillSwitch};
use metrics_exporter_prometheus::PrometheusBuilder;
use tokio::sync::{broadcast, mpsc};
use tokio::time::{timeout, Duration};

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn equity_floor_breach_emits_killswitch() {
    // Install metrics recorder.
    let handle = PrometheusBuilder::new()
        .install_recorder()
        .expect("recorder install");

    // Tighten polling cadence so test completes quickly.
    std::env::set_var("RISK_EQUITY_POLL_MS", "50");

    let (ks_tx, mut ks_rx) = broadcast::channel(4);
    let (_slip_tx, slip_rx) = mpsc::channel(4);

    // Start with healthy balance, then breach.
    risk::_set_mock_balance_usdc(400.0);
    tokio::spawn(async move {
        let _ = risk::run(ks_tx, slip_rx).await;
    });

    // Allow one poll tick at healthy level.
    tokio::time::sleep(Duration::from_millis(60)).await;
    // Drop below floor.
    risk::_set_mock_balance_usdc(200.0);

    let ks = timeout(Duration::from_secs(1), ks_rx.recv())
        .await
        .expect("timeout")
        .expect("sender closed");
    assert!(matches!(ks, KillSwitch::EquityFloor));

    // Verify metric exposed.
    let body = handle.render();
    assert!(body.contains("risk_equity_usdc"));
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn slippage_breach_emits_killswitch() {
    let handle = PrometheusBuilder::new()
        .install_recorder()
        .expect("recorder install");

    let (ks_tx, mut ks_rx) = broadcast::channel(4);
    let (slip_tx, slip_rx) = mpsc::channel(32);

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
    assert!(matches!(ks, KillSwitch::Slippage));

    // Metrics should include threshold + last slippage.
    let body = handle.render();
    assert!(body.contains("risk_slippage_threshold"));
    assert!(body.contains("risk_last_slippage"));
} 