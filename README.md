# SolVolumeBot

A two-part trading system that exploits the inverse correlation between Solana memecoin volume and the SOL price.

| Layer | Language | Purpose |
|-------|----------|---------|
| `research/` | Python | Back-tests, data exploration, parameter tuning, rapid prototyping. |
| `engine/`   | Rust   | Low-latency live trading bot: streams data, computes signals, places orders. |

## 1 . Why this repo exists
Meme coins often soak up liquidity on Solana.  
When their volume nosedives, capital rotates back into SOL and the price pops.  
We quantify that edge in Python, then trade it in Rust—the right tool for each job.

## 2 . Quick start

### Prerequisites
* Python 3.11+
* Rust 1.77+ (stable) with `cargo`
* `docker` (optional, for one-shot runs)

### Clone
```bash
git clone https://github.com/YOUR_GH_HANDLE/sol-volume-bot.git
cd sol-volume-bot
