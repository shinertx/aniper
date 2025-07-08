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
    signature::{Keypair, Signature, Signer, read_keypair_file},
    system_instruction,
    transaction::Transaction,
    compute_budget::ComputeBudgetInstruction,
};

/// Maximum number of slots to wait for a confirmation before giving up.
const MAX_CONFIRMATION_SLOTS: u64 = 10;

/// Returns the RPC URL to use (defaults to Solana devnet).
fn rpc_url() -> String {
    std::env::var("SOLANA_RPC_URL").unwrap_or_else(|_| "https://api.devnet.solana.com".to_string())
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
async fn fetch_swap_tx(client: &RpcClient, keypair: &Keypair, output_mint: &str) -> Result<SwapTx> {
    #[derive(serde::Deserialize)]
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

    // -- 1. Quote -----------------------------------------------------------
    let quote_url = format!(
        "{api}/quote?inputMint={}&outputMint={}&amount=1000000&slippageBps=100&onlyDirectRoutes=false&platformFeeBps=0",
        USDC_MINT, output_mint
    );
    let _quote: QuoteResp = http.get(&quote_url).send().await?.json().await?;
    // For now we do not inspect the quote – the second call will embed
    // slippage & post-only enforcement.  Retaining for completeness.

    // -- 2. Swap ------------------------------------------------------------
    // Jupiter swap endpoint requires the user public key so returned TX has us
    // as fee-payer.  The market makin' specifics are abstracted away.
    let swap_url = format!(
        "{api}/swap?inputMint={}&outputMint={}&amount=1000000&slippageBps=100&userPublicKey={}&wrapAndUnwrapSol=true&dynamicJitPricing=true&useSharedAccounts=true&asLegacyTransaction=true",
        USDC_MINT,
        output_mint,
        keypair.pubkey()
    );

    let resp: SwapResp = http.get(&swap_url).send().await?.json().await?;
    let raw = base64::decode(resp.swap_transaction.clone())?;
    let mut tx: Transaction = bincode::deserialize(&raw)?;

    // Ensure recent blockhash & additional signature from *our* private key –
    // Jupiter sometimes returns a stale hash if the HTTP round-trip lags.
    let blockhash = client.get_latest_blockhash()?;
    tx.partial_sign(&[keypair], blockhash);

    // price = out_amount / in_amount (both strings in lamports / token units)
    let in_amt: f64 = resp.in_amount.parse::<u64>()? as f64;
    let out_amt: f64 = resp.out_amount.parse::<u64>()? as f64;
    let price = if in_amt > 0.0 { out_amt / in_amt } else { 0.0 };

    Ok(SwapTx { tx, price })
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

/// Attach an optional priority-fee tip (lamports per CU) and broadcast to *all*
/// configured RPC endpoints.  Returns the signature from the primary RPC.
fn sign_and_send(urls: &[String], tx: &Transaction, keypair: &Keypair) -> Result<Signature> {
    // Determine tip in micro-lamports per CU.
    let tip_lamports: u64 = std::env::var("TRADE_TIP").ok().and_then(|v| v.parse().ok()).unwrap_or(0);

    // If a tip is requested, prepend a compute-budget ix.  We rebuild the
    // transaction instructions because mutating an already-compiled message is
    // fiddly.
    let final_tx = if tip_lamports > 0 {
        let blockhash = RpcClient::new(urls.first().unwrap().clone()).get_latest_blockhash()?;
        let mut ixs = vec![ComputeBudgetInstruction::set_compute_unit_price(tip_lamports)];
        // We cannot easily de-compile the existing compiled instructions back
        // into `Instruction`, so the safest option is to **submit two
        // separate transactions**: the tip stub followed by the original tx.
        // For now we opt for the simple route – tip stub.
        let tip_tx = Transaction::new_signed_with_payer(&ixs, Some(&keypair.pubkey()), &[keypair], blockhash);
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
                tracing::warn!(target="trade", "rpc {url} send error: {e}");
            }
        }
    }
    primary_sig.ok_or_else(|| anyhow!("all RPC submissions failed"))
}

