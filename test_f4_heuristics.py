"""F4 - heuristic model (R-038, scripts/heuristiky.py); no network, synthetic prices, temporary ledger.

New York aligned 1D / 4H bars; no look-ahead in any template (the mask at a bar is the same when the later bars do not
exist yet, the currency strength and the fundamentals included); predictions of a rule never overlap; net return
after costs, MFE / MAE; statuses; false discovery rate; the append-only ledger with its hash chain (an edit, a
deletion or a second evaluation is detected); the live step end to end (a prediction at a freshly closed bar, no
back-dating after a missed update, the evaluation after the horizon).
"""

import json
import os
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_f4_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import numpy as np  # noqa: E402

import heuristiky as HX  # noqa: E402
from src.instruments import DEFAULT_ACTIVE  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="fxbot_f4_heur_"))
HX.DIR = TMP
HX.REGISTRY = TMP / "pravidla.json.gz"
HX.STATUS_LOG = TMP / "stavy_log.jsonl"
HX.LIVE_STATE = TMP / "zive.json"
HX.PRED_DIR = TMP / "predikce"
HX.EVAL_DIR = TMP / "vyhodnoceni"
HX.REPORT = TMP / "report.md"
NY = ZoneInfo("America/New_York")
UTC = timezone.utc
FUND = {"rates": None, "vix": ([], []), "events": {k: set() for k in ("FED", "ECB", "BOJ", "BOE", "US_NFP", "US_CPI")}}
HX.load_fund = lambda: FUND
HX.main_model_view = lambda state: {}
rng = np.random.default_rng(5)


def trading_days(first: date, n: int) -> list[date]:
    out, d = [], first
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def hourly_for(days: list[date], start_px: float, drift: list[float] | None = None) -> dict:
    ts = []
    for d in days:
        a = int((datetime(d.year, d.month, d.day, 17, tzinfo=NY) - timedelta(days=1)).timestamp())
        b = int(datetime(d.year, d.month, d.day, 17, tzinfo=NY).timestamp())
        ts += list(range(a, b, 3600))
    ts = np.array(ts, np.int64)
    steps = rng.normal(0, 0.0008, len(ts))
    if drift is not None:
        steps[-len(drift):] += drift
    c = start_px * np.exp(np.cumsum(steps))
    o = np.concatenate([[start_px], c[:-1]])
    wig = np.abs(rng.normal(0, 0.0003, len(ts))) * c
    return {"ts": ts, "o": o, "h": np.maximum(o, c) + wig, "l": np.minimum(o, c) - wig, "c": c}


def cut(hb: dict, t: int) -> dict:
    m = hb["ts"] < t
    return {k: v[m] for k, v in hb.items()}


# ---------------------------------------------------------------- New York aligned bars
days = trading_days(date(2024, 3, 4), 10)                          # includes the US DST change (10 March 2024)
hb = hourly_for(days, 1.1)
D = HX.bars_tf(hb, "1D")
assert D["day"] == days and all(datetime.fromtimestamp(int(e), tz=NY).hour == 17 for e in D["end_ts"])
F4 = HX.bars_tf(hb, "4H")
assert np.bincount(F4["bucket"]).tolist() == [10] * 6                                # 6 bars a day
assert all(datetime.fromtimestamp(int(e), tz=NY).hour in (21, 1, 5, 9, 13, 17) for e in F4["end_ts"])
k = 3
assert abs(D["h"][k] - hb["h"][(hb["ts"] >= D["ts"][k]) & (hb["ts"] <= D["last_ts"][k])].max()) < 1e-12
mid = int(D["end_ts"][4]) - 1800                                                      # live: only finished bars
assert HX.bars_tf(cut(hb, mid), "1D", mid)["day"][-1] == days[3]

