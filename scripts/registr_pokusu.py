"""Registr pokusu (R-049, architektura-v2, faze 2): kazdy pokus o zlepseni modelu je zapsany DRIV, nez se spusti, a jeho
vysledek hned po behu. Pokus bez zaznamu se nepocita a nespusti se.

    python scripts/registr_pokusu.py import-logu     # zpetny import docs/UCENI_LOG.md (jednou)
    python scripts/registr_pokusu.py overeni         # retezec otisku je v poradku?
    python scripts/registr_pokusu.py souhrn          # kolik pokusu, kolik prijatych, prah DSR podle poctu pokusu
    python scripts/registr_pokusu.py zapis-analyzu <soubor> ["poznamka"]   # zapise otisk analyzy a stav registru
    python scripts/registr_pokusu.py registruj --nazev X --hypoteza "..." --duvod "..." [--parametry '{"...": 1}']

Soubor learning/registr_pokusu/registr.jsonl je append-only s retezcem otisku (src/core/ledger.py, stejne schema jako denik
predikci heuristik): radek nelze zmenit ani smazat, aniz by to overeni nenaslo. Zaznamy:
* typ "import"      - zpetny import z docs/UCENI_LOG.md (hypoteza, vysledek v obou testech, rozhodnuti; ekonomicky duvod
                      v logu zvlast nebyl, proto NEOVERENO),
* typ "registrace"  - pred behem: nazev, hypoteza, ekonomicky duvod, parametry, data a test (povinne vsechna pole),
* typ "vysledek"    - po behu: odkaz na registraci, rozhodnuti a cisla.
Pocet pokusu = importy + registrace (vysledek je jen dohledani). Z poctu pokusu vychazi prah DSR (src/core/statistika.py).
"""

from __future__ import annotations

import copy
import json
import re
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from src.core import ledger as LG  # noqa: E402

REG = PROJECT_ROOT / "learning" / "registr_pokusu" / "registr.jsonl"
LOG = PROJECT_ROOT / "docs" / "UCENI_LOG.md"
PERIOD_RE = re.compile(r"^(?P<per>\d{4}-\d{2}): (?P<rest>.*)$")
NOT_WRITTEN = "NEOVERENO (v logu uceni nebyl zapsan zvlast; viz hypoteza)"


# ---------------------------------------------------------------- zpetny import docs/UCENI_LOG.md
def _period(text: str) -> dict | None:
    """One test period of a log line: '2019-22: **+17.8%** rocne, propad 35% (marze 6% / ...), 3.0 ziskovych/mesic, po 2 letech
    +63% / +71%, vynos/propad 2.72' -> numbers; '2019-22: -' (nothing met the conditions) -> None."""
    m = PERIOD_RE.match(text.strip())
    rest = m.group("rest").strip() if m else ""
    c = re.match(r"\*\*(?P<cagr>[+-]?[\d.]+)%\*\* rocne, propad (?P<dd>[\d.]+)%", rest)
    if not c:
        return None
    out = {"rocne_proc": float(c.group("cagr")), "propad_proc": float(c.group("dd"))}
    w = re.search(r"([\d.]+) ziskovych/mesic", rest)
    if w:
        out["ziskovych_mesicne"] = float(w.group(1))
    sh = re.search(r"\(marze ([^)]*)\)", rest)
    if sh:
        out["marze_proc"] = [float(x) for x in re.findall(r"[\d.]+", sh.group(1))]
    b = re.search(r"po 2 letech ([^;]*?)(?:, vynos/propad|$)", rest)
    if b:
        out["bloky_2_roky_proc"] = [float(x) for x in re.findall(r"[+-]?\d+(?:\.\d+)?", b.group(1))]
    r = re.search(r"vynos/propad ([\d.]+)", rest)
    if r:
        out["vynos_na_propad"] = float(r.group(1))
    return out


def _result(line: str) -> dict:
    body = line.split(":", 1)[1].strip()
    out = {}
    for part in body.split(";"):
        m = PERIOD_RE.match(part.strip())
        if m:
            out[m.group("per")] = _period(part)
    return out


