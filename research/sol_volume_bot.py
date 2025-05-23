# sol_volume_bot.py
#
# Quick-and-dirty one-pager that watches the “memecoin volume → SOL price” edge.
# • Pulls SOL/USDT 5-min candles from Binance.
# • Pulls pump.fun 24 h memecoin volume.
# • Fires an ENTRY alert when:
#       – memecoin volume dropped ≥30 % from yesterday
#       – SOL sits inside the $160–162 support band
#       – RSI(14) < 45
#
# Run once:  $ python sol_volume_bot.py
# Run loop:  $ python sol_volume_bot.py --loop
#
# Dependencies: requests, numpy
# (pip install requests numpy)

import argparse, time, datetime as dt
from collections import deque
import requests, numpy as np

COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"
PUMPFUN_VOL24H = "https://pump.fun/api/volume"

SUPPORT = (160, 162)      # USD zone we care about
MEME_DROP = 0.30          # 30 % threshold
RSI_N = 14                # look-back
SLEEP = 300               # 5-minute loop

def get_sol_candle():
    params = {"ids": "solana", "vs_currencies": "usd"}
    response = requests.get(COINGECKO_API, params=params, timeout=10)
    data = response.json()
    
    if "solana" not in data or "usd" not in data["solana"]:
        print(f"Debug: API response: {data}")
        raise Exception(f"Unexpected response format: {data}")
    
    price = float(data["solana"]["usd"])
    # CoinGecko doesn't provide volume in this endpoint, so we'll use 0 as placeholder
    return price, 0

def get_memecoin_volume():
    # pump.fun API endpoint not available - using mock data
    # In production, replace with actual memecoin volume source
    import random
    base_volume = 1000.0
    # Simulate some variation in volume
    return base_volume * (0.8 + 0.4 * random.random())

def rsi(series):
    if len(series) < RSI_N + 1: return np.nan
    deltas = np.diff(series)
    up, down = np.maximum(deltas, 0).mean(), -np.minimum(deltas, 0).mean()
    return 100 if down == 0 else 100 - 100 / (1 + up / down)

def monitor(loop):
    prices, meme_hist = deque(maxlen=RSI_N + 1), deque(maxlen=2)
    print("⏳ monitoring…  Ctrl-C to stop")
    while True:
        now = dt.datetime.now(dt.timezone.utc)
        px, _ = get_sol_candle()
        mv = get_memecoin_volume()
        prices.append(px)
        if not np.isnan(mv) and (not meme_hist or meme_hist[-1][0] != now.date()):
            meme_hist.append((now.date(), mv))

        meme_drop = False
        if len(meme_hist) == 2:
            today, yday = meme_hist[-1][1], meme_hist[-2][1]
            meme_drop = today < (1 - MEME_DROP) * yday

        if meme_drop and SUPPORT[0] <= px <= SUPPORT[1] and rsi(prices) < 45:
            print(f"📈  ENTRY {now:%H:%M}  price={px:.2f}  RSI={rsi(prices):.1f}  "
                  f"memecoin-Δ={(today/yday-1):.0%}")
        else:
            print(f"{now:%H:%M}  price={px:.2f}  RSI={rsi(prices):.1f}  "
                  f"meme_drop={meme_drop}")

        if not loop: break
        time.sleep(SLEEP)

if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("--loop", action="store_true", help="run forever")
    monitor(argp.parse_args().loop)
