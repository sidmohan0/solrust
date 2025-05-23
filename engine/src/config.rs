use anyhow::Result;
use serde::Deserialize;

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub struct Config {
    pub exchange: ExchangeConfig,
    pub symbols: SymbolsConfig,
    pub thresholds: ThresholdsConfig,
    pub risk: RiskConfig,
}

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub struct ExchangeConfig {
    pub binance_key: String,
    pub binance_sec: String,
}

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub struct SymbolsConfig {
    pub spot: String,
    pub hedge: String,
}

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub struct ThresholdsConfig {
    pub meme_drop_pct: f64,
    pub rsi_max: f64,
    pub support_low: f64,
    pub support_high: f64,
}

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub struct RiskConfig {
    pub max_trade_risk: f64,
    pub stop_loss: f64,
}

impl Config {
    pub async fn load() -> Result<Self> {
        // TODO: Implement config loading from TOML and .env
        // This is a stub implementation for now
        Ok(Config {
            exchange: ExchangeConfig {
                binance_key: "test".to_string(),
                binance_sec: "test".to_string(),
            },
            symbols: SymbolsConfig {
                spot: "SOLUSDT".to_string(),
                hedge: "SOLUSD_PERP".to_string(),
            },
            thresholds: ThresholdsConfig {
                meme_drop_pct: 0.30,
                rsi_max: 45.0,
                support_low: 160.0,
                support_high: 162.0,
            },
            risk: RiskConfig {
                max_trade_risk: 0.05,
                stop_loss: 155.0,
            },
        })
    }
}
