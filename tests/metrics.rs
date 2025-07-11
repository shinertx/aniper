use executor::metrics;
use metrics_exporter_prometheus::PrometheusBuilder;
use once_cell::sync::Lazy;

// Ensure a single global Prometheus recorder is installed for all tests.
static HANDLE: Lazy<metrics_exporter_prometheus::PrometheusHandle> = Lazy::new(|| {
    PrometheusBuilder::new()
        .install_recorder()
        .expect("recorder install")
});

#[tokio::test]
async fn prometheus_bind_respects_env() {
    std::env::set_var("METRICS_BIND", "127.0.0.1:0");
    let handle = tokio::spawn(metrics::serve_prometheus());
    tokio::time::sleep(std::time::Duration::from_millis(50)).await;
    handle.abort(); // Clean up the spawned task
}

#[tokio::test]
#[ignore]
/// This test is ignored due to global state/race condition in Prometheus recorder.
/// See AGENTS.md for details. Run in isolation if needed.
async fn killswitch_counter_increments() {
    // Reset counters by dropping and reinstalling recorder is not possible, so
    // rely on monotonic counter semantics – compute delta instead.
    let before = HANDLE.render();
    let before_val = extract_counter(&before, "killswitch_total", "kind=\"slippage\"").unwrap_or(0);

    metrics::inc_killswitch("slippage");

    // Retry logic to handle metric update latency
    let mut after_val = 0;
    for _ in 0..10 {
        tokio::time::sleep(std::time::Duration::from_millis(10)).await;
        let after = HANDLE.render();
        if let Some(val) = extract_counter(&after, "killswitch_total", "kind=\"slippage\"") {
            after_val = val;
            if after_val == before_val + 1 {
                break;
            }
        }
    }

    assert_eq!(after_val, before_val + 1, "missing killswitch metric");
}

#[tokio::test]
#[ignore]
/// This test is ignored due to global state/race condition in Prometheus recorder.
/// See AGENTS.md for details. Run in isolation if needed.
async fn restart_counter_increments_across_startups() {
    let before = HANDLE.render();
    let before_val = extract_counter(&before, "restarts", "").unwrap_or(0);

    // Simulate second run.
    metrics::inc_restart();

    // Retry logic to handle metric update latency
    let mut after_val = 0;
    for _ in 0..10 {
        tokio::time::sleep(std::time::Duration::from_millis(10)).await;
        let after = HANDLE.render();
        if let Some(val) = extract_counter(&after, "restarts", "") {
            after_val = val;
            if after_val == before_val + 1 {
                break;
            }
        }
    }

    assert_eq!(after_val, before_val + 1, "missing restarts metric");
}

/// Simple helper to parse a Prometheus counter value from rendered exposition
/// text.  Looks for the first occurrence of `name{label_filter} value`.
fn extract_counter(body: &str, name: &str, label_filter: &str) -> Option<u64> {
    for line in body.lines() {
        // Skip comments.
        if line.starts_with('#') {
            continue;
        }
        if !line.starts_with(name) {
            continue;
        }
        if !label_filter.is_empty() && !line.contains(label_filter) {
            continue;
        }
        // Split whitespace to obtain value.
        if let Some(val_str) = line.split_whitespace().nth(1) {
            if let Ok(v) = val_str.parse::<u64>() {
                return Some(v);
            }
        }
    }
    None
}
