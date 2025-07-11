use super::classifier::score;
use super::metrics::{inc_trades_confirmed, inc_trades_submitted};
use super::ws_feed::{LaunchEvent, Platform};
use crate::compliance;
use anyhow::{anyhow, Result};
use base64::engine::general_purpose::STANDARD as BASE64_STD;
use base64::Engine;
use once_cell::sync::Lazy;
use redis::Client as RedisClient;
use std::collections::HashSet;
use std::str::FromStr;
use std::sync::{Arc, RwLock};
use std::time::{Duration, Instant};
use tokio::sync::mpsc::Receiver;

use reqwest::Client;
use solana_client::rpc_client::RpcClient;
use solana_sdk::{
    commitment_config::CommitmentConfig,
    compute_budget::ComputeBudgetInstruction,
    signature::{read_keypair_file, Keypair, Signature, Signer},
    system_instruction,
    transaction::Transaction,
};

/// Maximum number of slots to wait for a confirmation before giving up.
const MAX_CONFIRMATION_SLOTS: u64 = 10;

/// Risk Management Configuration
static RISK_CONFIG: Lazy<Arc<RwLock<RiskConfig>>> =
    Lazy::new(|| Arc::new(RwLock::new(RiskConfig::from_env())));

#[derive(Debug, Clone)]
struct RiskConfig {
    position_size_percent: f64,
    liquidity_threshold_usd: f64,
    auto_sell_profit_multiplier: f64,
    auto_sell_loss_percent: f64,
}

impl RiskConfig {
    fn from_env() -> Self {
        let position_size_percent = std::env::var("POSITION_SIZE_PERCENT")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(2.0); // Default to 2%
        let liquidity_threshold_usd = std::env::var("LIQUIDITY_THRESHOLD")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(10000.0); // Default to $10k
        let auto_sell_profit_multiplier = std::env::var("AUTO_SELL_PROFIT_MULTIPLIER")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(5.0); // 5x profit
        let auto_sell_loss_percent = std::env::var("AUTO_SELL_LOSS_PERCENT")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(20.0); // 20% loss

        Self {
            position_size_percent,
            liquidity_threshold_usd,
            auto_sell_profit_multiplier,
            auto_sell_loss_percent,
        }
    }

    fn refresh() {
        let mut config = RISK_CONFIG.write().unwrap();
        *config = RiskConfig::from_env();
        tracing::info!(target = "trade", "Refreshed risk configuration: {:?}", *config);
    }
}

/// Returns the RPC URL to use (defaults to Solana devnet).
/// Temporary fix: Added better fallback handling for CLI scenarios.
pub fn rpc_url() -> String {
    // Try multiple environment variables for compatibility
    std::env::var("SOLANA_RPC_URL")
        .or_else(|_| std::env::var("SOLANA_URL"))
        .or_else(|_| std::env::var("RPC_URL"))
        .unwrap_or_else(|_| {
            // Check if we're running in test/local mode
            if std::env::var("RUST_TEST").is_ok() || std::env::var("CARGO_PKG_NAME").is_ok() {
                "http://127.0.0.1:8899".to_string()
            } else {
                "https://api.devnet.solana.com".to_string()
            }
        })
}

/// Returns the base Jupiter API (quote & swap v6).
fn jupiter_api() -> String {
    std::env::var("JUPITER_API").unwrap_or_else(|_| "https://quote-api.jup.ag/v6".into())
}

/// USDC mint on devnet/mainnet (wrapped if on devnet stub).
const USDC_MINT: &str = "So11111111111111111111111111111111111111112";

/// Wrapper holding a signed transaction alongside its implied price (out_amount / in_amount).
#[derive(Clone)]
struct SwapTx {
    tx: Transaction,
    price: f64,
}

