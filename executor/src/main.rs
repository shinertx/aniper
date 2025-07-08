use anyhow::Result;
use tracing_subscriber::EnvFilter;
use executor::{metrics, trader, ws_feed};

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    let (tx, rx) = tokio::sync::mpsc::channel(10_000);
    tokio::spawn(ws_feed::run(tx));
    tokio::spawn(trader::run(rx));

    metrics::serve_prometheus();
    futures::future::pending::<()>().await;
    Ok(())
} 