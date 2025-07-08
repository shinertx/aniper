use metrics_exporter_prometheus::{PrometheusBuilder, PrometheusHandle};
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