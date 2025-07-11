use base64::engine::general_purpose::STANDARD as BASE64_STD;
use base64::Engine;
use metrics_exporter_prometheus::PrometheusBuilder;
use std::net::SocketAddr;
use tracing::info;

// NEW: remove single-thread Tokio runtime builder
// use tokio::runtime::Builder;

/// NEW: make function async to run on the main Tokio runtime
pub async fn serve_prometheus() {
    info!(
        target = "startup",
        "Initializing Prometheus metrics server..."
    );
    let builder = PrometheusBuilder::new();
    let handle = builder.install_recorder().expect("metrics recorder");

    // Optional Basic Auth header – format USER:PASS → "Basic <base64>"
    let auth_header = std::env::var("METRICS_BASIC_AUTH").ok().map(|raw| {
        let token = BASE64_STD.encode(raw);
        format!("Basic {token}")
    });

    // REMOVED: std::thread::spawn(move || {
    let addr: SocketAddr = std::env::var("METRICS_BIND")
        .unwrap_or_else(|_| "127.0.0.1:9185".into())
        .parse()
        .expect("invalid METRICS_BIND address");

    let server = hyper::Server::bind(&addr).serve(hyper::service::make_service_fn(move |_| {
        let handle = handle.clone();
        let auth_header = auth_header.clone();
        async move {
            Ok::<_, hyper::Error>(hyper::service::service_fn(move |req| {
                let handle = handle.clone();
                let auth_header = auth_header.clone();
                async move {
                    // Enforce auth if configured.
                    if let Some(expected) = auth_header {
                        match req.headers().get(hyper::header::AUTHORIZATION) {
                            Some(h) if h.to_str().ok() == Some(&expected) => {}
                            _ => {
                                return Ok::<_, hyper::Error>(
                                    hyper::Response::builder()
                                        .status(hyper::StatusCode::UNAUTHORIZED)
                                        // FIX: no `?` (avoid From/Into mismatch)
                                        .body::<String>("unauthorized".to_string())
                                        .unwrap(),
                                );
                            }
                        }
                    }
                    let body = handle.render();
                    Ok::<_, hyper::Error>(hyper::Response::new(body))
                }
            }))
        }
    }));

    // NEW: Run Hyper server directly on the current runtime and log errors.
    if let Err(e) = server.await {
        tracing::error!(target: "metrics", "server error: {e}");
    }
    // REMOVED: });
}

// --- Risk metrics helpers --------------------------------------------------
pub fn set_risk_equity_usdc(_bal: f64) {
    metrics::gauge!("risk_equity_usdc", _bal);
}
pub fn set_risk_last_slippage(_slip: f64) {
    metrics::gauge!("risk_last_slippage", _slip);
}
pub fn set_risk_slippage_threshold(_threshold: f64) {
    metrics::gauge!("risk_slippage_threshold", _threshold);
}

pub fn set_risk_portfolio_stop_loss(value: f64) {
    metrics::gauge!("risk_portfolio_stop_loss_usd", value);
}

// --- Trade metrics helpers -------------------------------------------------
/// Increments submitted trades counter for a given platform.
pub fn inc_trades_submitted(platform: &str) {
    let p: &'static str = Box::leak(platform.to_owned().into_boxed_str());
    metrics::increment_counter!("trades_submitted", "platform" => p);
}

/// Increments confirmed trades counter for a given platform.
pub fn inc_trades_confirmed(platform: &str) {
    let p: &'static str = Box::leak(platform.to_owned().into_boxed_str());
    metrics::increment_counter!("trades_confirmed", "platform" => p);
}

/// Increment the killswitch counter for the provided `kind` label.
/// Leaks a couple of &'static strs on purpose (trivial).
pub fn inc_killswitch(kind: &str) {
    let k: &'static str = Box::leak(kind.to_owned().into_boxed_str());
    metrics::increment_counter!("killswitch_total", "kind" => k);
}

pub fn inc_restart() {
    metrics::increment_counter!("restarts");
}
