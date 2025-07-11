use anyhow::Result;
use clap::{Parser, Subcommand};
use executor::risk;
use executor::{metrics, trader, ws_feed};
use tracing_subscriber::EnvFilter;

#[derive(Parser)]
#[command(name = "executor")]
#[command(about = "Meme sniper executor with trading capabilities")]
#[command(long_about = "
The executor is the core trading component that processes market events,
executes trades, and manages risk. It supports both live trading and
replay mode for testing.

URL Configuration Priority:
1. --solana-url CLI argument (highest priority)
2. SOLANA_RPC_URL environment variable
3. SOLANA_URL environment variable  
4. RPC_URL environment variable
5. Default: https://api.devnet.solana.com")]
struct Cli {
    /// Solana RPC URL to use (overrides SOLANA_RPC_URL env var)
    #[arg(long)]
    solana_url: Option<String>,

    /// Replay mode for testing with mock data
    #[arg(long)]
    replay: Option<String>,

    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Subcommand)]
enum Commands {}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    // Set SOLANA_RPC_URL if provided via CLI
    if let Some(url) = &cli.solana_url {
        std::env::set_var("SOLANA_RPC_URL", url);
        tracing::info!("Using Solana RPC URL from CLI: {}", url);
    }

    // Track process (re)starts.
    metrics::inc_restart();

    let (feed_tx, feed_rx) = tokio::sync::mpsc::channel(10_000);

    // risk slippage channel
    let (slip_tx, slip_rx) = tokio::sync::mpsc::channel(256);

    let replay_file = cli.replay.clone();
    if let Some(file) = replay_file {
        tokio::spawn(ws_feed::run_replay(file, feed_tx));
    } else {
        tokio::spawn(ws_feed::run(feed_tx));
    }
    
    tokio::spawn(trader::run(feed_rx, slip_tx.clone()));

    // --- Risk management ---------------------------------------------------
    let (kill_tx, mut kill_rx) = tokio::sync::broadcast::channel(16);
    tokio::spawn(async move {
        if let Err(e) = risk::run(kill_tx, slip_rx).await {
            tracing::error!(target = "risk", "risk module exited: {e}");
        }
    });

    // Listener task for kill-switch events.  On the first event the process
    // terminates with a non-zero exit code after logging a CRITICAL message.
    tokio::spawn(async move {
        use executor::risk::KillSwitch;
        use tokio::time::{sleep, Duration};

        if let Ok(kind) = kill_rx.recv().await {
            let label = match kind {
                KillSwitch::EquityFloor => "equity_floor",
                KillSwitch::Slippage => "slippage",
                KillSwitch::PortfolioStopLoss => "portfolio_stop_loss",
            };
            metrics::inc_killswitch(label);
            tracing::error!(
                target = "killswitch",
                "CRITICAL kill-switch triggered: {:?}",
                kind
            );
            sleep(Duration::from_millis(100)).await;
            std::process::exit(1);
        }
    });

    tokio::spawn(async {
        metrics::serve_prometheus().await;
    });
    std::future::pending::<()>().await;
    Ok(())
}
