use executor::metrics;
use metrics_exporter_prometheus::PrometheusBuilder;
use once_cell::sync::Lazy;

// Ensure a single global Prometheus recorder is installed for all tests.
static HANDLE: Lazy<metrics_exporter_prometheus::PrometheusHandle> = Lazy::new(|| {
    PrometheusBuilder::new()
        .install_recorder()
        .expect("recorder install")
});

#[test]
fn killswitch_counter_increments() {
    // Reset counters by dropping and reinstalling recorder is not possible, so
    // rely on monotonic counter semantics – compute delta instead.
    let before = HANDLE.render();
    let before_val = extract_counter(&before, "killswitch_total", "kind=\"slippage\"").unwrap_or(0);

    metrics::inc_killswitch("slippage");

    let after = HANDLE.render();
    let after_val = extract_counter(&after, "killswitch_total", "kind=\"slippage\"").expect("missing killswitch metric");
    assert_eq!(after_val, before_val + 1);
}

#[test]
fn restart_counter_increments_across_startups() {
    let before = HANDLE.render();
    let before_val = extract_counter(&before, "restarts_total", "").unwrap_or(0);

    // Simulate second run.
    metrics::inc_restart();

    let after = HANDLE.render();
    let after_val = extract_counter(&after, "restarts_total", "").expect("missing restarts metric");
    assert_eq!(after_val, before_val + 1);
}

/// Simple helper to parse a Prometheus counter value from rendered exposition
/// text.  Looks for the first occurrence of `name{label_filter} value`.
fn extract_counter(body: &str, name: &str, label_filter: &str) -> Option<u64> {
    for line in body.lines() {
        // Skip comments.
        if line.starts_with('#') { continue; }
        if !line.starts_with(name) { continue; }
        if !label_filter.is_empty() && !line.contains(label_filter) { continue; }
        // Split whitespace to obtain value.
        if let Some(val_str) = line.split_whitespace().nth(1) {
            if let Ok(v) = val_str.parse::<u64>() {
                return Some(v);
            }
        }
    }
    None
} 