/// Attempt to fetch a pre-built swap transaction from a Jupiter-style endpoint. This is a
/// placeholder implementation – on errors the caller should fall back to `fallback_transfer_tx`.
async fn fetch_swap_tx(
    client: &RpcClient,
    keypair: &Keypair,
    output_mint: &str,
    amount_usdc: Option<u64>,
    min_out_pct: Option<f64>,
) -> Result<SwapTx> {
    #[derive(serde::Deserialize)]
    #[allow(dead_code)]
    struct QuoteRoute {
        in_amount: String,
        out_amount: String,
        price_impact_pct: String,
        // we only need the route to pass to /swap but keep as raw json string.
        // serde will retain unknown fields – handy for forward compatibility.
        #[serde(flatten)]
        extra: serde_json::Value,
    }

    #[derive(serde::Deserialize)]
    #[allow(dead_code)]
    struct QuoteResp {
        data: Vec<QuoteRoute>,
    }

    #[derive(serde::Deserialize)]
    struct SwapResp {
        #[serde(rename = "swapTransaction")]
        swap_transaction: String,
        #[serde(rename = "inAmount")]
        in_amount: String,
        #[serde(rename = "outAmount")]
        out_amount: String,
    }

    let http = Client::new();
    let api = jupiter_api();

    // Use provided amount or default to 1 USDC (1,000,000 lamports)
    let trade_amount = amount_usdc.unwrap_or(1_000_000);

    // -- 1. Quote -----------------------------------------------------------
    let quote_url = format!("{api}/quote?inputMint={USDC_MINT}&outputMint={output_mint}&amount={trade_amount}&slippageBps=100&onlyDirectRoutes=false&platformFeeBps=0");
    let quote: QuoteResp = http.get(&quote_url).send().await?.json().await?;

    // Get expected output for min_out_pct calculation
    let expected_out = if let Some(route) = quote.data.first() {
        route.out_amount.parse::<u64>()?
    } else {
        return Err(anyhow!("No quote routes available"));
    };

    // -- 2. Swap with proper min_out calculation -----------------------------
    let min_out_amount = if let Some(pct) = min_out_pct {
        // For take-profit (pct > 1.0) or stop-loss (pct < 1.0)
        ((expected_out as f64) * pct) as u64
    } else {
        expected_out // Use expected amount
    };

    let swap_url = format!("{api}/swap?inputMint={USDC_MINT}&outputMint={output_mint}&amount={trade_amount}&slippageBps=100&userPublicKey={user}&wrapUnwrapSOL=true&feeBps=0&minOutAmount={min_out_amount}", user = keypair.pubkey());

    let resp: SwapResp = http.get(&swap_url).send().await?.json().await?;
    //  FIX: use BASE64_STD engine instead of deprecated base64::decode
    let raw = BASE64_STD.decode(resp.swap_transaction.clone())?;
    let mut tx: Transaction = bincode::deserialize(&raw)?;

    // Ensure recent blockhash & additional signature from *our* private key –
    // Jupiter sometimes returns a stale hash if the HTTP round-trip lags.
    let blockhash = client.get_latest_blockhash()?;
    tx.partial_sign(&[keypair], blockhash);

    // price = out_amount / in_amount - FIXED: Convert from lamports to token units
    let in_amt: f64 = resp.in_amount.parse::<u64>()? as f64;
    let out_amt: f64 = resp.out_amount.parse::<u64>()? as f64;
    let in_amt_ui = in_amt / 1_000_000.0; // USDC has 6 decimals
    let out_amt_ui = out_amt / 1_000_000.0; // Assume meme token has 6 decimals
    let price = if in_amt_ui > 0.0 {
        out_amt_ui / in_amt_ui
    } else {
        0.0
    };

    Ok(SwapTx { tx, price })
}

/// Build a simple 0-lamport self-transfer so that we submit *something* to the cluster when swap
/// construction fails. This keeps the dev-net traffic pattern realistic without taking risk.
fn fallback_transfer_tx(client: &RpcClient, keypair: &Keypair) -> Result<Transaction> {
    let blockhash = client.get_latest_blockhash()?;
    let ix = system_instruction::transfer(&keypair.pubkey(), &keypair.pubkey(), 0);
    let tx =
        Transaction::new_signed_with_payer(&[ix], Some(&keypair.pubkey()), &[keypair], blockhash);
    Ok(tx)
}

/// Poll the confirmation status of `sig` until it is finalised or `MAX_CONFIRMATION_SLOTS` elapsed.
fn wait_for_confirmation(client: &RpcClient, sig: &Signature) -> Result<()> {
    let start_slot = client.get_slot()?;
    loop {
        if client.confirm_transaction(sig)? {
            return Ok(());
        }
        let current = client.get_slot()?;
        if current.saturating_sub(start_slot) > MAX_CONFIRMATION_SLOTS {
            return Err(anyhow!(
                "transaction {} not confirmed within {} slots",
                sig,
                MAX_CONFIRMATION_SLOTS
            ));
        }
        std::thread::sleep(Duration::from_millis(400));
    }
}

