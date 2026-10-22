"""Entry price, target and stop of one trade: the ONE formula of the backtest, the live plan and the forward test.

The backtest (scripts/profit_deep.simulate) measures from the price at which the trade is really entered, i.e. WITH
half the spread and the slippage (bought at the ask, sold at the bid): entry = mid +/- half. The target and the stop
are distances (ATR multiples) from that entry; an hour hits them when the price of the other side does (the bid of a
long: its high minus half). Until R-048 the live plan and the forward test measured them from the mid price, so a
published target was `half` closer and a published stop `half` farther than the tested ones. Now the backtest
(simulate) and the live plan (signals_live.make_plan / evaluate_pair) call these functions, and
test_h2_levels.py checks that the live plan and the forward test give the backtest's trades.
"""


def execution_price(mid: float, side: int, half: float) -> float:
    """Assumed fill price: the mid price of the decision bar plus (buy) or minus (sell) `half`."""
    return mid + side * half


def atr_distances(tp_atr: float, sl_atr: float, atr: float) -> tuple[float, float]:
    """Target and stop distance in price units for the rule's ATR multiples."""
    return tp_atr * atr, sl_atr * atr


def plan_levels(side: int, mid: float, atr: float, tp_atr: float, sl_atr: float, half: float, leverage: int) -> dict:
    """Everything the live plan shows for one trade, with the backtest's arithmetic: the assumed fill price, the
    price levels of the target and the stop, and their distances in % of the margin (price move x leverage)."""
    entry = execution_price(mid, side, half)
    tp_dist, sl_dist = atr_distances(tp_atr, sl_atr, atr)
    return {"entry": entry, "tp": entry + side * tp_dist, "sl": entry - side * sl_dist, "tp_dist": tp_dist,
            "sl_dist": sl_dist, "tp_margin": tp_dist / entry * 100 * leverage, "sl_margin": sl_dist / entry * 100 * leverage}
