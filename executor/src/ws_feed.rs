use futures_util::{SinkExt, StreamExt};
use serde::{Deserialize, Serialize};
use std::str::FromStr;
use tokio::sync::mpsc::Sender;
use tokio_tungstenite::{connect_async, tungstenite::Message};
use tracing::{error, info, warn};
/* -------------------------------------------------------------------------
 * NEW: anyhow for ergonomic Result
 * ---------------------------------------------------------------------- */
use anyhow::{anyhow, Context, Result};
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;

// --- JSON-RPC Deserialization Structures ---
#[derive(Deserialize, Debug)]
struct RpcLogValue {
    logs: Vec<String>,
    #[serde(default)]
    err: serde_json::Value,
}

#[derive(Deserialize, Debug)]
struct RpcResult {
    value: RpcLogValue,
}

#[derive(Deserialize, Debug)]
struct RpcParams {
    result: RpcResult,
    #[allow(dead_code)]
    subscription: u64,
}

#[derive(Deserialize, Debug)]
struct LogNotification {
    method: String,
    params: RpcParams,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum Platform {
    PumpFun,
    LetsBonk,
}

impl FromStr for Platform {
    type Err = anyhow::Error;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "pumpfun" => Ok(Platform::PumpFun),
            "letsbonk" => Ok(Platform::LetsBonk),
            _ => Err(anyhow!("Unknown platform: {}", s)),
        }
    }
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct LaunchEvent {
    pub mint: String,
    pub creator: String,
    pub holders_60: u32,
    pub lp: f64,
    pub platform: Platform,
    pub amount_usdc: Option<f64>,
    pub max_slippage: Option<f64>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct HistoricalEvent {
    pub timestamp: String,
    pub platform: String,
    pub token_address: String,
    pub creator_address: String,
    pub name: String,
    pub symbol: String,
    pub description: String,
    pub market_cap_usd: f64,
    pub trade_volume_24h: f64,
    pub is_rugpull: bool,
    pub raw_event_data: String,
}

const MAX_MSG_LEN: usize = 65536; // Increased for verbose log messages

/// Extracts a value from a log line given a prefix.
/// e.g., "Program log: mint: 123" with prefix "mint: " -> "123"
fn extract_from_log(log: &str, prefix: &str) -> Option<String> {
    log.find(prefix).map(|start| {
        let rest = &log[start + prefix.len()..];
        rest.split_whitespace().next().unwrap_or("").to_string()
    })
}

/// Validate and parse raw websocket text from a Solana logsSubscribe stream.
pub fn normalise_message(raw: &str, platform: Platform) -> Option<LaunchEvent> {
    if raw.len() > MAX_MSG_LEN {
        warn!(
            target = "ws_feed",
            "dropping oversized frame: {} bytes",
            raw.len()
        );
        return None;
    }

    let notification: LogNotification = match serde_json::from_str::<LogNotification>(raw) {
        Ok(n) if n.method == "logsNotification" => n,
        _ => return None,
    };

    // Ignore if the transaction failed
    if !notification.params.result.value.err.is_null() {
        return None;
    }

    let logs = &notification.params.result.value.logs;

    // Check for a specific log message that indicates a new LP has been added.
    if !logs.iter().any(|log| log.contains("initialize2")) {
        return None;
    }

    let mut mint = None;
    let mut creator = None;
    let mut holders_60 = None;
    let mut lp = None;

    for log in logs {
        if let Some(val) = extract_from_log(log, "Program log: mint: ") {
            mint = Some(val);
        }
        if let Some(val) = extract_from_log(log, "Program log: creator: ") {
            creator = Some(val);
        }
        if let Some(val) = extract_from_log(log, "Program log: holders_60: ") {
            holders_60 = val.parse::<u32>().ok();
        }
        if let Some(val) = extract_from_log(log, "Program log: lp: ") {
            lp = val.parse::<f64>().ok();
        }
    }

    if let (Some(mint), Some(creator), Some(holders_60), Some(lp)) = (mint, creator, holders_60, lp)
    {
        Some(LaunchEvent {
            mint,
            creator,
            holders_60,
            lp,
            platform,
            amount_usdc: None,  // Default, can be overridden by agent
            max_slippage: None, // Default, can be overridden by agent
        })
    } else {
        None
    }
}

/// Replays events from a file, sending them to the trader.
pub async fn run_replay(file_path: String, tx: Sender<LaunchEvent>) -> Result<()> {
    info!(
        target = "ws_feed",
        "Starting replay from file: {}", file_path
    );

    let path = Path::new(&file_path);
    let extension = path.extension().and_then(|s| s.to_str());

    match extension {
        Some("json") => {
            let file = File::open(path).context("Failed to open JSON replay file")?;
            let reader = BufReader::new(file);
            for line in reader.lines() {
                let line = line.context("Failed to read line from replay file")?;
                if let Ok(event) = serde_json::from_str::<LaunchEvent>(&line) {
                    if tx.send(event).await.is_err() {
                        error!("Receiver dropped, stopping replay");
                        break;
                    }
                }
            }
        }
        Some("parquet") => {
            // This is a simplified placeholder for Parquet reading.
            // For a real implementation, you would use a library like `arrow` or `parquet`.
            // This example will just log a message.
            warn!(target: "ws_feed", "Parquet replay is a placeholder. No events will be sent.");
            info!(target: "ws_feed", "Simulating a long-running historical replay...");
            // In a real scenario, you'd loop through Parquet row groups here.
            // For now, we just sleep to simulate work.
            tokio::time::sleep(tokio::time::Duration::from_secs(10)).await;
            info!(target: "ws_feed", "Finished simulated historical replay.");
        }
        _ => {
            return Err(anyhow!("Unsupported replay file format: {:?}", extension));
        }
    }

    info!(target = "ws_feed", "Replay finished.");
    Ok(())
}

/// Returns the websocket URL to use, derived from the `SOLANA_RPC_URL`
/// environment variable.
fn ws_url() -> String {
    let rpc_url = std::env::var("SOLANA_RPC_URL")
        .or_else(|_| std::env::var("SOLANA_URL"))
        .or_else(|_| std::env::var("RPC_URL"))
        .unwrap_or_else(|_| "https://api.devnet.solana.com".to_string());

    // Convert http(s) to ws(s)
    rpc_url
        .replace("https://", "wss://")
        .replace("http://", "ws://")
}

async fn subscribe_platform(
    tx: Sender<LaunchEvent>,
    platform: Platform,
    program_id: String,
) -> Result<()> {
    let url = ws_url();
    info!(
        target = "ws_feed",
        "Connecting to WebSocket for platform {:?}: {}", platform, url
    );

    let (mut ws, _) = connect_async(&url)
        .await
        .with_context(|| format!("Failed to connect to WebSocket at {url}"))?;

    let subscribe_request = serde_json::json!({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "logsSubscribe",
        "params": [
            { "mentions": [ program_id ] },
            { "commitment": "finalized" }
        ]
    });

    ws.send(Message::Text(subscribe_request.to_string()))
        .await?;
    info!(
        target = "ws_feed",
        "Subscribed to logs for program ID: {}", program_id
    );

    // The first message is a confirmation of subscription with an ID.
    // We can store this ID if we want to unsubscribe later.
    if let Some(Ok(Message::Text(msg))) = ws.next().await {
        if !msg.contains("result") {
            warn!(target = "ws_feed", "Subscription may have failed: {}", msg);
        }
    }

    while let Some(frame) = ws.next().await {
        match frame {
            Ok(Message::Text(txt)) => {
                if let Some(ev) = normalise_message(&txt, platform) {
                    if let Err(e) = tx.send(ev).await {
                        warn!(
                            target = "ws_feed",
                            "Failed to send event to trader channel: {}", e
                        );
                    }
                }
            }
            Ok(Message::Close(close_frame)) => {
                warn!(
                    target = "ws_feed",
                    "WebSocket stream closed for {:?}: {:?}", platform, close_frame
                );
                break;
            }
            Err(e) => {
                warn!(
                    target = "ws_feed",
                    "WebSocket stream error for {:?}: {}", platform, e
                );
                break;
            }
            _ => {}
        }
    }

    Err(anyhow!("WebSocket stream for {:?} disconnected.", platform))
}

pub async fn run(tx: Sender<LaunchEvent>) -> Result<()> {
    use std::time::Duration;

    let platforms_str = std::env::var("PLATFORMS").unwrap_or_else(|_| "pumpfun".to_string());
    let platforms: Vec<Platform> = platforms_str
        .split(',')
        .filter_map(|s| s.trim().parse().ok())
        .collect();

    if platforms.is_empty() {
        return Err(anyhow!(
            "No valid platforms configured in PLATFORMS env var."
        ));
    }

    let mut handles = vec![];

    for platform in platforms {
        let program_id_key = match platform {
            Platform::PumpFun => "PUMPFUN_PROGRAM_ID",
            Platform::LetsBonk => "LETSBONK_PROGRAM_ID",
        };

        if let Ok(program_id) = std::env::var(program_id_key) {
            let tx_clone = tx.clone();
            let handle = tokio::spawn(async move {
                loop {
                    info!(
                        target = "ws_feed",
                        "Starting subscription for {:?}...", platform
                    );
                    match subscribe_platform(tx_clone.clone(), platform, program_id.clone()).await {
                        Ok(_) => {
                            // This should not happen as subscribe_platform should run indefinitely
                            warn!(
                                target = "ws_feed",
                                "Subscription for {:?} ended unexpectedly without an error.",
                                platform
                            );
                        }
                        Err(e) => {
                            warn!(
                                target = "ws_feed",
                                "Subscription for {:?} failed: {}. Retrying in 5s.", platform, e
                            );
                        }
                    }
                    tokio::time::sleep(Duration::from_secs(5)).await;
                }
            });
            handles.push(handle);
        } else {
            warn!(
                target = "ws_feed",
                "Program ID for {:?} not found in environment variables (expected {}).",
                platform,
                program_id_key
            );
        }
    }

    // Keep the main `run` task alive. The spawned tasks will run in the background.
    futures_util::future::join_all(handles).await;

    Ok(())
}