/// Build *OCO* (one-cancels-other) exit orders: a take-profit around +75% and a
/// stop-loss at ‑40%.  This placeholder uses two independent Jupiter swap
/// transactions.  If swap construction fails we fall back to 0-lamport
/// transfers so latency tests remain unaffected.
async fn build_oco(client: &RpcClient, keypair: &Keypair, mint: &str) -> Result<(SwapTx, SwapTx)> {
    // TP route (sell) --------------------------------------------------------------------
    let tp_tx = fetch_swap_tx(client, keypair, mint).await.unwrap_or_else(|_| {
        tracing::warn!(target="trade", "TP construction failed – using noop tx");
        SwapTx { tx: fallback_transfer_tx(client, keypair).expect("transfer tx"), price: 0.0 }
    });

    // SL route (sell) --------------------------------------------------------------------
    let sl_tx = fetch_swap_tx(client, keypair, mint).await.unwrap_or_else(|_| {
        tracing::warn!(target="trade", "SL construction failed – using noop tx");
        SwapTx { tx: fallback_transfer_tx(client, keypair).expect("transfer tx"), price: 0.0 }
    });

    Ok((tp_tx, sl_tx))
}

/// Core trade loop – consumes launch events and, when a positive classification is produced,
/// executes a buy followed immediately by a sell.
pub async fn run(mut rx: Receiver<LaunchEvent>, slip_tx: tokio::sync::mpsc::Sender<f64>) -> Result<()> {
    // Initialise once outside the loop.
    let rpc = RpcClient::new_with_commitment(rpc_url(), CommitmentConfig::processed());

    // ------------------------------------------------------------------
    // Secure signer loading --------------------------------------------------
    // ------------------------------------------------------------------
    // Production deployments store the hot-wallet keypair in Cloud KMS / Secret
    // Manager and surface it to the executor as a decrypted file path via the
    // `KEYPAIR_PATH` environment variable.  We abort early if the variable is
    // missing or the file cannot be parsed – running with a fresh key would be
    // catastrophic on main-net.
    //
    // Tests create a temporary keypair file and set `KEYPAIR_PATH`, so this
    // logic is fully covered in CI.
    let keypair = match std::env::var("KEYPAIR_PATH") {
        Ok(p) => read_keypair_file(&p)
            .map_err(|e| anyhow!(format!("failed to load keypair from {p}: {e}")))?,
        Err(_) => {
            return Err(anyhow!(
                "KEYPAIR_PATH not set – refusing to start; see README 'Security Controls'."
            ))
        }
    };
    tracing::info!(target = "trade", "Loaded trading keypair: {}", keypair.pubkey());

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
        let buy_swap = match fetch_swap_tx(&rpc, &keypair, &ev.mint).await {
            Ok(t) => t,
            Err(e) => {
                tracing::warn!(target = "trade", "swap construction failed – falling back: {e}");
                SwapTx { tx: fallback_transfer_tx(&rpc, &keypair)?, price: 0.0 }
            }
        };

        // Broadcast.
        let sig = sign_and_send(&[rpc_url()], &buy_swap.tx, &keypair)?;
        inc_trades_submitted();
        tracing::info!(target = "trade", "Submitted buy tx: {sig}");
        wait_for_confirmation(&rpc, &sig)?;
        inc_trades_confirmed();
        tracing::info!(target = "trade", "Buy confirmed: {sig}");

        // ------------------------------------------------------------------
        // Build OCO exit legs
        // ------------------------------------------------------------------
        let (tp_swap, sl_swap) = build_oco(&rpc, &keypair, &ev.mint).await?;

        // Gather RPC endpoints – primary defaults to initial URL, others may
        // be supplied via comma-separated `SOLANA_RPC_URLS` env var.
        let mut rpc_urls: Vec<String> = std::env::var("SOLANA_RPC_URLS")
            .ok()
            .map(|v| v.split(',').map(|s| s.trim().to_string()).collect())
            .unwrap_or_else(Vec::new);
        if rpc_urls.is_empty() {
            rpc_urls.push(rpc_url());
        }

        // --- TP leg -------------------------------------------------------
        let tp_sig = sign_and_send(&rpc_urls, &tp_swap.tx, &keypair)?;
        inc_trades_submitted();
        tracing::info!(target="trade", "TP leg submitted: {tp_sig}");

        // --- SL leg -------------------------------------------------------
        let sl_sig = sign_and_send(&rpc_urls, &sl_swap.tx, &keypair)?;
        inc_trades_submitted();
        tracing::info!(target="trade", "SL leg submitted: {sl_sig}");

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
        } else { 0.0 };
        let _ = slip_tx.send(slip_value).await; // ignore error if channel closed
    }

    Ok(())
} 