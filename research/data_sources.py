"""
Enhanced data sources for SolVolumeBot research layer.
Replaces mock APIs with real endpoints for memecoin volume and SOL price data.
"""

import time
import logging
import requests
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass


@dataclass
class VolumeData:
    """Memecoin volume data structure"""
    volume_24h: float
    volume_change_24h: float
    price_change_24h: float
    timestamp: datetime
    source: str


@dataclass
class OHLCVData:
    """OHLCV candle data structure"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str


class DataSourceError(Exception):
    """Custom exception for data source errors"""
    pass


class BirdeyeAPI:
    """Birdeye API client for Solana memecoin volume data"""
    
    def __init__(self, api_key: str, base_url: str = "https://public-api.birdeye.so"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-KEY': api_key,
            'x-chain': 'solana',
            'accept': 'application/json'
        })
        self.last_request_time = 0
        self.min_request_interval = 0.6  # 100 requests/minute
        
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
        
    def get_token_volume(self, token_address: str) -> Optional[VolumeData]:
        """Get 24h volume data for a specific token"""
        self._rate_limit()
        
        try:
            url = f"{self.base_url}/defi/price"
            params = {'list_address': token_address}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'data' not in data or not data['data']:
                return None
                
            token_data = data['data']
            return VolumeData(
                volume_24h=float(token_data.get('volume24h', 0)),
                volume_change_24h=float(token_data.get('volumeChange24h', 0)),
                price_change_24h=float(token_data.get('priceChange24h', 0)),
                timestamp=datetime.now(timezone.utc),
                source='birdeye'
            )
            
        except Exception as e:
            logging.error(f"Birdeye API error for {token_address}: {e}")
            return None
            
    def get_top_tokens_by_volume(self, limit: int = 50) -> List[Dict]:
        """Get top tokens by 24h volume"""
        self._rate_limit()
        
        try:
            url = f"{self.base_url}/defi/tokenlist"
            params = {
                'sort_by': 'volume24hUSD',
                'sort_type': 'desc',
                'limit': limit
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', {}).get('items', [])
            
        except Exception as e:
            logging.error(f"Birdeye top tokens API error: {e}")
            return []


class DexScreenerAPI:
    """DexScreener API client as fallback for volume data"""
    
    def __init__(self, base_url: str = "https://api.dexscreener.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 60 requests/minute
        
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
        
    def get_token_volume(self, token_address: str) -> Optional[VolumeData]:
        """Get volume data for a specific token"""
        self._rate_limit()
        
        try:
            url = f"{self.base_url}/latest/dex/tokens/{token_address}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            pairs = data.get('pairs', [])
            
            if not pairs:
                return None
                
            # Aggregate volume from all pairs
            total_volume_24h = sum(float(pair.get('volume', {}).get('h24', 0)) for pair in pairs)
            
            # Use first pair for price change data
            first_pair = pairs[0]
            price_change_24h = float(first_pair.get('priceChange', {}).get('h24', 0))
            
            return VolumeData(
                volume_24h=total_volume_24h,
                volume_change_24h=0,  # Not provided by DexScreener
                price_change_24h=price_change_24h,
                timestamp=datetime.now(timezone.utc),
                source='dexscreener'
            )
            
        except Exception as e:
            logging.error(f"DexScreener API error for {token_address}: {e}")
            return None


class CoinGeckoAPI:
    """CoinGecko API client for SOL price data (fallback)"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.coingecko.com/api/v3"):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({'x-cg-demo-api-key': api_key})
        self.last_request_time = 0
        self.min_request_interval = 4.0  # 15 requests/minute for free tier
        
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
        
    def get_current_price(self, coin_id: str = "solana") -> Optional[float]:
        """Get current SOL price from CoinGecko"""
        self._rate_limit()
        
        try:
            url = f"{self.base_url}/simple/price"
            params = {'ids': coin_id, 'vs_currencies': 'usd'}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return float(data[coin_id]['usd'])
            
        except Exception as e:
            logging.error(f"CoinGecko price API error: {e}")
            return None


class BinanceAPI:
    """Enhanced Binance API client for SOL OHLCV data"""
    
    def __init__(self, base_url: str = "https://api.binance.com/api/v3"):
        self.base_url = base_url
        self.session = requests.Session()
        self.last_request_time = 0
        self.min_request_interval = 0.05  # 1200 requests/minute
        
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
        
    def get_current_price(self, symbol: str = "SOLUSDT") -> Optional[float]:
        """Get current SOL price"""
        self._rate_limit()
        
        try:
            url = f"{self.base_url}/ticker/price"
            params = {'symbol': symbol}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return float(data['price'])
            
        except Exception as e:
            logging.error(f"Binance price API error: {e}")
            return None
            
    def get_klines(self, symbol: str = "SOLUSDT", interval: str = "5m", 
                   limit: int = 100) -> List[OHLCVData]:
        """Get OHLCV kline data for SOL"""
        self._rate_limit()
        
        try:
            url = f"{self.base_url}/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            candles = []
            
            for kline in data:
                candles.append(OHLCVData(
                    timestamp=datetime.fromtimestamp(kline[0] / 1000, timezone.utc),
                    open=float(kline[1]),
                    high=float(kline[2]),
                    low=float(kline[3]),
                    close=float(kline[4]),
                    volume=float(kline[5]),
                    source='binance'
                ))
                
            return candles
            
        except Exception as e:
            logging.error(f"Binance klines API error: {e}")
            return []


class MemecoinVolumeAggregator:
    """Aggregates memecoin volume from multiple sources"""
    
    # Popular Solana memecoins to monitor
    MEMECOIN_ADDRESSES = [
        "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # Bonk
        "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr",  # POPCAT  
        "CATSUi6yGJhFt6SQTrwJDj8P8VJj5kcWA1pzGJL4M4K2",  # CATSU
        "AMDHGgHcUqNGrA4MqKGjJVqU4JF9B5ZA3Cw4r5jTpump",  # Example pump.fun token
    ]
    
    def __init__(self, birdeye_api: Optional[BirdeyeAPI] = None, 
                 dexscreener_api: Optional[DexScreenerAPI] = None):
        self.birdeye = birdeye_api
        self.dexscreener = dexscreener_api or DexScreenerAPI()
        
    def get_aggregate_volume(self, addresses: Optional[List[str]] = None) -> Dict[str, VolumeData]:
        """Get volume data for multiple memecoin addresses"""
        addresses = addresses or self.MEMECOIN_ADDRESSES
        results = {}
        
        for address in addresses:
            # Try primary source first
            volume_data = None
            if self.birdeye:
                volume_data = self.birdeye.get_token_volume(address)
                
            # Fallback to secondary source
            if not volume_data:
                volume_data = self.dexscreener.get_token_volume(address)
                
            if volume_data:
                results[address] = volume_data
                
        return results
        
    def calculate_total_volume_change(self, addresses: Optional[List[str]] = None) -> float:
        """Calculate aggregate volume change across tracked memecoins"""
        volume_data = self.get_aggregate_volume(addresses)
        
        if not volume_data:
            return 0.0
            
        # Weight by 24h volume and calculate weighted average change
        total_volume = sum(data.volume_24h for data in volume_data.values())
        
        if total_volume == 0:
            return 0.0
            
        weighted_change = sum(
            (data.volume_24h / total_volume) * data.volume_change_24h 
            for data in volume_data.values()
            if data.volume_change_24h is not None
        )
        
        return weighted_change / 100  # Convert percentage to decimal


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """Calculate RSI from price series"""
    if len(prices) < period + 1:
        return np.nan
        
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    
    if avg_loss == 0:
        return 100.0
        
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi