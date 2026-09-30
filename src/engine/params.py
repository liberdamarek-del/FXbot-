"""Every numeric threshold of the model in one versioned place.

ALL values are PROVISIONAL (NEOVERENO) unless the walk-forward evidence
in the model registry says otherwise. Changing a value is a model change
(modules 80, 95, 126, 144): it produces a different parameter hash, which
is part of the run manifest and of every locked prediction, so results of
different parameter sets are never mixed.
"""

import hashlib
import json
from dataclasses import asdict, dataclass, replace


@dataclass(frozen=True)
class ModelParams:
    # ---------------------------------------------------------------- technical
    trend_slope_atr: float = 0.15        # EMA20 must move >= x ATR over 5 bars
    slope_bars: int = 5
    pivot_k_h1: int = 3
    pivot_k_h4: int = 2
    pivot_k_d1: int = 2
    pivot_prominence_atr: float = 0.8    # pivot must stand out by x ATR
    level_tolerance_atr: float = 0.25    # pivots within x ATR form one level
    level_lookback_h1: int = 400         # bars of pivots considered
    level_lookback_h4: int = 200
    max_level_distance_atr: float = 4.0  # ignore levels further than x ATR(H1)
    near_level_atr: float = 0.6          # "price is at the level" (NOW) if within x ATR
    entry_offset_atr: float = 0.3        # WAIT entry = level +/- x ATR
    stop_buffer_atr: float = 0.5         # SL beyond the level by x ATR
    target_buffer_atr: float = 0.1       # TP1 just before the opposing level
    max_tp1_atr: float = 3.0             # TP1 never further than x ATR(H1)
    no_chase_atr: float = 1.0            # move of x ATR in bias direction = no NOW (module 48)
    no_chase_bars: int = 4
    atr_timeframe: str = "1h"            # unit of the trade geometry: "1h" (champion) or "4h" (CH-001)
    entry_mode: str = "limit"            # WAIT entry: "limit" (champion) or "confirm" (CH-003, module 52)
    momentum_days: int = 20              # time-series momentum lookback (D1 bars)
    # ---------------------------------------------------------------- R:R / costs
    min_rr: float = 1.5                  # module 55 default gate
    slippage_pips: float = 0.2           # assumed per side (KNOWN-COST-ADJUSTED)
    broker_markup_pips: float = 0.5      # retail spread above the ECN source spread (NEOVERENO for XTB)
    max_spread_atr: float = 0.25         # spread above x ATR(H1) blocks NOW (module 51)
    # ---------------------------------------------------------------- fundamental
    repricing_days: int = 20             # rate repricing window (business days)
    repricing_min_bp: float = 10.0       # differential change that counts as evidence
    carry_min_pct: float = 1.0           # policy differential that counts as carry
    cot_z_extreme: float = 1.5           # positioning z-score marking crowding
    cot_lookback_weeks: int = 156
    risk_vix_jump: float = 3.0           # VIX points in 5 days = risk shock
    risk_beta_days: int = 120            # window for pair vs equity correlation
    risk_beta_min_corr: float = 0.25     # |corr| needed before risk is used as evidence
    # ---------------------------------------------------------------- decision
    require_fundamental_for_now: bool = True   # NOW needs >= 1 fundamental cluster in favour
    min_clusters_a: int = 3              # confidence A: technical + 2 fundamental clusters
    min_clusters_b: int = 2
    event_pre_hours: float = 6.0         # high-impact event ahead -> no NOW (module 47/48)
    event_post_minutes: float = 90.0
    horizon_hours: int = 24              # primary horizon of a prediction
    stability_atr: float = 0.15          # NOW must survive a price shift of +-x ATR(H1) and 2x spread (module 49)
    # ---------------------------------------------------------------- risk (module 57)
    risk_pct_standard: float = 0.5
    risk_pct_event: float = 0.25
    max_candidates: int = 3              # Top-3 (module 58, 141)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def fingerprint(self) -> str:
        text = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def with_changes(self, **changes) -> "ModelParams":
        return replace(self, **changes)


DEFAULT_PARAMS = ModelParams()
