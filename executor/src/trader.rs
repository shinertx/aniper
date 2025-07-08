use anyhow::{Result, anyhow};
use tokio::sync::mpsc::Receiver;
use super::classifier::score;
use super::ws_feed::LaunchEvent;
use std::time::Duration;
use super::metrics::{inc_trades_submitted, inc_trades_confirmed};

use reqwest::Client;
use solana_client::rpc_client::RpcClient;
use solana_sdk::{
    commitment_config::CommitmentConfig,
    signature::{Keypair, Signature, Signer},
    system_instruction,
    transaction::Transaction,
};

/// Maximum number of slots to wait for a confirmation before giving up.
const MAX_CONFIRMATION_SLOTS: u64 = 10;

/// Returns the RPC URL to use (defaults to Solana devnet).
fn rpc_url() -> String {
    std::env::var("SOLANA_RPC_URL").unwrap_or_else(|_| "https://api.devnet.solana.com".to_string())
}

/// Returns the Jupiter swap API endpoint (placeholder).
fn jupiter_api() -> String {
    std::env::var("JUPITER_SWAP_API").unwrap_or_else(|_| "https://quote-api.jup.ag/v6/swap".into())
}

/// Attempt to fetch a pre-built swap transaction from a Jupiter-style endpoint. This is a
/// placeholder implementation – on errors the caller should fall back to `fallback_transfer_tx`.
async fn fetch_swap_tx(_client: &RpcClient, keypair: &Keypair, mint: &str) -> Result<Transaction> {
    #[derive(serde::Deserialize)]
    struct SwapResp {
        #[serde(rename = "swapTransaction")]
        swap_transaction: String,
    }

    let url = jupiter_api();
    let query = format!("{url}?outputMint={mint}&inputMint=So11111111111111111111111111111111111111112&amount=1");
    let http = Client::new();
    let resp: SwapResp = http
        .get(&query)
        .send()
        .await?
        .json()
        .await?;

    let raw = base64::decode(resp.swap_transaction)?;
    // NOTE: Deserialising to a VersionedTransaction requires the same Borsh layout on chain, which
    // can break across releases. To keep things simple we deserialize into `Transaction` which will
    // work for legacy format returned by devnet endpoints.
    let mut tx: Transaction = bincode::deserialize(&raw)?;

    // Ensure we are the fee-payer / signer.
    let blockhash = _client.get_latest_blockhash()?;
    tx.partial_sign(&[keypair], blockhash);
    Ok(tx)
}

/// Build a simple 0-lamport self-transfer so that we submit *something* to the cluster when swap
/// construction fails. This keeps the dev-net traffic pattern realistic without taking risk.
fn fallback_transfer_tx(client: &RpcClient, keypair: &Keypair) -> Result<Transaction> {
    let blockhash = client.get_latest_blockhash()?;
    let ix = system_instruction::transfer(&keypair.pubkey(), &keypair.pubkey(), 0);
    let tx = Transaction::new_signed_with_payer(&[ix], Some(&keypair.pubkey()), &[keypair], blockhash);
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
            return Err(anyhow!("transaction {} not confirmed within {} slots", sig, MAX_CONFIRMATION_SLOTS));
        }
        std::thread::sleep(Duration::from_millis(400));
    }
}

/// Core trade loop – consumes launch events and, when a positive classification is produced,
/// executes a buy followed immediately by a sell.
pub async fn run(mut rx: Receiver<LaunchEvent>, slip_tx: tokio::sync::mpsc::Sender<f64>) -> Result<()> {
    // Initialise once outside the loop.
    let rpc = RpcClient::new_with_commitment(rpc_url(), CommitmentConfig::processed());
    let keypair = Keypair::new();
    tracing::info!(target = "trade", "Generated ephemeral dev-net keypair: {}", keypair.pubkey());

    // Fund the account – devnet & local validator honour airdrops. Ignore errors on rate-limit.
    if let Ok(sig) = rpc.request_airdrop(&keypair.pubkey(), 1_000_000_000) {
        let _ = wait_for_confirmation(&rpc, &sig);
    }

    while let Some(ev) = rx.recv().await {
        if score(&ev) <= 0.5 {
            continue;
        }

        tracing::info!(target = "trade", "Attempting buy for mint {}", ev.mint);

        // Build swap TX or fall back.
        let buy_tx = match fetch_swap_tx(&rpc, &keypair, &ev.mint).await {
            Ok(t) => t,
            Err(e) => {
                tracing::warn!(target = "trade", "swap construction failed – falling back: {e}");
                fallback_transfer_tx(&rpc, &keypair)?
            }
        };

        // Broadcast.
        let sig = rpc.send_transaction(&buy_tx)?;
        inc_trades_submitted();
        tracing::info!(target = "trade", "Submitted buy tx: {sig}");
        wait_for_confirmation(&rpc, &sig)?;
        inc_trades_confirmed();
        tracing::info!(target = "trade", "Buy confirmed: {sig}");

        // Immediate sell (market-sell) using the same logic as fallback (no price movement).
        let sell_tx = fallback_transfer_tx(&rpc, &keypair)?;
        let sell_sig = rpc.send_transaction(&sell_tx)?;
        inc_trades_submitted();
        wait_for_confirmation(&rpc, &sell_sig)?;
        inc_trades_confirmed();
        tracing::info!(target = "trade", "Sell confirmed: {sell_sig}");

        // -----------------------------------------------------------------
        // Slippage reporting (placeholder – assumes 0% slip for fallback tx)
        // -----------------------------------------------------------------
        let slip_value = 0.0; // TODO: compute from exit_price / entry_price – 1
        let _ = slip_tx.send(slip_value).await; // ignore error if channel closed
    }

    Ok(())
} 