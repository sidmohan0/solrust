use crate::config::Config;
use anyhow::Result;
use axum::{routing::get, Router};

pub struct TelemetryServer {
    _config: Config,
}

impl TelemetryServer {
    pub async fn new(config: &Config) -> Result<Self> {
        Ok(Self {
            _config: config.clone(),
        })
    }

    pub async fn run(self) -> Result<()> {
        // TODO: Implement telemetry server with Prometheus metrics
        let app = Router::new()
            .route("/metrics", get(metrics_handler))
            .route("/health", get(health_handler));

        let listener = tokio::net::TcpListener::bind("0.0.0.0:8080").await?;
        axum::serve(listener, app).await?;
        Ok(())
    }
}

async fn metrics_handler() -> &'static str {
    // TODO: Return Prometheus metrics
    "# HELP sol_volume_bot_status Bot status\n# TYPE sol_volume_bot_status gauge\nsol_volume_bot_status 1\n"
}

async fn health_handler() -> &'static str {
    "OK"
}
