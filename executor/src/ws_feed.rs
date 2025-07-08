use anyhow::Result;
use async_channel::Sender;
use serde::Deserialize;
use tokio_tungstenite::{connect_async, tungstenite::Message};
use futures_util::{StreamExt, TryStreamExt};

#[derive(Debug, Deserialize)]
pub struct LaunchEvent {
    pub mint: String,
    pub creator: String,
    pub holders_60: u32,
    pub lp: f64,
}

pub async fn run(tx: Sender<LaunchEvent>) -> Result<()> {
    let url = "wss://devnet-replay.example/ws"; // placeholder
    let (ws, _) = connect_async(url).await?;
    let (_, mut read) = ws.split();
    while let Some(msg) = read.next().await {
        let msg = msg?;
        if let Message::Text(t) = msg {
            if let Ok(ev) = serde_json::from_str::<LaunchEvent>(&t) {
                let _ = tx.try_send(ev);
            }
        }
    }
    Ok(())
} 