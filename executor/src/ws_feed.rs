use tokio::sync::mpsc::Sender;
use serde::Deserialize;
use tokio_tungstenite::{connect_async, tungstenite::Message};
use futures_util::StreamExt;
use tracing::warn;

#[derive(Debug, Deserialize)]
pub struct LaunchEvent {
    pub mint: String,
    pub creator: String,
    pub holders_60: u32,
    pub lp: f64,
}

const MAX_MSG_LEN: usize = 4_096;

/// Validate and parse raw websocket text into LaunchEvent.
pub fn normalise_message(raw: &str) -> Option<LaunchEvent> {
    if raw.len() > MAX_MSG_LEN {
        warn!(target="ws_feed", "dropping oversized frame: {} bytes", raw.len());
        return None;
    }
    serde_json::from_str::<LaunchEvent>(raw).ok()
}

pub async fn run(tx: Sender<LaunchEvent>) -> Result<()> {
    use std::time::Duration;
    let url = "wss://devnet-replay.example/ws";
    loop {
        let (ws, _) = match connect_async(url).await {
            Ok(v) => v,
            Err(e) => {
                warn!(target="ws_feed", "connect error: {e}");
                tokio::time::sleep(Duration::from_secs(1)).await;
                continue;
            }
        };
        let (_, mut read) = ws.split();
        while let Some(frame) = read.next().await {
            match frame {
                Ok(Message::Text(txt)) => {
                    if let Some(ev) = normalise_message(&txt) {
                        let _ = tx.try_send(ev);
                    }
                }
                Ok(Message::Close(_)) => break,
                Err(e) => {
                    warn!(target="ws_feed", "stream error: {e}");
                    break;
                }
                _ => {}
            }
        }
        tokio::time::sleep(Duration::from_secs(1)).await;
    }
} 