def parse_log(text: str | None = None) -> list[dict]:
    """All trials of docs/UCENI_LOG.md in the order of the file (### headings), with the context of the section above
    (profile and universe)."""
    lines = (text if text is not None else LOG.read_text(encoding="utf-8")).splitlines()
    profile, universe, out, cur = "max", "41 paru", [], None
    for n, line in enumerate(lines, 1):
        if line.startswith("## "):
            profile = "mesicne" if "profil mesicne" in line else "max"
            u = re.search(r"\((\d+) paru\)", line)
            universe = f"{u.group(1)} paru" if u else universe
            cur = None
        elif line.startswith("### "):
            m = re.match(r"### (\d{4}-\d{2}-\d{2}) - (?:\[(champion_12_mesicne|champion_12|champion_mesicne)\] )?(\S+): "
                         r"(PRIJATO|zamitnuto)\s*$", line)
            if not m:
                raise ValueError(f"neznamy format hlavicky pokusu, radek {n}: {line}")
            day, tag, name, decision = m.groups()
            prof, uni = {"champion_12": ("max", "12 paru"), "champion_12_mesicne": ("mesicne", "12 paru"),
                         "champion_mesicne": ("mesicne", "41 paru")}.get(tag, (profile, universe))
            cur = {"datum": day, "profil": prof, "universum": uni, "nazev": name, "rozhodnuti": decision,
                   "zdroj": f"docs/UCENI_LOG.md:{n}", "hypoteza": None, "kandidat": None, "sampion": None}
            out.append(cur)
        elif cur is not None and line.startswith("* "):
            if line.startswith("* kandidat:"):
                cur["kandidat"] = _result(line)
            elif line.startswith("* sampion:"):
                cur["sampion"] = _result(line)
            elif cur["hypoteza"] is None:
                cur["hypoteza"] = line[2:].strip()
    return out


