### Rust Engine Requirements

*A single page of essentials, written so a busy trader or engineer can glance once and know what to build.*

---

#### 1 . Purpose

Run unattended, low-latency execution of the “memecoin-volume → SOL pump” edge found in Python research.
Tasks:

1. **Listen** to live data streams (Solana DEX, pump.fun, Binance/other CEX).
2. **Compute** signals in <1 ms/event.
3. **Act**: place, amend, and cancel orders fast enough to live inside a 400 ms Solana block.
4. **Guard** capital with position sizing, stops, and exposure rules.
5. **Record** everything (fills, PnL, metrics) for audit and restart.

---

#### 2 . Functional Requirements

| Area                    | Requirement                                                                                                                                                                                                                                |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Data Ingest**         | • Subscribe to Solana RPC *slot* + Jupiter/Helius L2 order-book websockets.<br>• Pull pump.fun 24 h volume every 60 s (REST).<br>• Poll DeFiLlama aggregate volume every 5 min.<br>• Optional: Binance/Kraken depth snapshot every 250 ms. |
| **Signal Engine**       | • Detect >30 % day-over-day memecoin volume drop.<br>• Track rolling RSI(14) on SOL 5-min closes.<br>• Confirm price in \$160–162 band.<br>• Emit *ENTER*, *EXIT*, or *NO-OP* events.                                                      |
| **Risk Manager**        | • Max 5 % of portfolio at risk per trade.<br>• Global stop-loss at \$155.<br>• Pause trading after 4 consecutive losers.<br>• Block trading when `news_lock = true` in config.                                                             |
| **Execution**           | • Scale into position with 3 IOC/FOK tranches over 2–4 h (configurable).<br>• Place TP1/TP2 limit sells and a protective stop on entry fill.<br>• Cancel & re-post limits every new slot if top-of-book shifts >0.1 %.                     |
| **Persistence**         | • Use SQLite for orders, fills, equity curve.<br>• Write flat CSV back-ups hourly.                                                                                                                                                         |
| **Monitoring / Alerts** | • Expose Prometheus `/metrics` (latency, fills, PnL, mem usage).<br>• Log to `stdout` in JSON (one line per event).<br>• Send Telegram/Slack alert on *ENTER*, *STOP*, fatal error.                                                        |

---

#### 3 . Non-Functional Requirements

| Aspect              | Target                                                      |
| ------------------- | ----------------------------------------------------------- |
| **Latency**         | <2 ms median from market event → order send.                |
| **Throughput**      | 5 k msgs/s sustained without GC pauses.                     |
| **Reliability**     | Automatic reconnect & state sync after network drop.        |
| **Security**        | Exchange keys read once at start from `.env`, never logged. |
| **Resource Budget** | ≤150 MB RAM, ≤1 vCPU idle, spikes < 200 % CPU on burst.     |
| **Portability**     | Build on Linux x86-64 (`musl` optional for static Docker).  |

---

#### 4 . Architecture

```
┌──────────┐   ws   ┌──────────┐
│  Feeds   │◀──────│ DataMux   │─┐
│ (DEX,    │       └──────────┘ │
│  pump.fun)                    ▼
                            ┌────────────┐
                            │ Signal     │  (rules engine, state)
                            │  Engine    │
                            └────┬───────┘
             REST (keys)         │ orders
┌─────────┐        ▲         ┌───▼────────┐
│ Account │        │ fills   │ Executor   │─▶ CEX / RPC
│ Manager │────────┘         └────┬──────┘
└─────────┘                       │
       ▲                          ▼
       │                    ┌────────────┐
       │ metrics            │ Telemetry  │──▶ Prometheus/Grafana
       └────────────────────┴────────────┘
```

Each box is an **async task** under `tokio::select!`.

---

#### 5 . Key Crates

| Need               | Crate                                        |
| ------------------ | -------------------------------------------- |
| Async runtime      | `tokio`                                      |
| WebSocket          | `tokio-tungstenite`, `async-tungstenite`     |
| REST / H 2         | `reqwest`                                    |
| Solana RPC         | `solana-client`, `solana-transaction-status` |
| Exchange API       | `binance-rs` (or custom HMAC client)         |
| Config             | `serde`, `toml`, `config`                    |
| Persistence        | `rusqlite`, `sqlx` (SQLite)                  |
| Metrics            | `prometheus-client`, `axum` (for `/metrics`) |
| Logging            | `tracing`, `tracing-subscriber`              |
| Task orchestration | `futures`, `tokio-util`                      |

---

#### 6 . Configuration

`config.toml` (reloaded on `SIGHUP`):

```toml
[exchange]
binance_key  = "BINANCE_API_KEY"
binance_sec  = "BINANCE_SECRET"

[symbols]
spot = "SOLUSDT"
hedge = "SOLUSD_PERP"

[thresholds]
meme_drop_pct = 0.30
rsi_max       = 45
support_low   = 160
support_high  = 162

[risk]
max_trade_risk = 0.05
stop_loss      = 155
```

Secrets live in `.env`.  Anything in `.env` shadows TOML.

---

#### 7 . Build & Deploy

```bash
# local release
cargo build --release
./target/release/sol_volume_bot

# static Docker
docker build -f docker/Dockerfile -t sol-volume-bot:latest .
docker run --env-file .env -v $(pwd)/config:/config sol-volume-bot
```

---

#### 8 . Testing

1. **Unit**: pure functions (RSI, risk sizing) under `#[cfg(test)]`.
2. **Integration**: spin up `nats-server` or `solana-test-validator`, replay sample JSON, assert orders.
3. **Property**: use `proptest` to fuzz order-book deltas → no panic.

CI runs `cargo clippy -- -D warnings`, `cargo test --all`, and `cargo fmt --check`.

---

#### 9 . Stretch Goals

* **Cross-exchange hedging**: auto-switch hedge leg from Binance to Kraken on latency.
* **Web UI**: tiny Svelte dashboard off `/ws` feed for live PnL.
* **Machine-stopped**: Killswitch if Prometheus shows >0.2 % slippage 5 min rolling mean.

---

