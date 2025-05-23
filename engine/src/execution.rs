use crate::config::Config;
use anyhow::Result;

pub struct Executor {
    _config: Config,
}

impl Executor {
    pub async fn new(config: &Config) -> Result<Self> {
        Ok(Self {
            _config: config.clone(),
        })
    }

    pub async fn run(self) -> Result<()> {
        // TODO: Implement order executor
        // This is a stub implementation for now
        tokio::time::sleep(tokio::time::Duration::from_secs(3600)).await;
        Ok(())
    }
}