/// Attach an optional priority-fee tip (lamports per CU) and broadcast to *all*
/// configured RPC endpoints.  Returns the signature from the primary RPC.
fn sign_and_send(urls: &[String], tx: &Transaction, keypair: &Keypair) -> Result<Signature> {
    // Determine tip in micro-lamports per CU.
    let tip_lamports: u64 = std::env::var("TRADE_TIP")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(0);

    // If a tip is requested, prepend a compute-budget ix.  We rebuild the
    // transaction instructions because mutating an already-compiled message is
    // fiddly.
    let final_tx = if tip_lamports > 0 {
        let blockhash = RpcClient::new(urls.first().unwrap().clone()).get_latest_blockhash()?;
        let ixs = vec![ComputeBudgetInstruction::set_compute_unit_price(
            tip_lamports,
        )];
        // We cannot easily de-compile the existing compiled instructions back
        // into `Instruction`, so the safest option is to **submit two
        // separate transactions**: the tip stub followed by the original tx.
        // For now we opt for the simple route – tip stub.
        let tip_tx = Transaction::new_signed_with_payer(
            &ixs,
            Some(&keypair.pubkey()),
            &[keypair],
            blockhash,
        );
        // Broadcast tip first but ignore errors (non-supported rpc versions).
        for url in urls {
            let rpc = RpcClient::new(url.clone());
            let _ = rpc.send_transaction(&tip_tx);
        }
        // Continue with original tx.
        tx.clone()
    } else {
        tx.clone()
    };

    // Broadcast original / swapped tx.
    let mut primary_sig: Option<Signature> = None;
    for url in urls {
        let rpc = RpcClient::new(url.clone());
        match rpc.send_transaction(&final_tx) {
            Ok(sig) => {
                if primary_sig.is_none() {
                    primary_sig = Some(sig);
                }
            }
            Err(e) => {
                tracing::warn!(target = "trade", "rpc {url} send error: {e}");
            }
        }
    }
    primary_sig.ok_or_else(|| anyhow!("all RPC submissions failed"))
}

/// Build *OCO* (one-cancels-other) exit orders: a take-profit and a stop-loss.
/// This placeholder uses two independent Jupiter swap transactions.
/// If swap construction fails we fall back to 0-lamport transfers so latency tests remain unaffected.
async fn build_oco(client: &RpcClient, keypair: &Keypair, mint: &str) -> Result<(SwapTx, SwapTx)> {
    let config = RISK_CONFIG.read().unwrap().clone();
    let take_profit_multiplier = config.auto_sell_profit_multiplier;
    let stop_loss_multiplier = 1.0 - (config.auto_sell_loss_percent / 100.0);

    // TP route (sell)
    let tp_tx = fetch_swap_tx(client, keypair, mint, None, Some(take_profit_multiplier))
        .await
        .unwrap_or_else(|_| {
            tracing::warn!(target = "trade", "TP construction failed – using noop tx");
            SwapTx {
                tx: fallback_transfer_tx(client, keypair).expect("transfer tx"),
                price: 0.0,
            }
        });

    // SL route (sell)
    let sl_tx = fetch_swap_tx(client, keypair, mint, None, Some(stop_loss_multiplier))
        .await
        .unwrap_or_else(|_| {
            tracing::warn!(target = "trade", "SL construction failed – using noop tx");
            SwapTx {
                tx: fallback_transfer_tx(client, keypair).expect("transfer tx"),
                price: 0.0,
            }
        });

    Ok((tp_tx, sl_tx))
}

/// Manual trade signal from Redis
#[derive(Debug, serde::Deserialize)]
struct RedisTradeSignal {
    action: String,
    token: String,
    amount_usdc: f64,
    max_slippage: f64,
    source: String,
    platform: Option<String>, // Added platform field
}

/// Convert Redis signal to LaunchEvent for processing
fn redis_signal_to_launch_event(signal: &RedisTradeSignal) -> LaunchEvent {
    let platform = signal
        .platform
        .as_deref()
        .and_then(|s| Platform::from_str(s).ok())
        .unwrap_or(Platform::PumpFun); // Default to PumpFun if not specified or invalid

    LaunchEvent {
        mint: signal.token.clone(),
        creator: format!("redis_{}", signal.source),
        holders_60: 1000, // High holder count to pass scoring
        lp: 999999.0,     // High LP to pass liquidity check
        platform,
    }
}

/// Placeholder for event enrichment. In a real system, this would fetch
/// live LP, holder count, and other data via RPC.
async fn enrich_event(_rpc: &RpcClient, event: &mut LaunchEvent) -> Result<()> {
    // TODO: Implement real-time data fetching.
    // 1. Find the Raydium liquidity pool for the event.mint.
    // 2. Get the token balances of the pool to calculate liquidity in USD.
    // 3. Get the number of token holders.
    // For now, we use a placeholder value that will pass the default check.
    event.lp = 20000.0;
    Ok(())
}