def _diff(a, b, path="") -> dict:
    """Changed leaves between two configurations: {path: [old, new]} (JSON-able)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = {}
        for k in sorted(set(a) | set(b), key=str):
            out.update(_diff(a.get(k), b.get(k), f"{path}/{k}"))
        return out
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)) and len(a) == len(b):
        out = {}
        for i, (x, y) in enumerate(zip(a, b)):
            out.update(_diff(x, y, f"{path}[{i}]"))
        return out
    return {} if a == b else {path or "/": [_plain(a), _plain(b)]}


def _plain(x):
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x
    return repr(x)


def experiment_parameters() -> dict:
    """What each experiment of scripts/self_learn.EXPERIMENTS changes in the starting configuration (CH-009 on 12 pairs):
    the real parameters of the trial instead of a prose description; {} where the experiment cannot be applied to it."""
    import self_learn as SL
    out = {}
    for name, _text, make in SL.EXPERIMENTS:
        try:
            out[name] = _diff(SL.START, make(copy.deepcopy(SL.START)))
        except Exception as exc:                                   # an experiment needing a later champion's options
            out[name] = {"nelze_pouzit_na_START": f"{type(exc).__name__}: {exc}"}
    return out


def import_log() -> list[dict]:
    if REG.exists() and LG.read(REG):
        raise SystemExit("registr uz neco obsahuje - import se dela jen jednou do prazdneho registru")
    trials = parse_log()
    params = experiment_parameters()
    rows = []
    for k, t in enumerate(trials, 1):
        rows.append({
            "id": f"T-{k:04d}", "poradi": k, "typ": "import", "datum": t["datum"], "profil": t["profil"],
            "universum": t["universum"], "nazev": t["nazev"], "hypoteza": t["hypoteza"],
            "ekonomicky_duvod": NOT_WRITTEN, "parametry_zmena_oproti_START": params.get(t["nazev"], "NEOVERENO"),
            "data": {"vyber": "2012-2018 -> test 2019-2022; 2012-2022 -> test 2023-2026 (walk-forward)",
                     "brana": "v1 do 2026-10-02 (vecer), pak v3; zaznamy 2026-10-02 nelze presne zaradit"},
            "vysledek": {"kandidat": t["kandidat"], "sampion": t["sampion"]}, "rozhodnuti": t["rozhodnuti"],
            "zdroj": t["zdroj"], "poznamka": "zpetny import 2026-10-20 (R-049), zaznam nevznikl v dobe pokusu"})
    return LG.append(REG, rows)


# ---------------------------------------------------------------- pouziti za behu
def rows() -> list[dict]:
    return LG.read(REG)


def n_trials() -> int:
    """Number of counted trials: imports + registrations (a result record is not a new trial)."""
    return sum(1 for r in rows() if r["typ"] in ("import", "registrace"))


def is_registered(name: str) -> bool:
    """A trial may run only when it is registered (imports count: their results are in the log)."""
    return any(r["nazev"] == name and r["typ"] in ("import", "registrace") for r in rows())


def register(name: str, hypothesis: str, reason: str, parameters: dict, data: dict, plan: str = "") -> dict:
    """Pre-registration of a trial; all fields are mandatory (an empty reason is not a reason)."""
    for label, value in (("nazev", name), ("hypoteza", hypothesis), ("ekonomicky_duvod", reason)):
        if not str(value).strip() or str(value).strip().upper().startswith("NEOVERENO"):
            raise ValueError(f"registrace pokusu: pole {label} je povinne")
    if not parameters or not data:
        raise ValueError("registrace pokusu: parametry i data (vyber, test) jsou povinne")
    k = n_trials() + 1
    rec = {"id": f"T-{k:04d}", "poradi": k, "typ": "registrace", "datum": date.today().isoformat(), "nazev": name,
           "hypoteza": hypothesis, "ekonomicky_duvod": reason, "parametry": parameters, "data": data, "plan_vyhodnoceni": plan}
    return LG.append(REG, [rec])[0]


def record_result(name: str, profile: str, decision: str, result: dict) -> dict:
    reg = next((r for r in reversed(rows()) if r["nazev"] == name and r["typ"] in ("import", "registrace")), None)
    if reg is None:
        raise ValueError(f"pokus {name} neni v registru")
    rec = {"typ": "vysledek", "datum": date.today().isoformat(), "registrace": reg["id"], "nazev": name, "profil": profile,
           "rozhodnuti": decision, "vysledek": result}
    return LG.append(REG, [rec])[0]


def record_analysis(path: Path, note: str) -> dict:
    """Ties an analysis file (DSR / PBO of the registry's trials) to the registry state it was computed from."""
    import hashlib
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    rec = {"typ": "analyza", "datum": date.today().isoformat(), "soubor": str(path.relative_to(PROJECT_ROOT)),
           "sha256_souboru": digest, "pokusu_v_registru": n_trials(), "poznamka": note}
    return LG.append(REG, [rec])[0]


# ---------------------------------------------------------------- souhrn
def summary() -> dict:
    from src.core import statistika as ST
    rs = rows()
    trials = [r for r in rs if r["typ"] in ("import", "registrace")]
    accepted = [r for r in rs if r.get("rozhodnuti") == "PRIJATO"]
    n = len(trials)
    bars = {}
    for t in (48, 93):                                           # months of the 2019-22 test, of both tests together
        v = 1.0 / (t - 1)
        bars[f"T={t}"] = {str(k): round(ST.expected_max_sr(k, v), 4) for k in sorted({1, 10, 30, 100, n, 1000})}
    return {"pokusu": n, "prijato": len(accepted), "zamitnuto": n - len(accepted),
            "podle_dne": _by_day(trials), "prah_sr0_mesicni_pri_n_pokusech": bars, "retezec": LG.verify(REG)}


def _by_day(trials: list[dict]) -> dict:
    out = {}
    for t in trials:
        out[t["datum"]] = out.get(t["datum"], 0) + 1
    return out


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "souhrn"
    if cmd == "import-logu":
        out = import_log()
        print(f"importovano {len(out)} pokusu do {REG.relative_to(PROJECT_ROOT)}; posledni hash {out[-1]['hash'][:16]}")
    elif cmd == "overeni":
        res = LG.verify(REG)
        print(json.dumps(res, ensure_ascii=False))
        return 0 if res["ok"] else 1
    elif cmd == "souhrn":
        print(json.dumps(summary(), ensure_ascii=False, indent=1))
    elif cmd == "zapis-analyzu":
        rec = record_analysis(Path(argv[1]).resolve(), argv[2] if len(argv) > 2 else "")
        print(f"zapsano: analyza {rec['soubor']} sha256 {rec['sha256_souboru'][:16]} pri {rec['pokusu_v_registru']} pokusech")
    elif cmd == "registruj":
        def opt(name, default=None):
            return argv[argv.index(name) + 1] if name in argv else default
        rec = register(opt("--nazev", ""), opt("--hypoteza", ""), opt("--duvod", ""), json.loads(opt("--parametry", "{}")),
                       json.loads(opt("--data", "{}")), opt("--plan", ""))
        print(f"zaregistrovano {rec['id']} {rec['nazev']}")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
