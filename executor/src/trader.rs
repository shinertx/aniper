use anyhow::Result;
use async_channel::Receiver;
use super::classifier::score;
use super::ws_feed::LaunchEvent;

pub async fn run(rx: Receiver<LaunchEvent>) -> Result<()> {
    while let Ok(ev) = rx.recv().await {
        if score(&ev) > 0.5 {
            // TODO: build & send devnet TX
            tracing::info!(target="trade", "Would buy token {}", ev.mint);
        }
    }
    Ok(())
} 