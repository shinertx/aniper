use base64::engine::general_purpose::STANDARD as BASE64_STD;
use base64::Engine;
use metrics_exporter_prometheus::PrometheusBuilder;
use std::net::SocketAddr;
// -----------------------------------------------------------------------------
//  NEW: single-thread Tokio runtime to block on Hyper server
// -----------------------------------------------------------------------------
use tokio::runtime::Builder;

pub fn serve_prometheus() {
    let builder = PrometheusBuilder::new();
    let handle = builder.install_recorder().expect("metrics recorder");

    // Optional Basic Auth header – format USER:PASS → "Basic <base64>"
    let auth_header = std::env::var("METRICS_BASIC_AUTH").ok().map(|raw| {
        let token = BASE64_STD.encode(raw);
        format!("Basic {token}")
    });

    std::thread::spawn(move || {
        let addr: SocketAddr = std::env::var("METRICS_BIND")
            .unwrap_or_else(|_| "127.0.0.1:9184".into())
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

        // Run Hyper server on a tiny single-threaded runtime.
        Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap()
            .block_on(server)
            .unwrap();
    });
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

// --- Trade metrics helpers -------------------------------------------------
pub fn inc_trades_confirmed() {
    metrics::increment_counter!("trades_confirmed");
}
pub fn inc_trades_submitted() {
    metrics::increment_counter!("trades_submitted");
}

/// Increment the killswitch counter for the provided `kind` label.
/// Leaks a couple of &'static strs on purpose (trivial).
pub fn inc_killswitch(kind: &str) {
    let k: &'static str = Box::leak(kind.to_owned().into_boxed_str());
    metrics::increment_counter!("killswitch_total", "kind" => k);
}
