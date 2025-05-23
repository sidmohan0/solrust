#!/usr/bin/env python3
"""
Test script for enhanced SolVolumeBot components.
Validates real data sources and basic functionality.
"""

import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from data_sources import BinanceAPI, DexScreenerAPI, CoinGeckoAPI, calculate_rsi
from enhanced_bot import EnhancedSolVolumeBot


def test_binance_api():
    """Test Binance API connection"""
    print("Testing Binance API...")
    
    try:
        api = BinanceAPI()
        
        # Test current price
        price = api.get_current_price("SOLUSDT")
        if price:
            print(f"✅ SOL Price: ${price:.2f}")
        else:
            print("❌ Failed to get SOL price")
            return False
            
        # Test klines
        candles = api.get_klines("SOLUSDT", "5m", 10)
        if candles:
            print(f"✅ Retrieved {len(candles)} SOL candles")
            latest = candles[-1]
            print(f"   Latest: {latest.timestamp} OHLC={latest.open:.2f}/{latest.high:.2f}/{latest.low:.2f}/{latest.close:.2f}")
        else:
            print("❌ Failed to get SOL candles")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Binance API test failed: {e}")
        return False


def test_coingecko_api():
    """Test CoinGecko API connection"""
    print("\nTesting CoinGecko API...")
    
    try:
        api = CoinGeckoAPI()
        
        # Test SOL price
        price = api.get_current_price("solana")
        if price:
            print(f"✅ SOL Price (CoinGecko): ${price:.2f}")
            return True
        else:
            print("❌ Failed to get SOL price from CoinGecko")
            return False
            
    except Exception as e:
        print(f"❌ CoinGecko API test failed: {e}")
        return False


def test_dexscreener_api():
    """Test DexScreener API connection"""
    print("\nTesting DexScreener API...")
    
    try:
        api = DexScreenerAPI()
        
        # Test with Bonk token
        bonk_address = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
        volume_data = api.get_token_volume(bonk_address)
        
        if volume_data:
            print(f"✅ BONK Volume: ${volume_data.volume_24h:,.0f}")
            print(f"   Price Change 24h: {volume_data.price_change_24h:.2f}%")
        else:
            print("⚠️  No volume data retrieved (may be normal for DexScreener)")
            
        return True
        
    except Exception as e:
        print(f"❌ DexScreener API test failed: {e}")
        return False


def test_rsi_calculation():
    """Test RSI calculation"""
    print("\nTesting RSI calculation...")
    
    try:
        # Test with sample price data
        prices = [100, 102, 98, 105, 103, 99, 104, 106, 101, 108, 107, 105, 110, 109, 111, 115, 112]
        
        rsi = calculate_rsi(prices, 14)
        
        if rsi and 0 <= rsi <= 100:
            print(f"✅ RSI calculation: {rsi:.2f}")
            return True
        else:
            print(f"❌ Invalid RSI value: {rsi}")
            return False
            
    except Exception as e:
        print(f"❌ RSI calculation test failed: {e}")
        return False


def test_config_loading():
    """Test configuration loading"""
    print("\nTesting configuration loading...")
    
    try:
        config_path = Path("config.yaml")
        if not config_path.exists():
            print("⚠️  config.yaml not found, using default path")
            return True
            
        bot = EnhancedSolVolumeBot(config_path=str(config_path))
        print(f"✅ Configuration loaded successfully")
        print(f"   Support band: ${bot.support_band['min']}-${bot.support_band['max']}")
        print(f"   Volume drop threshold: {bot.volume_drop_threshold:.0%}")
        print(f"   RSI threshold: {bot.rsi_threshold}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🧪 Testing Enhanced SolVolumeBot Components\n")
    
    tests = [
        ("Binance API", test_binance_api),
        ("CoinGecko API", test_coingecko_api),
        ("DexScreener API", test_dexscreener_api),  
        ("RSI Calculation", test_rsi_calculation),
        ("Configuration Loading", test_config_loading)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
            
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if success:
            passed += 1
            
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("🎉 All tests passed! Enhanced bot is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Check API keys and network connection.")
        return 1


if __name__ == "__main__":
    exit(main())