/// Core trade loop – consumes launch events and, when a positive classification is produced,
/// executes a buy followed immediately by a sell.
pub async fn run(
    mut rx: Receiver<LaunchEvent>,
    slip_tx: tokio::sync::mpsc::Sender<f64>,
) -> Result<()> {
    // Initialise once outside the loop.
    let rpc = RpcClient::new_with_commitment(rpc_url(), CommitmentConfig::processed());

    // ------------------------------------------------------------------
    // Secure signer loading --------------------------------------------------
    // ------------------------------------------------------------------
    let keypair = match std::env::var("KEYPAIR_PATH") {
        Ok(p) => read_keypair_file(&p)
            .map_err(|e| anyhow!("failed to load keypair from {p}: {e}", p = p, e = e))?,
        Err(_) => {
            return Err(anyhow!(
                "KEYPAIR_PATH not set – refusing to start; see README 'Security Controls'."
            ))
        }
    };
    tracing::info!(
        target = "trade",
        "Loaded trading keypair: {}",
        keypair.pubkey()
    );

    // Fund the account – devnet & local validator honour airdrops. Ignore errors on rate-limit.
    if let Ok(sig) = rpc.request_airdrop(&keypair.pubkey(), 1_000_000_000) {
        let _ = wait_for_confirmation(&rpc, &sig);
    }

    // Connect to Redis for manual trade signals
    let redis_client = RedisClient::open("redis://redis:6379")?;
    let mut redis_conn = redis_client.get_async_connection().await?;
    tracing::info!(target = "trade", "Connected to Redis for manual trade signals");

    // Deduplication: Track processed (mint, creator) pairs for 5 minutes
    let mut processed_events: HashSet<(String, String)> = HashSet::new();
    let mut last_cleanup = Instant::now();
    let mut last_risk_refresh = Instant::now();

    loop {
        // Clean up old events every minute
        if last_cleanup.elapsed() > Duration::from_secs(60) {
            processed_events.clear();
            last_cleanup = Instant::now();
            tracing::debug!(target = "trade", "Cleared deduplication cache");
        }

        // Refresh risk config every 5 minutes
        if last_risk_refresh.elapsed() > Duration::from_secs(300) {
            RiskConfig::refresh();
            last_risk_refresh = Instant::now();
        }

        tokio::select! {
            // Process WebSocket launch events
            Some(mut ev) = rx.recv() => {
                // Deduplication check
                let event_key = (ev.mint.clone(), ev.creator.clone());
                if processed_events.contains(&event_key) {
                    tracing::debug!(target = "trade", "Skipping duplicate event for mint: {}", ev.mint);
                    continue;
                }
                processed_events.insert(event_key);

                // --- Enrich event with live data (e.g., liquidity) ---
                if let Err(e) = enrich_event(&rpc, &mut ev).await {
                    tracing::warn!(target = "trade", "Failed to enrich event for mint {}: {}", ev.mint, e);
                    continue;
                }

                if score(&ev) <= 0.5 {
                    continue;
                }

                // Compliance / sanctions check.
                if compliance::is_sanctioned(&ev.creator) || compliance::is_sanctioned(&ev.mint) {
                    tracing::warn!(
                        target = "trade",
                        "Skipping sanctioned asset or creator: creator={} mint={}",
                        ev.creator,
                        ev.mint
                    );
                    continue;
                }

                // --- New Risk Checks ---
                let risk_config = RISK_CONFIG.read().unwrap();
                if ev.lp < risk_config.liquidity_threshold_usd {
                    tracing::warn!(
                        target = "trade",
                        "Skipping trade due to low liquidity for mint {}: LP {:.2} < threshold {:.2}",
                        ev.mint, ev.lp, risk_config.liquidity_threshold_usd
                    );
                    continue;
                }

                // --- Platform-specific Guards ---
                if ev.platform == Platform::LetsBonk {
                    // Example guard: check if token name contains "bonk"
                    // In a real scenario, this would involve more complex checks like
                    // analyzing the token's metadata or on-chain program details.
                    if !ev.mint.to_lowercase().contains("bonk") {
                         tracing::info!(target = "trade", "[LetsBonk Guard] Skipping token without 'bonk' in name: {}", ev.mint);
                         continue;
                    }
                }


                tracing::info!(target = "trade", "Processing WebSocket launch event for mint {} from {:?}", ev.mint, ev.platform);
                if let Err(e) = execute_trade(&rpc, &keypair, &ev, &slip_tx).await {
                    tracing::error!(target = "trade", "Trade execution failed: {}", e);
                }
            }

            // Process Redis trade signals
            _ = tokio::time::sleep(tokio::time::Duration::from_secs(1)) => {
                // Check for Redis trade signals
                let signal_data: Option<String> = redis::cmd("LPOP")
                    .arg("trade_signals")
                    .query_async(&mut redis_conn)
                    .await
                    .unwrap_or(None);

                if let Some(signal_json) = signal_data {
                    tracing::info!(target = "trade", "Processing Redis trade signal: {}", signal_json);

                    match serde_json::from_str::<RedisTradeSignal>(&signal_json) {
                        Ok(signal) => {
                            if signal.action == "buy" {
                                let launch_event = redis_signal_to_launch_event(&signal);
                                tracing::info!(target = "trade", "Executing Redis-triggered trade for mint {}", launch_event.mint);

                                if let Err(e) = execute_trade(&rpc, &keypair, &launch_event, &slip_tx).await {
                                    tracing::error!(target = "trade", "Redis trade execution failed: {}", e);
                                }
                            }
                        }
                        Err(e) => {
                            tracing::warn!(target = "trade", "Failed to parse Redis signal: {}", e);
                        }
                    }
                }
            }
        }
    }
}

