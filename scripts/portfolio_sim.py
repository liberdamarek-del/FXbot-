"""Realistic account simulation of a portfolio of rules (walk-forward) - part of the live core.

`run_portfolio` takes trade lists (scripts/profit_deep.simulate) and plays them through one account:
- at most one open position per pair in the whole portfolio (a better ranked list has priority when two signal at
  the same moment),
- each trade ties up `share` x current equity as margin (compounding),
- the sum of margins of open trades <= MARGIN_CAP x equity (else skip),
- the result of a trade = margin x its % of the margin.
`Money` = bet-sizing systems (R-031), `mtm_drawdown` = drawdown with the open trades at their daily closes.

The research report on the wide portfolio of the lab systems (docs/PORTFOLIO_SIROKE.md) moved to
scripts/portfolio_report.py in R-048 (architektura-v2, phase 1), so that this module no longer imports the labs.
"""

import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

UTC = timezone.utc
MARGIN_CAP = 1.0


class Money:
    """Bet sizing of gambling systems on the account's own sequence of CLOSED trades (known at each entry); the
    multiplier scales the margin of the next trade (user's question 2026-10-05, docs/HAZARD.md):
        martingale:F:N   x F after each loss in a row (at most N steps), back to 1 after a win
        anti:F:N         x F after each win in a row (at most N steps), back to 1 after a loss
        dalembert:S:C    +S after a loss, -S after a win, starting at 1, kept between 1 and C
        fibonacci:N      one step up the Fibonacci sequence after a loss, two steps down after a win (<= step N)
    No system can change the expected result of the trades; they only reshape its distribution."""

    FIB = (1, 1, 2, 3, 5, 8, 13, 21, 34)

    def __init__(self, spec: str):
        kind, *args = spec.split(":")
        if kind not in ("martingale", "anti", "dalembert", "fibonacci"):
            raise ValueError(f"neznamy system sazeni {spec}")
        self.kind, self.args = kind, [float(a) for a in args]
        self.level = 1.0 if kind == "dalembert" else 0.0

    def update(self, margin_pct: float) -> None:
        win = margin_pct > 0
        if self.kind == "martingale":
            self.level = 0.0 if win else min(self.level + 1, self.args[1])
        elif self.kind == "anti":
            self.level = min(self.level + 1, self.args[1]) if win else 0.0
        elif self.kind == "dalembert":
            self.level = float(np.clip(self.level + (-self.args[0] if win else self.args[0]), 1.0, self.args[1]))
        else:
            self.level = max(self.level - 2, 0) if win else min(self.level + 1, self.args[0])

    def mult(self) -> float:
        if self.kind in ("martingale", "anti"):
            return self.args[0] ** self.level
        if self.kind == "dalembert":
            return self.level
        return float(self.FIB[int(self.level)])


def _legs(trade: dict) -> tuple[str, str]:
    """(currency bought, currency sold) of a trade."""
    base, quote = trade["pair"].split("/")
    return (base, quote) if trade["side"] > 0 else (quote, base)


def mtm_drawdown(taken: list[dict], margins: list[float]) -> float:
    """Largest drop of the account valued at every New York close with the
    open trades at their current price (realized results + open results);
    trades without daily marks (synthetic tests) count at their exit only."""
    if not taken:
        return 0.0
    times, deltas = [], []                                  # realized result at each exit
    for t, m in zip(taken, margins):
        times.append(t["t_out"])
        deltas.append(m * t["margin_pct"] / 100)
    mark_t, mark_v = [], []
    for t, m in zip(taken, margins):
        for when, v in t.get("marks", ()):
            mark_t.append(when)
            mark_v.append(m * v / 100)
    grid = np.unique(np.concatenate([np.array(times, dtype=np.int64), np.array(mark_t, dtype=np.int64)]))
    order = np.argsort(times)
    realized = np.concatenate([[0.0], np.cumsum(np.array(deltas)[order])])
    done = np.searchsorted(np.array(times)[order], grid, side="right")
    equity = 1.0 + realized[done]
    if mark_t:
        equity = equity + np.bincount(np.searchsorted(grid, mark_t), weights=mark_v, minlength=len(grid))
    peak = np.maximum.accumulate(np.maximum(equity, 1.0))
    return float(np.max(1 - equity / peak))


