use anyhow::Result;
use tracing::{info, warn};

mod account;
mod config;
mod data;
mod execution;
mod signal;
mod telemetry;

use account::AccountManager;
use config::Config;
use data::DataMux;
use execution::Executor;
use signal::SignalEngine;
use telemetry::TelemetryServer;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt().with_target(false).json().init();

    info!("Starting SolVolumeBot trading engine");

    // Load configuration
    let config = Config::load().await?;
    info!("Configuration loaded successfully");

    // Start telemetry server
    let telemetry = TelemetryServer::new(&config).await?;
    let telemetry_handle = tokio::spawn(async move {
        if let Err(e) = telemetry.run().await {
            warn!("Telemetry server error: {}", e);
        }
    });

    // Initialize core components
    let data_mux = DataMux::new(&config).await?;
    let signal_engine = SignalEngine::new(&config).await?;
    let executor = Executor::new(&config).await?;
    let account_manager = AccountManager::new(&config).await?;

    info!("All components initialized, starting main loop");

    // Main event loop using tokio::select!
    tokio::select! {
        result = data_mux.run() => {
            warn!("DataMux terminated: {:?}", result);
        }
        result = signal_engine.run() => {
            warn!("SignalEngine terminated: {:?}", result);
        }
        result = executor.run() => {
            warn!("Executor terminated: {:?}", result);
        }
        result = account_manager.run() => {
            warn!("AccountManager terminated: {:?}", result);
        }
        _ = tokio::signal::ctrl_c() => {
            info!("Received shutdown signal");
        }
    }

    // Graceful shutdown
    info!("Shutting down SolVolumeBot");
    telemetry_handle.abort();

    Ok(())
}
