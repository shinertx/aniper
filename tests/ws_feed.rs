use executor::ws_feed::{normalise_message, LaunchEvent};
use std::time::{Duration, Instant};

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn normalise_under_2ms() {
    const N: usize = 100;
    let raw = r#"{\"mint\":\"X\",\"creator\":\"Y\",\"holders_60\":111,\"lp\":0.9}"#;

    for _ in 0..N {
        let start = Instant::now();
        let ev: LaunchEvent = normalise_message(raw).expect("parse failed");
        assert!(ev.holders_60 > 0);
        assert!(start.elapsed() < Duration::from_millis(2), "latency > 2ms");
    }
} 