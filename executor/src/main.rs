use anyhow::Result;
use tracing_subscriber::EnvFilter;
use executor::{metrics, trader, ws_feed};
use executor::risk;

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    // Track process (re)starts.
    metrics::inc_restart();

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