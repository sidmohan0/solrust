# Solana Bot - Strategy Two-Pager: Memecoin Volume Correlation

**Market Scope**  
SOL/USDT and SOL/ETH pairs with 4-8 hour holding periods. Strategy capitalizes on the inverse correlation between Solana memecoin trading volume and SOL price movements. Target 2-6% returns per trade with 8-15 trades per week during high-activity periods.

**Edge Hypothesis**  
Memecoins represent 50%+ of Solana's total trading volume, with recent data showing 94.9% of all memecoin trading volume occurring on Solana. When memecoin volume drops significantly (>30% decline), capital rotates back into SOL, creating predictable pump patterns. Conversely, excessive memecoin activity often coincides with SOL price stagnation or decline.

**Signal Inputs**  
- **Primary**: Solana DEX volume changes (monitor $6B-$20B range)
- **Memecoin Metrics**: pump.fun daily volume (<$1.5M = rotation signal)
- **Technical Confirmation**: SOL RSI <45 with support at $160-162 range
- **Volume Analysis**: SOL trading volume increase >25% during memecoin lulls
- **Time-Based**: US trading hours (9 AM - 4 PM EST) show strongest correlations
- **Network Activity**: Transaction count drops as memecoin trading slows

**Execution Plan**  
1. **Monitor Phase**: Track memecoin volume via DeFiLlama and pump.fun analytics
2. **Entry Trigger**: When memecoin volume drops >30% AND SOL tests $160 support
3. **Position Entry**: Scale in over 2-4 hours with 3 equal tranches
4. **Target Zones**: 
   - TP1: $172 (historical resistance)
   - TP2: $181 (momentum breakout level)
5. **Quick Scalp**: Close 60% of position at +3-4% moves, hold remainder for extended targets

**Risk Limits**  
- Maximum 5% portfolio risk per trade sequence
- Stop loss at $155 (invalidates bullish structure)
- No trading during network outages or major announcements
- Limit exposure if memecoin volume remains elevated >48 hours
- Avoid overlapping with macro events (CPI, FOMC, major earnings)

**Success Metrics**  
- Target: 70% win rate with 1.5:1 minimum risk-reward
- Daily PnL target: 1-3% of portfolio
- Maximum consecutive losses: 4 before pause
- Track correlation coefficient between memecoin volume and SOL price (target >0.6)
- Monitor slippage on entries/exits (keep <0.2%)

**Data Needs & Gaps**  
- Real-time memecoin volume aggregator across all Solana DEXs
- Historical correlation data between $BONK, $WIF volumes and SOL price
- Institutional vs retail flow differentiation
- Cross-chain memecoin volume to isolate Solana-specific effects
- Automated alerts for pump.fun volume thresholds

**Open Questions**  
- Does correlation strength vary by memecoin market cap tiers?
- How do weekend vs weekday patterns affect the strategy?
- What's the optimal lookback period for volume correlation analysis?
- Should position sizing adapt based on overall crypto market volatility?
- How do new memecoin launches (vs existing) impact the correlation?