def run_portfolio(trade_lists: list[list[dict]], share, years=(2012, 2026), max_ccy: int | None = None,
                  brake=None, money: str | None = None, max_trades: int | None = None,
                  pause_sl_days: float | None = None) -> dict:
    """Chronological account with compounding, one position per pair. `share`
    = margin share of the equity per trade, one number or one per list. `brake`
    = (drawdown, factor): while the account (closed trades) is more than
    `drawdown` below its peak, new trades get `factor` x the margin. `money` = a bet-sizing system (Money).
    `max_trades` = at most this many open trades in the account (at the same moment the stronger list first).
    `pause_sl_days` = no new trade in a pair for this many days after the account's trade there hit its stop."""
    mm = Money(money) if money else None
    last_sl = {}                                      # pair -> exit time of the account's last stopped trade
    shares = list(share) if isinstance(share, (list, tuple)) else [share] * len(trade_lists)
    events = []
    for rank, trades in enumerate(trade_lists):
        if shares[rank] <= 0:
            continue                                  # a rule with no money does not block pairs
        for t in trades:
            if years[0] <= t["day"].year <= years[1]:
                events.append((t["t_in"], rank, t))
    events.sort(key=lambda e: (e[0], e[1]))
    equity, peak, max_dd = 1.0, 1.0, 0.0
    open_pos = []                                     # (t_out, pair, margin, trade)
    busy = set()
    taken, monthly, wins_m = [], defaultdict(float), defaultdict(int)
    max_used, max_open = 0.0, 0
    margins, entry_frac = [], []                      # margin and margin / equity of each taken trade
    start_equity_month = {}

    def close_until(moment):
        nonlocal equity, peak, max_dd
        open_pos.sort(key=lambda x: x[0])
        while open_pos and open_pos[0][0] <= moment:
            t_out, pair, margin, tr = open_pos.pop(0)
            pnl = margin * tr["margin_pct"] / 100
            if mm:
                mm.update(tr["margin_pct"])
            if tr.get("reason") == "SL":
                last_sl[pair] = t_out
            month = datetime.fromtimestamp(t_out, tz=UTC).strftime("%Y-%m")
            start_equity_month.setdefault(month, equity)
            equity += pnl
            monthly[month] += pnl
            wins_m[month] += tr["margin_pct"] > 0
            if not tr.get("stack"):
                busy.discard(pair)
            peak = max(peak, equity)
            max_dd = max(max_dd, 1 - equity / peak)

    taken_keys = set()
    for t_in, rank, tr in events:
        close_until(t_in)
        if tr.get("stack"):                           # a scale-in order: only together with its base trade
            if tr["base"] not in taken_keys:
                continue
        elif tr["pair"] in busy:
            continue
        if pause_sl_days and not tr.get("stack") and t_in < last_sl.get(tr["pair"], -10 ** 12) + pause_sl_days * 86400:
            continue
        if max_trades and not tr.get("stack") and sum(1 for x in open_pos if not x[3].get("stack")) >= max_trades:
            continue
        if max_ccy and not tr.get("stack"):                                   # at most max_ccy open trades long (short) one currency
            bought, sold = _legs(tr)
            legs = [_legs(x[3]) for x in open_pos]
            if sum(1 for b, _ in legs if b == bought) >= max_ccy or sum(1 for _, q in legs if q == sold) >= max_ccy:
                continue
        used = sum(m for _, _, m, _ in open_pos)
        margin = shares[rank] * equity * tr.get("size_mult", 1.0) * tr.get("size_factor", 1.0)
        if brake and equity < (1 - brake[0]) * peak:
            margin *= brake[1]
        if mm:
            margin *= mm.mult()
        if used + margin > MARGIN_CAP * equity:
            continue
        max_used = max(max_used, (used + margin) / equity)
        max_open = max(max_open, len(open_pos) + 1)
        open_pos.append((tr["t_out"], tr["pair"], margin, tr))
        if not tr.get("stack"):
            busy.add(tr["pair"])
        taken_keys.add((tr["pair"], tr["t_in"]))
        taken.append(tr)
        margins.append(margin)
        entry_frac.append(margin / equity)
    close_until(10 ** 12)
    dd_realized, max_dd = max_dd, mtm_drawdown(taken, margins)
    first = min(t["t_in"] for t in taken) if taken else 0
    last = max(t["t_out"] for t in taken) if taken else 1
    span_years = max((last - first) / 86400 / 365.25, 1e-9)
    months = []
    if taken:                                         # every calendar month of the span, also without trades
        y, m = datetime.fromtimestamp(first, tz=UTC).year, datetime.fromtimestamp(first, tz=UTC).month
        end = datetime.fromtimestamp(last, tz=UTC).strftime("%Y-%m")
        while f"{y}-{m:02d}" <= end:
            months.append(f"{y}-{m:02d}")
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return {"equity": equity, "cagr": equity ** (1 / span_years) - 1 if equity > 0 else -1.0, "max_dd": max_dd,
            "max_dd_realized": dd_realized,
            "trades": taken, "n_year": len(taken) / span_years,
            "win": np.mean([t["margin_pct"] > 0 for t in taken]) if taken else 0,
            "e": np.mean([t["margin_pct"] for t in taken]) if taken else 0,
            "wins_month": np.mean([wins_m[m] for m in months]) if months else 0,
            "months_2wins": np.mean([wins_m[m] >= 2 for m in months]) if months else 0,
            "months_pos": np.mean([monthly[m] > 0 for m in months]) if months else 0,
            "max_used": max_used, "max_open": max_open, "monthly": dict(monthly), "months": months,
            "entry_frac": entry_frac,
            "wins_by_month": dict(wins_m),
            "month_returns": [monthly[m] / start_equity_month[m] if m in start_equity_month else 0.0 for m in months]}