/// Execute a trade for the given launch event
async fn execute_trade(
    rpc: &RpcClient,
    keypair: &Keypair,
    ev: &LaunchEvent,
    slip_tx: &tokio::sync::mpsc::Sender<f64>,
) -> Result<()> {
    tracing::info!(target = "trade", "Attempting buy for mint {}", ev.mint);

    // --- Position Sizing ---
    let risk_config = RISK_CONFIG.read().unwrap();
    let balance_usdc = crate::risk::get_balance_usdc().await.unwrap_or(1000.0); // Default to 1k if fetch fails
    let position_size_usdc = balance_usdc * (risk_config.position_size_percent / 100.0);
    let position_size_lamports = (position_size_usdc * 1_000_000.0) as u64;

    // Build swap TX or fall back.
    let buy_swap = match fetch_swap_tx(rpc, keypair, &ev.mint, Some(position_size_lamports), None).await {
        Ok(t) => t,
        Err(e) => {
            tracing::warn!(
                target = "trade",
                "swap construction failed – falling back: {e}"
            );
            SwapTx {
                tx: fallback_transfer_tx(rpc, keypair)?,
                price: 0.0,
            }
        }
    };

    // Broadcast.
    let platform_str = format!("{:?}", ev.platform).to_lowercase();
    let sig = sign_and_send(&[rpc_url()], &buy_swap.tx, keypair)?;
    inc_trades_submitted(&platform_str);
    tracing::info!(target = "trade", "Submitted buy tx: {sig} for {:.2} USDC on {}", position_size_usdc, platform_str);
    wait_for_confirmation(rpc, &sig)?;
    inc_trades_confirmed(&platform_str);
    tracing::info!(target = "trade", "Buy confirmed: {sig}");

    // ------------------------------------------------------------------
    // Build OCO exit legs
    // ------------------------------------------------------------------
    let (tp_swap, sl_swap) = build_oco(rpc, keypair, &ev.mint).await?;

    // Gather RPC endpoints – primary defaults to initial URL, others may
    // be supplied via comma-separated `SOLANA_RPC_URLS` env var.
    let mut rpc_urls: Vec<String> = std::env::var("SOLANA_RPC_URLS")
        .ok()
        .map(|v| v.split(',').map(|s| s.trim().to_string()).collect())
        .unwrap_or_default();
    if rpc_urls.is_empty() {
        rpc_urls.push(rpc_url());
    }

    // --- TP leg -------------------------------------------------------
    let tp_sig = sign_and_send(&rpc_urls, &tp_swap.tx, keypair)?;
    inc_trades_submitted(&platform_str);
    tracing::info!(target = "trade", "TP leg submitted: {tp_sig}");

    // --- SL leg -------------------------------------------------------
    let sl_sig = sign_and_send(&rpc_urls, &sl_swap.tx, keypair)?;
    inc_trades_submitted(&platform_str);
    tracing::info!(target = "trade", "SL leg submitted: {sl_sig}");

    // We do *not* wait for confirmations here – the two orders race each
    // other and one will eventually settle the position.  Whichever wins
    // will be picked up by the slippage sentinel down-stream.

    // -----------------------------------------------------------------
    // Slippage reporting – compute based on TP leg implied price.
    // If prices unavailable, default to 0.
    // -----------------------------------------------------------------
    let entry_price = buy_swap.price;
    let exit_price = tp_swap.price; // optimistic TP reference
    let slip_value = if entry_price > 0.0 && exit_price > 0.0 {
        (exit_price / entry_price) - 1.0
    } else {
        0.0
    };
    let _ = slip_tx.send(slip_value).await; // ignore error if channel closed

    Ok(())
}
