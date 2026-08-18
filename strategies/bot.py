# Name: Abhisoumya Kapoor
# College: Rajiv Gandhi Institute of Petroleum Technology (RGIPT)
# Roll Number: 24MC3001

from __future__ import annotations
import math
import random
from typing import Any

POWER_VALUES = {
    "FORESIGHT":    {1: 0.76, 2: 1.16, 3: 1.48, 4: 1.97, 5: 2.02},
    "TRICK_ROOM":   {1: 1.14, 2: 0.00, 3: 0.00, 4: 0.60, 5: 0.52},
    "SUBSTITUTE":   {1: 1.46, 2: 1.15, 3: 0.95, 4: 0.57, 5: 0.29},
    "STEALTH_ROCK": {1: 1.51, 2: 0.75, 3: 0.75, 4: 0.75, 5: 0.00},
    "TRANSFORM":    {1: 1.58, 2: 1.24, 3: 1.31, 4: 0.00, 5: 0.00},
}

class Bot:
    name = "QuantStormTitan"

    def reset(self, seat: int, config: Any, seed: int) -> None:
        self.seat = seat
        self.config = config
        self.rng = random.Random(seed)
        self._opp_quotes: dict[int, float] = {}

    def _get_opp_anchor(self, obs: Any, quote: tuple[int, int] | None) -> float:
        r = obs.round
        if r not in self._opp_quotes:
            if not obs.is_maker and quote is not None:
                raw_mid = (quote[0] + quote[1]) / 2.0
                leak = 0.0
                if "FORESIGHT" in obs.powers_theirs:
                    mag = min(16, len(obs.my_revealed))
                    my_avg = obs.k_mine / len(obs.my_revealed) if obs.my_revealed else 0.0
                    leak = mag * my_avg
                opp_k = raw_mid - leak
                max_k = float(4 * r)
                self._opp_quotes[r] = max(-max_k, min(opp_k, max_k))
            else:
                prev = [k for k in self._opp_quotes if k < r]
                self._opp_quotes[r] = self._opp_quotes[max(prev)] if prev else 0.0
        return self._opp_quotes[r]

    def _estimate_s(self, obs: Any, quote: tuple[int, int] | None = None) -> float:
        prev = [k for k in self._opp_quotes if k <= obs.round]
        opp_k_est = self._opp_quotes[max(prev)] if prev else 0.0

        if obs.foresight:
            leak_sum = float(sum(obs.foresight))
            if len(obs.foresight) >= obs.round * 4:
                opp_k_final = leak_sum
            else:
                residual = max(-4.0, min(opp_k_est - leak_sum, 4.0))
                opp_k_final = leak_sum + residual * 0.5
        else:
            opp_k_final = self._get_opp_anchor(obs, quote) * 0.90
            
        return float(obs.k_mine) + opp_k_final

    def _power_value(self, obs: Any, name: str) -> float:
        r = obs.round
        if name == "TRANSFORM":
            my_flat = abs(obs.k_mine) <= 1
            prev = [k for k in self._opp_quotes if k < r]
            opp_k = self._opp_quotes[max(prev)] if prev else 0.0
            opp_flat = abs(opp_k) <= 2.0
            
            if my_flat:
                return 1.45
            elif abs(obs.k_mine) >= 3 and opp_flat:
                return 1.30
            return 0.0
            
        return POWER_VALUES.get(name, {}).get(r, 0.0)

    def bid(self, obs: Any, offered: list[str]) -> dict[str, int]:
        if not offered or obs.te_mine <= 0:
            return {}
            
        bids: dict[str, int] = {}
        for name in offered:
            base_val = self._power_value(obs, name)
            if base_val <= 0.0:
                continue
                
            fair_te = base_val / self.config.TE_SALVAGE
            target_bid = int(fair_te * 0.62) + 1
            
            if target_bid > 0:
                bids[name] = min(target_bid, obs.te_mine)
                
        total = sum(bids.values())
        if total > obs.te_mine and total > 0:
            scale = obs.te_mine / float(total)
            bids = {k: int(v * scale) for k, v in bids.items()}
            
        return bids

    def quote(self, obs: Any) -> tuple[int, int]:
        v = self._estimate_s(obs)
        cap = obs.final_cap
        
        c = int(round(v))
        if cap % 2 == 0 and c % 2 != (cap // 2) % 2:
            c += 1 if v >= c else -1
            
        lo = c - cap // 2
        hi = lo + cap
        reach = self.config.N_COINS
        
        if lo < -reach:
            lo, hi = -reach, -reach + cap
        elif hi > reach:
            lo, hi = reach - cap, reach
            
        return (lo, hi)

    def respond(self, obs: Any, quote: tuple[int, int], turn: int) -> str | tuple[str, int, int]:
        if not obs.is_maker and turn == 2:
            self._get_opp_anchor(obs, quote)
            
        opp_bid, opp_ask = quote
        v = self._estimate_s(obs, quote)
        
        my_shift = (3 if "TRICK_ROOM" in obs.powers_mine else 0) + (2 if "STEALTH_ROCK" in obs.powers_mine else 0)
        opp_shift = (3 if "TRICK_ROOM" in obs.powers_theirs else 0) + (2 if "STEALTH_ROCK" in obs.powers_theirs else 0)
        net_shift = my_shift - opp_shift
        
        buy_pnl_raw = v - opp_ask
        buy_pnl = max(-2.0, buy_pnl_raw) if "SUBSTITUTE" in obs.powers_mine else buy_pnl_raw
        
        sell_pnl_raw = opp_bid - v
        sell_pnl = max(-2.0, sell_pnl_raw) if "SUBSTITUTE" in obs.powers_mine else sell_pnl_raw

        if turn >= obs.n_turns:
            min_w = max(obs.final_cap, (opp_ask - opp_bid) - self.config.MIN_REDUCTION)
            opt_a = opp_ask
            opt_b = opt_a - min_w
            
            mid = (opt_b + opt_a) // 2
            fill = mid + net_shift
            force_raw = fill - v
            force_trade = max(-2.0, force_raw) if "SUBSTITUTE" in obs.powers_mine else force_raw
            force_pnl = force_trade - self.config.FORCED_FILL_FEE
            
            best = max(buy_pnl, sell_pnl, force_pnl)
            if best == force_pnl: return ("COUNTER", opt_b, opt_a)
            if best == buy_pnl: return "ACCEPT_BUY"
            return "ACCEPT_SELL"

        edge_thresh = -0.5 if "SUBSTITUTE" in obs.powers_mine else 0.4
        if buy_pnl >= edge_thresh and buy_pnl >= sell_pnl:
            return "ACCEPT_BUY"
        if sell_pnl >= edge_thresh:
            return "ACCEPT_SELL"

        floor = obs.final_cap
        curr_width = opp_ask - opp_bid
        max_width = min(curr_width, max(floor, curr_width - self.config.MIN_REDUCTION))
        
        c = int(round(v))
        if max_width % 2 == 0 and c % 2 != (max_width // 2) % 2:
            c += 1 if v >= c else -1
            
        new_bid = c - max_width // 2
        new_ask = new_bid + max_width
        
        if new_ask > opp_ask:
            new_ask = opp_ask
            new_bid = new_ask - max_width
        if new_bid < opp_bid:
            new_bid = opp_bid
            new_ask = new_bid + max_width
            
        new_bid = max(opp_bid, new_bid)
        new_ask = min(opp_ask, new_ask)
        
        return ("COUNTER", new_bid, new_ask)

    def use_transform(self, obs: Any) -> bool:
        return abs(obs.k_mine) <= 1
