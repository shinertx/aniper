use anyhow::Result;
use tokio::sync::mpsc::Receiver;
use super::classifier::score;
use super::ws_feed::LaunchEvent;

pub async fn run(mut rx: Receiver<LaunchEvent>) -> Result<()> {
    while let Some(ev) = rx.recv().await {
        if score(&ev) > 0.5 {
            // TODO: build & send devnet TX
            tracing::info!(target="trade", "Would buy token {}", ev.mint);
        }
    }
    Ok(())
} 