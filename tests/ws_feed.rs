use executor::ws_feed::{normalise_message, LaunchEvent, Platform};
use std::time::{Duration, Instant};

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn normalise_under_2ms() {
    const N: usize = 100;
    let raw = r#"{"jsonrpc":"2.0","method":"logsNotification","params":{"result":{"context":{"slot":123},"value":{"signature":"abc...","err":null,"logs":["Program log: Instruction: Create","Program log: mint: DuMmyMintAddress1111111111111111111111111111","Program log: creator: DummyCreatorAddress11111111111111111111111"]}},"subscription":456}}"#;

    for _ in 0..N {
        let start = Instant::now();
        let ev: LaunchEvent = normalise_message(raw, Platform::PumpFun).expect("parse failed");
        assert_eq!(ev.mint, "DuMmyMintAddress1111111111111111111111111111");
        assert_eq!(ev.creator, "DummyCreatorAddress11111111111111111111111");
        assert!(start.elapsed() < Duration::from_millis(2), "latency > 2ms");
    }
}
