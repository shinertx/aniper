use base64::engine::general_purpose::STANDARD as BASE64_STD;
use base64::Engine;
use metrics_exporter_prometheus::PrometheusBuilder;
use std::net::SocketAddr;
use tokio::runtime::Builder;

/// Spawn an HTTP server that exposes Prometheus metrics.
///
/// If the `METRICS_BASIC_AUTH` env-var is set (`USER:PASS`) every request must
/// supply a matching `Authorization: Basic <base64>` header.
pub fn serve_prometheus() {
    // Register global recorder
    let builder = PrometheusBuilder::new();
    let handle = builder.install_recorder().expect("metrics recorder");

    // Optional basic-auth token
    let auth_header = std::env::var("METRICS_BASIC_AUTH").ok().map(|raw| {
        let token = BASE64_STD.encode(raw);
        format!("Basic {token}")
    });

    std::thread::spawn(move || {
        let addr: SocketAddr = std::env::var("METRICS_BIND")
            .unwrap_or_else(|_| "127.0.0.1:9184".into())
            .parse()
            .expect("invalid METRICS_BIND address");

        // Hyper service for a single endpoint
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
                                            .body("unauthorized".into())
                                            .unwrap(),
                                    );
                                }
                            }
                        }

                        let body = handle.render();
                        Ok::<_, hyper::Error>(hyper::Response::new(body.into()))
                    }
                }))
            }
        }));

        // Run the server on a minimal single-threaded runtime.
        Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap()
            .block_on(server)
            .unwrap();
    });
}

// ---------------------------------------------------------------------------
// Trade metrics helpers
// ---------------------------------------------------------------------------

/// Increment when a trade transaction is submitted to the cluster.
pub fn inc_trades_submitted() {
    metrics::increment_counter!("trades_submitted_total");
}

/// Increment when the previously submitted trade is confirmed.
pub fn inc_trades_confirmed() {
    metrics::increment_counter!("trades_confirmed_total");
}

/// Set the current dynamic slippage threshold (absolute value).
pub fn set_risk_slippage_threshold(v: f64) {
    metrics::gauge!("risk_slippage_threshold", v);
}

/// Set the last observed realised slippage sample.
pub fn set_risk_last_slippage(v: f64) {
    metrics::gauge!("risk_last_slippage", v);
}

/// Track account equity (USDC) sampled by the equity-floor guard.
pub fn set_risk_equity_usdc(v: f64) {
    metrics::gauge!("risk_equity_usdc", v);
}

/// Increment the killswitch counter for the provided `kind` label.
///
/// The label is leaked once so it can live for the entire process lifetime;
/// only a handful of distinct kinds exist so this is fine.
pub fn inc_killswitch(kind: &str) {
    let k: &'static str = Box::leak(kind.to_owned().into_boxed_str());
    metrics::increment_counter!("killswitch_total", "kind" => k);
}

/// Increment the restart counter – call from the executor entry-point at
/// startup so successive launches can be tracked.
pub fn inc_restart() {
    metrics::increment_counter!("restarts_total");
}
