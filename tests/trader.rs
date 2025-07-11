use executor::trader;
use executor::ws_feed::LaunchEvent;
use mockito::Server;
use tokio::sync::mpsc;
use std::process::{Command, Stdio};
use std::time::Duration;
use tempfile::NamedTempFile;
use solana_sdk::signature::{Keypair, write_keypair_file};

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
    // Prepare temporary keypair file and set KEYPAIR_PATH.
    let kp = Keypair::new();
    let tmp = NamedTempFile::new().expect("tmp file");
    write_keypair_file(&kp, tmp.path()).expect("write keypair");
    std::env::set_var("KEYPAIR_PATH", tmp.path());

    // Spin up local validator (skip if unavailable).
    let mut validator = match start_test_validator() {
        Some(v) => v,
        None => return,
    };

    // Mock Jupiter API.
    let mut server = Server::new_async().await;
    let jupiter_api_url = server.url();

    // Point interactor at local node.
    std::env::set_var("SOLANA_RPC_URL", "http://127.0.0.1:8899");
    std::env::set_var("JUPITER_API", &jupiter_api_url);

    // Mock new Jupiter endpoints to force fallback path.
    let _m_quote = server.mock("GET", "/quote")
        .with_status(500)
        .create_async().await;
    let _m_swap = server.mock("GET", "/swap")
        .with_status(500)
        .create_async().await;

    let (tx, rx) = mpsc::channel(1);
    let (slip_tx, _slip_rx) = mpsc::channel(4);
    let trader_handle = tokio::spawn(async move { trader::run(rx, slip_tx).await });

    let ev = LaunchEvent {
        mint: "TEST".into(),
        creator: "CREATOR".into(),
        holders_60: 100,
        lp: 99999.0, // Set high to pass liquidity check
        platform: executor::ws_feed::Platform::PumpFun,
    };
    tx.send(ev).await.unwrap();
    drop(tx); // close channel so trader exits after processing.

    let res = trader_handle.await.expect("join error");
    assert!(res.is_ok(), "trader run failed: {:?}", res.err());

    // Clean up validator.
    let _ = validator.kill();
}

#[test]
fn test_rpc_url_fallback() {
    // Clear any existing env vars
    std::env::remove_var("SOLANA_RPC_URL");
    std::env::remove_var("SOLANA_URL");
    std::env::remove_var("RPC_URL");
    
    // Test default fallback
    let url = executor::trader::rpc_url();
    assert!(url.contains("api.devnet.solana.com") || url.contains("127.0.0.1:8899"));
    
    // Test SOLANA_RPC_URL takes priority
    std::env::set_var("SOLANA_RPC_URL", "http://custom.example.com");
    let url = executor::trader::rpc_url();
    assert_eq!(url, "http://custom.example.com");
    
    // Test fallback chain
    std::env::remove_var("SOLANA_RPC_URL");
    std::env::set_var("SOLANA_URL", "http://fallback.example.com");
    let url = executor::trader::rpc_url();
    assert_eq!(url, "http://fallback.example.com");
    
    // Cleanup
    std::env::remove_var("SOLANA_URL");
}