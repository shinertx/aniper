use metrics_exporter_prometheus::PrometheusBuilder;
use std::net::SocketAddr;

pub fn serve_prometheus() {
    let builder = PrometheusBuilder::new();
    let handle = builder.install_recorder().expect("metrics recorder");
    std::thread::spawn(move || {
        let addr: SocketAddr = "0.0.0.0:9184".parse().unwrap();
        hyper::Server::bind(&addr)
            .serve(hyper::service::make_service_fn(move |_| {
                let handle = handle.clone();
                async move {
                    Ok::<_, hyper::Error>(hyper::service::service_fn(move |_req| {
                        let handle = handle.clone();
                        async move {
                            let body = handle.render();
                            Ok::<_, hyper::Error>(hyper::Response::new(body.into()))
                        }
                    }))
                }
            }))
            .unwrap();
    });
}

// --- Trade metrics helpers -------------------------------------------------

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