# ---------------------------------------------------------------- no look-ahead in any template
pairs = list(DEFAULT_ACTIVE)
long_days = trading_days(date(2023, 1, 2), 330)
H12 = {p: hourly_for(long_days, 150.0 if "JPY" in p else 1.0) for p in pairs}
full = HX.build_contexts(H12, "1D", FUND)
k_cut = full["EUR/USD"].n - 25
t_cut = int(full["EUR/USD"].bars["end_ts"][k_cut])
part = HX.build_contexts({p: cut(h, t_cut) for p, h in H12.items()}, "1D", FUND)
checked = 0
for p in ("EUR/USD", "AUD/JPY", "USD/CAD"):
    mf = {t: m for _, _, _, t, m in HX.rule_masks(full[p])}
    for _, _, _, t, m in HX.rule_masks(part[p]):
        kk = part[p].n - 1
        assert part[p].bars["end_ts"][kk] == full[p].bars["end_ts"][kk]
        assert m[kk] == mf[t][kk], f"{p} {t}: the mask at a bar depends on later bars"
        checked += 1
assert checked > 600
assert not np.isnan(full["EUR/USD"].aux["rank5"][0][-1])                              # all 8 currencies ranked

# ---------------------------------------------------------------- predictions never overlap; outcomes
mask = np.zeros(40, bool)
mask[[3, 4, 5, 9, 10, 20, 24, 25]] = True
assert HX.take(mask, np.ones(40, bool), 5).tolist() == [3, 9, 20, 25]
x = full["EUR/USD"]
o = HX.outcomes(x)
i = int(np.flatnonzero(o["valid"])[0])
assert abs(o["gross"][i] - (x.c[i + 5] / x.c[i] - 1) * 100) < 1e-12
assert abs(o["up_mfe"][i] - (x.h[i + 1:i + 6].max() / x.c[i] - 1) * 100) < 1e-12
a = HX.pred_arrays(o, np.array([i]), -1)
assert abs(a["net"][0] - (-o["gross"][i] - o["cost"][i])) < 1e-12                  # short: sign and costs
assert abs(a["mfe"][0] - o["up_mae"][i]) < 1e-12 and abs(a["mae"][0] - o["up_mfe"][i]) < 1e-12
assert o["cost"][i] > 0 and not o["valid"][-5:].any()                                 # no outcome without the horizon

# ---------------------------------------------------------------- statuses, false discovery rate, estimates
base = {"par": "EUR/USD", "sousede": {"celkem": 2, "drzi": 2, "podil": 1.0}, "wf": {"let": 5, "kladnych": 4, "podil": 0.8},
        "bloky": [0.1, 0.1, 0.1, 0.1], "pary": {"celkem": 12, "kladnych": 9, "podil": 0.75}}
good_is = {"n": 300, "ev": 0.1, "prevyseni": 0.1, "p": 0.01, "win": 0.55}
good_oos = {"n": 300, "ev": 0.1, "prevyseni": 0.1, "p": 0.001, "q": 0.05, "p_perm": 0.002, "ci": [0.02, 0.2], "win": 0.55}
assert HX.classify({**base, "is": good_is, "oos": good_oos})[0] == "AKTIVNÍ"
assert HX.classify({**base, "is": good_is, "oos": {**good_oos, "q": 0.3}})[0] == "SLABÁ"
assert HX.classify({**base, "is": good_is, "oos": {**good_oos, "n": 12}})[0] == "NEOVĚŘENÁ"
assert HX.classify({**base, "is": good_is, "oos": {**good_oos, "ev": -0.01}})[0] == "NEFUNKČNÍ"
assert HX.classify({**base, "is": {**good_is, "ev": -0.02}, "oos": good_oos})[0] == "OVERFIT/NESTABILNÍ"
assert HX.classify({**base, "sousede": {"celkem": 4, "drzi": 1, "podil": 0.25}, "is": good_is, "oos": good_oos})[0] == "OVERFIT/NESTABILNÍ"
assert HX.classify({**base, "par": "VŠE", "pary": {"celkem": 12, "kladnych": 4, "podil": 0.33}, "is": good_is,
                    "oos": good_oos})[0] == "OVERFIT/NESTABILNÍ"
