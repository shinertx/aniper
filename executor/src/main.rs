use anyhow::Result;
use tracing_subscriber::EnvFilter;
use executor::{metrics, trader, ws_feed};
use executor::risk;

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    let (feed_tx, feed_rx) = tokio::sync::mpsc::channel(10_000);

    // risk slippage channel
    let (slip_tx, slip_rx) = tokio::sync::mpsc::channel(256);

    tokio::spawn(ws_feed::run(feed_tx));
    tokio::spawn(trader::run(feed_rx, slip_tx.clone()));

    // --- Risk management ---------------------------------------------------
    let (kill_tx, _kill_rx) = tokio::sync::broadcast::channel(16);
    tokio::spawn(async move {
        if let Err(e) = risk::run(kill_tx, slip_rx).await {
            tracing::error!(target = "risk", "risk module exited: {e}");
        }
    });

    metrics::serve_prometheus();
    futures::future::pending::<()>().await;
    Ok(())
} 