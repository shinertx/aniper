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
    #[arg(long, env = "SOLANA_RPC_URL")]
    solana_url: Option<String>,

    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Subcommand)]
enum Commands {
    /// Replay mode for testing with mock data
    ///
    /// This mode loads historical trading events from a JSON file and processes
    /// them without connecting to live market feeds. Useful for testing and
    /// backtesting trading strategies.
    Replay {
        /// Path to mock data JSON file (e.g., tests/data/mock_data.json)
        file: String,
    },
}

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

    match cli.command {
        Some(Commands::Replay { file }) => {
            tracing::info!("Starting in replay mode with file: {}", file);
            // For now, just log that we're in replay mode and verify file exists
            if !std::path::Path::new(&file).exists() {
                tracing::error!("Replay file not found: {}", file);
                return Err(anyhow::anyhow!("Replay file not found: {}", file));
            }
            // The actual replay logic would be implemented later
            std::thread::sleep(std::time::Duration::from_secs(1));
            tracing::info!("Replay mode completed");
            return Ok(());
        }
        None => {
            // Normal execution mode
            tracing::info!("Starting normal execution mode");
        }
    }

    let (feed_tx, feed_rx) = tokio::sync::mpsc::channel(10_000);

    // risk slippage channel
    let (slip_tx, slip_rx) = tokio::sync::mpsc::channel(256);

    tokio::spawn(ws_feed::run(feed_tx));
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

        while let Ok(kind) = kill_rx.recv().await {
            let label = match kind {
                KillSwitch::EquityFloor => "equity_floor",
                KillSwitch::Slippage => "slippage",
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

    metrics::serve_prometheus();
    futures::future::pending::<()>().await;
    Ok(())
}
