# Algorithmic Market-Making Bot

## The Competition: Divided Oracle
The competition simulates a low-latency, incomplete-information market. Bots must price a hidden asset `S` (the sum of 40 fair coins) and bid on asymmetric powers using a limited Tactical Energy (TE) budget over 5 rounds of negotiation.

## Algorithmic Strategy & Edges
My bot (`strategies/bot.py`) acts as an optimal market maker and taker, maximizing expected value (EV) through three primary mathematical exploits:

1. **Bayesian Shrinkage on Opponent Signals:** Instead of taking opponent quotes at face value, the bot mathematically pulls the opponent's quote toward the prior (0) based on round-level uncertainty. It cleanly extracts exact values when the opponent's hand is leaked via the `FORESIGHT` power, filtering out negotiation noise by intercepting their strict Turn 1 quote.

2. **Fractional Asymmetric Bidding (The +1 Sniper):** Most baseline algorithms bid using standard truncated integers (e.g., `val * 0.60`). By evaluating the fair-value surface dynamically per round and mathematically bidding `+1` over the known truncated boundaries, the bot bypasses 50/50 coin flips to completely dominate the power auction economy for only a minimal 0.08 tick premium.

3. **Turn 6 Midpoint Trap & Parity Arbitrage:** The hidden asset `S` is strictly an even integer. The bot physically forces its straddle bounds to align with even lattice nodes, capturing maximum probability mass. On the final turn of negotiation, it calculates the exact Ternary Payoff (Buy vs. Sell vs. Forced Fill) and forces the spread against the highest possible edge, artificially inflating the forced execution price right before becoming the seller.

## File Structure
* `strategies/bot.py`: The core production-ready trading algorithm.