q = HX.bh_qvalues([0.001, 0.01, 0.02, 0.5])
assert abs(q[0] - 0.004) < 1e-12 and abs(q[1] - 0.02) < 1e-12 and abs(q[2] - 0.02 * 4 / 3) < 1e-12 and q[3] == 0.5
assert HX.heur_estimate(2, 1) == 60 and HX.heur_estimate(2, -1) == 40 and HX.heur_estimate(20, 1) == 80
assert abs(HX.binom_cdf(5, 10, 0.5) - 0.623046875) < 1e-12
assert HX.neighbours(HX._family("osc_rsi_obrat"), "1D", (2, 10)) == [(2, 5), (2, 15)]
assert HX.neighbours(HX._family("tr_ema_x"), "1D", (20, 50)) == [(10, 30), (50, 200)]

# ---------------------------------------------------------------- ledger: append-only hash chain
HX._append(HX.PRED_DIR, [{"id": "a", "pravidlo": "r"}, {"id": "b", "pravidlo": "r"}], "2026-10-07")
HX._append(HX.EVAL_DIR, [{"id": "a", "vysledek": "ÚSPĚCH", "vynos_proc": 0.1}], "2026-10-07")
assert HX.verify_ledger()["problemy"] == []
f = HX.PRED_DIR / "2026-10-07.jsonl"
orig = f.read_text(encoding="utf-8")
f.write_text(orig.replace('"pravidlo": "r"', '"pravidlo": "x"', 1), encoding="utf-8")      # an edited prediction
assert HX.verify_ledger()["problemy"]
f.write_text(orig.split("\n", 1)[1], encoding="utf-8")                                     # a deleted prediction
assert HX.verify_ledger()["problemy"]
f.write_text(orig, encoding="utf-8")
HX._append(HX.EVAL_DIR, [{"id": "a", "vysledek": "NEÚSPĚCH", "vynos_proc": -0.1}], "2026-10-07")  # second evaluation
assert any("dvakrát" in p for p in HX.verify_ledger()["problemy"])
for d in (HX.PRED_DIR, HX.EVAL_DIR):
    for x_ in d.glob("*.jsonl"):
        x_.unlink()

# ---------------------------------------------------------------- live step end to end
days2 = trading_days(date(2024, 1, 2), 300)
drop = [-0.0012] * 48                                                                   # two falling days: RSI(2) < 10
H12 = {p: hourly_for(days2, 150.0 if "JPY" in p else 1.0, drop if p == "EUR/USD" else None) for p in pairs}
ext_days = trading_days(days2[-1] + timedelta(days=1), 8)
EXT = {p: hourly_for(ext_days, float(h["c"][-1])) for p, h in H12.items()}
ALL = {p: {k: np.concatenate([H12[p][k], EXT[p][k]]) for k in "ts o h l c".split()} for p in pairs}
rid = "osc_rsi_obrat-2-10-L|EURUSD|1D"
fam = HX._family("osc_rsi_obrat")
rule = {"id": rid, "sablona": "osc_rsi_obrat-2-10-L", "rodina": "osc_rsi_obrat", "typ": "oscilatory", "par": "EUR/USD",
        "tf": "1D", "smer": "LONG", "horizont": "5 dní", **HX.describe(fam, (2, 10), 1), "parametry": [2, 10],
        "is": {"n": 200, "win": 0.56}, "oos": {"n": 150, "win": 0.54, "win_ci": [0.47, 0.6], "ev": 0.05},
        "ocekavany_vynos": 0.04, "stav": "AKTIVNÍ", "duvod": "test", "duveryhodnost": "STŘEDNÍ"}
import gzip  # noqa: E402
with gzip.open(HX.REGISTRY, "wt", encoding="utf-8") as fh:
    json.dump({"vytvoreno": "2026-10-07T00:00", "data_do": "2024-12-31", "metodika": {}, "kalibrace": {},
               "hlavni_model": {}, "pravidla": [rule]}, fh)
