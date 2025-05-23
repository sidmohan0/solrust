"""
Enhanced SolVolumeBot research layer with real data sources.
Replaces the original sol_volume_bot.py with production-ready components.
"""

import os
import time
import argparse
import yaml
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from dotenv import load_dotenv

from data_sources import (
    BirdeyeAPI, DexScreenerAPI, BinanceAPI, CoinGeckoAPI, MemecoinVolumeAggregator,
    calculate_rsi, DataSourceError
)
from data_storage import DataStorage, HistoricalDataCollector
from logging_config import setup_logging, configure_third_party_logging, PerformanceTimer


class EnhancedSolVolumeBot:
    """Enhanced trading bot with real data sources and proper infrastructure"""
    
    def __init__(self, config_path: str = "config.yaml"):
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Load environment variables
        load_dotenv()
        
        # Setup logging
        configure_third_party_logging()
        self.logger = setup_logging(self.config)
        
        # Initialize data storage
        storage_config = self.config.get('data', {}).get('storage', {})
        self.storage = DataStorage(
            storage_dir=storage_config.get('directory', 'data'),
            storage_format=storage_config.get('format', 'parquet')
        )
        
        # Initialize APIs
        self._init_apis()
        
        # Initialize data collector
        self.data_collector = HistoricalDataCollector(
            storage=self.storage,
            binance_api=self.binance_api,
            volume_aggregator=self.volume_aggregator
        )
        
        # Strategy parameters
        strategy_config = self.config.get('strategy', {})
        self.support_band = strategy_config.get('support_band', {'min': 160.0, 'max': 162.0})
        self.volume_drop_threshold = strategy_config.get('memecoin', {}).get('volume_drop_threshold', 0.30)
        self.rsi_threshold = strategy_config.get('rsi', {}).get('oversold_threshold', 45)
        self.rsi_period = strategy_config.get('rsi', {}).get('period', 14)
        
        # Data collection intervals
        intervals_config = self.config.get('data', {}).get('intervals', {})
        self.sol_candles_interval = intervals_config.get('sol_candles', 300)  # 5 minutes
        self.memecoin_volume_interval = intervals_config.get('memecoin_volume', 3600)  # 1 hour
        
        # Tracking variables
        self.price_history = []
        self.last_volume_check = None
        self.current_volume_data = {}
        
        self.logger.info("Enhanced SolVolumeBot initialized successfully")
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
            
    def _init_apis(self):
        """Initialize API clients"""
        # Birdeye API (primary memecoin volume source)
        birdeye_key = os.getenv('BIRDEYE_API_KEY')
        if birdeye_key:
            self.birdeye_api = BirdeyeAPI(api_key=birdeye_key)
            self.logger.info("Birdeye API initialized")
        else:
            self.birdeye_api = None
            self.logger.warning("Birdeye API key not found, using fallback only")
            
        # DexScreener API (fallback)
        self.dexscreener_api = DexScreenerAPI()
        self.logger.info("DexScreener API initialized")
        
        # SOL price APIs (Binance primary, CoinGecko fallback)
        self.binance_api = BinanceAPI()
        
        coingecko_key = os.getenv('COINGECKO_API_KEY')
        self.coingecko_api = CoinGeckoAPI(api_key=coingecko_key)
        
        self.logger.info("Price APIs initialized (Binance + CoinGecko fallback)")
        
        # Volume aggregator
        self.volume_aggregator = MemecoinVolumeAggregator(
            birdeye_api=self.birdeye_api,
            dexscreener_api=self.dexscreener_api
        )
        
    def collect_sol_price_data(self) -> Optional[float]:
        """Collect current SOL price and update history"""
        with PerformanceTimer(self.logger, "SOL price collection"):
            try:
                # Try Binance first
                current_price = self.binance_api.get_current_price("SOLUSDT")
                
                # Fallback to CoinGecko if Binance fails
                if current_price is None:
                    self.logger.debug("Binance failed, trying CoinGecko fallback")
                    current_price = self.coingecko_api.get_current_price("solana")
                
                if current_price is not None:
                    self.price_history.append(current_price)
                    
                    # Keep only the data we need for RSI calculation
                    max_history = self.rsi_period + 10  # Some buffer
                    if len(self.price_history) > max_history:
                        self.price_history = self.price_history[-max_history:]
                        
                    self.logger.debug(f"SOL price updated: ${current_price:.2f}")
                    return current_price
                else:
                    self.logger.warning("Failed to retrieve SOL price from all sources")
                    return None
                    
            except Exception as e:
                self.logger.error(f"Error collecting SOL price data: {e}")
                return None
                
    def collect_memecoin_volume_data(self) -> bool:
        """Collect current memecoin volume data"""
        with PerformanceTimer(self.logger, "memecoin volume collection"):
            try:
                volume_data = self.volume_aggregator.get_aggregate_volume()
                
                if volume_data:
                    # Store current data
                    self.current_volume_data = volume_data
                    
                    # Save to storage for historical analysis
                    self.storage.save_memecoin_volume(volume_data)
                    
                    self.logger.data_collection(
                        data_type="memecoin_volume",
                        record_count=len(volume_data),
                        collection_time_ms=0  # Timer will log actual time
                    )
                    
                    return True
                else:
                    self.logger.warning("No memecoin volume data retrieved")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Error collecting memecoin volume data: {e}")
                return False
                
    def calculate_volume_drop(self) -> Optional[float]:
        """Calculate aggregate memecoin volume drop"""
        if not self.current_volume_data:
            return None
            
        try:
            # Load historical volume data for comparison
            yesterday = datetime.now(timezone.utc).date()
            historical_df = self.storage.load_memecoin_volume(
                start_date=datetime.now(timezone.utc).replace(day=yesterday.day-1),
                end_date=datetime.now(timezone.utc)
            )
            
            if historical_df.empty:
                self.logger.debug("No historical volume data available for comparison")
                return None
                
            # Calculate weighted volume change
            total_current_volume = sum(data.volume_24h for data in self.current_volume_data.values())
            
            if total_current_volume == 0:
                return None
                
            # Simple approach: use volume_change_24h from API if available
            volume_changes = [
                data.volume_change_24h for data in self.current_volume_data.values()
                if data.volume_change_24h is not None
            ]
            
            if volume_changes:
                avg_volume_change = sum(volume_changes) / len(volume_changes)
                return avg_volume_change / 100  # Convert percentage to decimal
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error calculating volume drop: {e}")
            return None
            
    def calculate_rsi(self) -> Optional[float]:
        """Calculate RSI from price history"""
        if len(self.price_history) < self.rsi_period + 1:
            return None
            
        try:
            rsi_value = calculate_rsi(self.price_history, self.rsi_period)
            return rsi_value if not pd.isna(rsi_value) else None
        except Exception as e:
            self.logger.error(f"Error calculating RSI: {e}")
            return None
            
    def check_entry_conditions(self, current_price: float, volume_drop: Optional[float], 
                             rsi: Optional[float]) -> bool:
        """Check if entry conditions are met"""
        conditions = {
            'price_in_support': self.support_band['min'] <= current_price <= self.support_band['max'],
            'volume_drop_sufficient': volume_drop is not None and volume_drop <= -self.volume_drop_threshold,
            'rsi_oversold': rsi is not None and rsi < self.rsi_threshold
        }
        
        self.logger.debug(f"Entry conditions check: {conditions}")
        
        return all(conditions.values())
        
    def monitor_single_check(self) -> Dict[str, Any]:
        """Perform a single monitoring check"""
        results = {
            'timestamp': datetime.now(timezone.utc),
            'sol_price': None,
            'rsi': None,
            'volume_drop': None,
            'entry_signal': False
        }
        
        # Collect SOL price data
        current_price = self.collect_sol_price_data()
        if current_price is None:
            self.logger.warning("Failed to collect SOL price, skipping check")
            return results
            
        results['sol_price'] = current_price
        
        # Calculate RSI
        rsi = self.calculate_rsi()
        results['rsi'] = rsi
        
        # Collect memecoin volume data (less frequent)
        now = datetime.now(timezone.utc)
        if (self.last_volume_check is None or 
            (now - self.last_volume_check).total_seconds() >= self.memecoin_volume_interval):
            
            self.collect_memecoin_volume_data()
            self.last_volume_check = now
            
        # Calculate volume drop
        volume_drop = self.calculate_volume_drop()
        results['volume_drop'] = volume_drop
        
        # Check entry conditions
        entry_signal = self.check_entry_conditions(current_price, volume_drop, rsi)
        results['entry_signal'] = entry_signal
        
        # Log results
        if entry_signal:
            self.logger.trade_signal(
                signal_type="ENTRY",
                price=current_price,
                volume_drop=volume_drop or 0,
                rsi=rsi or 0,
                support_min=self.support_band['min'],
                support_max=self.support_band['max']
            )
            print(f"📈  ENTRY SIGNAL  {now:%H:%M:%S}  price=${current_price:.2f}  "
                  f"RSI={rsi:.1f}  volume_drop={volume_drop:.1%}")
        else:
            rsi_str = f"{rsi:.1f}" if rsi is not None else "N/A"
            volume_str = f"{volume_drop:.1%}" if volume_drop is not None else "N/A"
            print(f"{now:%H:%M:%S}  price=${current_price:.2f}  "
                  f"RSI={rsi_str}  volume_drop={volume_str}  entry={entry_signal}")
            
        return results
        
    def monitor_loop(self, sleep_seconds: Optional[int] = None):
        """Run continuous monitoring loop"""
        sleep_seconds = sleep_seconds or self.sol_candles_interval
        
        self.logger.info(f"Starting monitoring loop (interval: {sleep_seconds}s)")
        print("⏳ Enhanced monitoring started... Ctrl-C to stop")
        
        try:
            while True:
                try:
                    self.monitor_single_check()
                    time.sleep(sleep_seconds)
                    
                except KeyboardInterrupt:
                    self.logger.info("Monitoring stopped by user")
                    break
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(60)  # Wait before retrying
                    
        except Exception as e:
            self.logger.error(f"Fatal error in monitoring loop: {e}")
            raise
            
    def backfill_historical_data(self, days: int = 30):
        """Backfill historical data for analysis"""
        self.logger.info(f"Starting historical data backfill for {days} days")
        
        # Backfill SOL OHLCV data
        sol_success = self.data_collector.backfill_sol_ohlcv(days=days)
        
        # Backfill memecoin volume data
        volume_success = self.data_collector.backfill_memecoin_volume(days=min(days, 7))
        
        if sol_success and volume_success:
            self.logger.info("Historical data backfill completed successfully")
        else:
            self.logger.warning("Historical data backfill completed with some failures")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Enhanced SolVolumeBot Research Layer")
    parser.add_argument("--config", default="config.yaml", help="Configuration file path")
    parser.add_argument("--loop", action="store_true", help="Run continuous monitoring")
    parser.add_argument("--backfill", type=int, metavar="DAYS", 
                       help="Backfill historical data for N days")
    parser.add_argument("--test-apis", action="store_true", help="Test API connections")
    
    args = parser.parse_args()
    
    try:
        # Initialize bot
        bot = EnhancedSolVolumeBot(config_path=args.config)
        
        if args.test_apis:
            # Test API connections
            print("Testing API connections...")
            sol_price = bot.collect_sol_price_data()
            volume_success = bot.collect_memecoin_volume_data()
            
            print(f"SOL Price: ${sol_price:.2f}" if sol_price else "SOL Price: FAILED")
            print(f"Volume Data: {'SUCCESS' if volume_success else 'FAILED'}")
            
        elif args.backfill:
            # Backfill historical data
            bot.backfill_historical_data(days=args.backfill)
            
        elif args.loop:
            # Run continuous monitoring
            bot.monitor_loop()
            
        else:
            # Single check
            results = bot.monitor_single_check()
            print(f"Single check completed. Entry signal: {results['entry_signal']}")
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    exit(main())