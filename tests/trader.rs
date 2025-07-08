use executor::trader;
use executor::ws_feed::LaunchEvent;
use tokio::sync::mpsc;
use std::process::{Command, Stdio};
use std::time::Duration;

/// Helper to start a local `solana-test-validator`. Skips the test if the binary
/// is not available in the current PATH.
fn start_test_validator() -> Option<std::process::Child> {
    if which::which("solana-test-validator").is_err() {
        eprintln!("solana-test-validator not found – skipping trader integration test");
        return None;
    }
    let child = Command::new("solana-test-validator")
        .arg("--reset")
        .arg("--quiet")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .expect("failed to start test validator");

    // Allow node to boot – keep retry short to avoid CI stalls.
    for _ in 0..10 {
        if let Ok(slot) = solana_client::rpc_client::RpcClient::new("http://127.0.0.1:8899").get_slot() {
            if slot > 0 { break; }
        }
        std::thread::sleep(Duration::from_millis(500));
    }
    Some(child)
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn trade_flow_confirmed() {
    // Spin up local validator (skip if unavailable).
    let validator = match start_test_validator() {
        Some(v) => v,
        None => return,
    };

    // Point interactor at local node.
    std::env::set_var("SOLANA_RPC_URL", "http://127.0.0.1:8899");
    std::env::set_var("JUPITER_API", &mockito::server_url());

    // Mock new Jupiter endpoints to force fallback path.
    let _m_quote = mockito::mock("GET", "/quote")
        .with_status(500)
        .create();
    let _m_swap = mockito::mock("GET", "/swap")
        .with_status(500)
        .create();

    let (tx, rx) = mpsc::channel(1);
    let (slip_tx, _slip_rx) = mpsc::channel(4);
    let trader_handle = tokio::spawn(async move { trader::run(rx, slip_tx).await });

    let ev = LaunchEvent {
        mint: "TEST".into(),
        creator: "CREATOR".into(),
        holders_60: 100,
        lp: 1.0,
    };
    tx.send(ev).await.unwrap();
    drop(tx); // close channel so trader exits after processing.

    let res = trader_handle.await.expect("join error");
    assert!(res.is_ok(), "trader run failed: {:?}", res.err());

    // Clean up validator.
    let _ = validator.kill();
} 