close_ts = int(datetime(days2[-1].year, days2[-1].month, days2[-1].day, 17, tzinfo=NY).timestamp())
now = close_ts + 600                                                                    # 10 minutes after the close
out = HX.live(None, now=now, hourly={p: cut(h, now) for p, h in ALL.items()})
preds = HX._read_chain(HX.PRED_DIR)
assert out["nove"] == 1 and len(preds) == 1 and preds[0]["pravidlo"] == rid and preds[0]["smer"] == "LONG"
p0 = preds[0]
assert p0["cas_svicky"] == close_ts and p0["cil"] > p0["cena"] > p0["prah"] and 30 <= p0["heur_odhad"] <= 80
assert p0["stat_pravdepodobnost"] == 0.54 and p0["stav_pravidla"] == "AKTIVNÍ"
HX.live(None, now=now + 1800, hourly={p: cut(h, now + 1800) for p, h in ALL.items()})   # the same bar again: nothing new
assert len(HX._read_chain(HX.PRED_DIR)) == 1
late = int(datetime(ext_days[0].year, ext_days[0].month, ext_days[0].day, 17, tzinfo=NY).timestamp()) + 9 * 3600
HX.live(None, now=late, hourly={p: cut(h, late) for p, h in ALL.items()})               # missed the next close by 9 h
assert json.loads(HX.LIVE_STATE.read_text())["zmeskano"] >= 1
end5 = int(datetime(ext_days[4].year, ext_days[4].month, ext_days[4].day, 17, tzinfo=NY).timestamp())
out = HX.live(None, now=end5 + 600, hourly={p: cut(h, end5 + 600) for p, h in ALL.items()})
ev = [e for e in HX._read_chain(HX.EVAL_DIR) if e["id"] == p0["id"]]
assert len(ev) == 1 and ev[0]["konec"] == end5
px_end = float(ALL["EUR/USD"]["c"][ALL["EUR/USD"]["ts"] == end5 - 3600][0])
cost = float(HX.cost_pct("EUR/USD", np.array([p0["cena"]]))[0])
assert abs(ev[0]["vynos_proc"] - round((px_end / p0["cena"] - 1) * 100 - cost, 4)) < 1e-9
assert ev[0]["vysledek"] == ("ÚSPĚCH" if ev[0]["vynos_proc"] > 0 else "NEÚSPĚCH") and ev[0]["duvod"]
assert out["sebehodnoceni"]["okna"]["vse"]["n"] == 1 and HX.verify_ledger()["problemy"] == []
HX.live(None, now=end5 + 3000, hourly={p: cut(h, end5 + 3000) for p, h in ALL.items()})
assert len([e for e in HX._read_chain(HX.EVAL_DIR) if e["id"] == p0["id"]]) == 1      # evaluated once

print("=" * 60)
print("F4 HEURISTIC MODEL")
print("=" * 60)
print("NEW YORK ALIGNED 1D / 4H BARS (DST), LIVE BARS ONLY WHEN FINISHED: PASS")
print(f"NO LOOK-AHEAD IN ANY TEMPLATE ({checked} MASKS, STRENGTH AND FUNDAMENTALS INCLUDED): PASS")
print("NON-OVERLAPPING PREDICTIONS, NET RETURN AFTER COSTS, MFE / MAE: PASS")
print("STATUSES, FALSE DISCOVERY RATE, HEURISTIC ESTIMATE, NEIGHBOURS: PASS")
print("LEDGER HASH CHAIN: EDIT, DELETION AND SECOND EVALUATION DETECTED: PASS")
print("LIVE: PREDICTION AT A FRESH CLOSE, NO BACK-DATING, ONE EVALUATION AFTER THE HORIZON: PASS")
print("RESULT: PASS")
print("=" * 60)
