use executor::trader;
use executor::ws_feed::LaunchEvent;
use metrics_exporter_prometheus::PrometheusBuilder;
use mockito::Server;
use solana_sdk::signature::{write_keypair_file, Keypair};
use std::process::{Command, Stdio};
use std::time::Duration;
use tempfile::NamedTempFile;
use tokio::sync::mpsc;

/// Start a local `solana-test-validator`. Skips the test if binary missing.
fn start_test_validator() -> Option<std::process::Child> {
    if which::which("solana-test-validator").is_err() {
        eprintln!("solana-test-validator not found – skipping trader OCO test");
        return None;
    }
    let child = Command::new("solana-test-validator")
        .arg("--reset")
        .arg("--quiet")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .expect("failed to start validator");

    // Wait until node ready.
    for _ in 0..10 {
        if let Ok(slot) =
            solana_client::rpc_client::RpcClient::new("http://127.0.0.1:8899").get_slot()
        {
            if slot > 0 {
                break;
            }
        }
        std::thread::sleep(Duration::from_millis(500));
    }
    Some(child)
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn oco_two_orders_and_slippage_sample() {
    // Prepare temporary keypair file for signer.
    let kp = Keypair::new();
    let tmp = NamedTempFile::new().expect("tmp file");
    write_keypair_file(&kp, tmp.path()).expect("write keypair");
    std::env::set_var("KEYPAIR_PATH", tmp.path());

    // Spin validator.
    let mut validator = match start_test_validator() {
        Some(v) => v,
        None => return,
    };

    // Metrics recorder.
    let handle = PrometheusBuilder::new()
        .install_recorder()
        .expect("prom metrics");

    // Mock Jupiter API.
    let mut server = Server::new_async().await;
    let jupiter_api_url = server.url();

    // Environment wires.
    std::env::set_var("SOLANA_RPC_URL", "http://127.0.0.1:8899");
    std::env::set_var("JUPITER_API", &jupiter_api_url);

    // Mock quote & swap to force fallback path (500 status).
    let _m_quote = server
        .mock("GET", "/quote")
        .with_status(500)
        .with_body("Internal Server Error")
        .create_async()
        .await;
    let _m_swap = server
        .mock("POST", "/swap")
        .with_status(500)
        .with_body("Internal Server Error")
        .create_async()
        .await;

    // Channels.
    let (evt_tx, evt_rx) = mpsc::channel(1);
    let (slip_tx, mut slip_rx) = mpsc::channel(4);

    // Spawn trader.
    let trader_handle = tokio::spawn(async move { trader::run(evt_rx, slip_tx).await });

    // Send launch event.
    let ev = LaunchEvent {
        mint: "TESTMINT".into(),
        creator: "CREATOR".into(),
        holders_60: 120,
        lp: 1.1,
        platform: executor::ws_feed::Platform::PumpFun,
        amount_usdc: None,
        max_slippage: None,
    };
    evt_tx.send(ev).await.unwrap();
    drop(evt_tx);

    // Expect slippage sample within 5 seconds (increased timeout for debugging).
    let slip = tokio::time::timeout(Duration::from_secs(5), slip_rx.recv())
        .await
        .expect("timeout waiting slip");
    println!("Received slippage sample: {:?}", slip);
    assert!(slip.is_some(), "no slippage sample received");

    // Wait for task end.
    let res = trader_handle.await.expect("join err");
    assert!(res.is_ok(), "trader returned error");

    // Inspect metrics – should submit three txs (buy + 2 OCO legs).
    let body = handle.render();
    let submitted = body
        .lines()
        .find(|l| l.starts_with("trades_submitted_total"))
        .unwrap_or("trades_submitted_total 0");
    let parts: Vec<&str> = submitted.split_whitespace().collect();
    let count: f64 = parts.last().unwrap().parse().unwrap_or(0.0);
    assert!(count >= 3.0, "expected >=3 trades submitted, got {count}");

    // Clean up validator.
    let _ = validator.kill();
}
