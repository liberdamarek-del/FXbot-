"""Error taxonomy, root cause and counterfactual (module 69).

"SL hit" is a symptom, not a root cause. Each failed or non-productive
prediction gets one primary error family and a finer diagnostic case,
derived only from the recorded path (MFE/MAE, trigger, horizon) - the
history itself is never changed; the counterfactual only says what would
have had to be different.
"""

FAMILIES = (
    "direction", "entry", "trigger", "timing", "SL", "TP", "data", "execution",
    "dominant factor", "regime", "transition", "flow/positioning", "surprise", "noise", "management",
)


def classify(trade: dict) -> dict | None:
    state = trade.get("outcome_state")
    mfe = trade.get("mfe_r")
    mae = trade.get("mae_r")
    r = trade.get("r_net")

    if state == "TP1_BEFORE_SL":
        if mae is not None and mae >= 0.8:
            return {"family": "noise", "case": "correct direction, SL almost hit (fragile win)",
                    "root_cause": "vstup prilis blizko hluku", "counterfactual": "hlubsi vstup nebo sirsi SL"}
        return None

    if state == "SL_BEFORE_TP1":
        if mfe is not None and mfe >= 1.0:
            return {"family": "TP", "case": "correct direction / poor TP or management",
                    "root_cause": "cena sla >= 1R ve smeru, TP1 prilis daleko nebo chybi rizeni",
                    "counterfactual": "TP1 blize (struktura/ATR) nebo posun SL na vstup po 1R"}
        if mfe is not None and mfe >= 0.5:
            return {"family": "timing", "case": "correct thesis / wrong timing",
                    "root_cause": "cena se nejdriv pohnula ve smeru a pak otocila",
                    "counterfactual": "pozdejsi vstup po potvrzeni"}
        if trade.get("setup_type") == "BREAKOUT_RETEST":
            return {"family": "trigger", "case": "correct setup / bad trigger (failed retest)",
                    "root_cause": "retest prorazene urovne selhal",
                    "counterfactual": "vyzadovat uzavreni nad urovni pred vstupem"}
        return {"family": "direction", "case": "wrong trade",
                "root_cause": "trh sel proti tezi prakticky okamzite (MFE < 0.5R)",
                "counterfactual": "smer nemel byt potvrzen (zkontrolovat klastr dukazu)"}

    if state == "NOT_ACTIVATED":
        if "TP1" in (trade.get("notes") or ""):
            return {"family": "entry", "case": "correct direction / wrong entry (too deep)",
                    "root_cause": "cena dosahla cile bez navratu ke vstupu",
                    "counterfactual": "mensi entry offset nebo NOW pri silnem trendu"}
        return {"family": "entry", "case": "no entry within horizon",
                "root_cause": "uroven vstupu nebyla dosazena", "counterfactual": "bez zmeny (neni chyba smeru)"}

    if state == "EXPIRED":
        if r is not None and r > 0:
            return {"family": "TP", "case": "correct direction / TP too far for the horizon",
                    "root_cause": "zisk bez dosazeni TP1", "counterfactual": "TP1 blize nebo delsi horizont"}
        return {"family": "timing", "case": "thesis not confirmed within horizon",
                "root_cause": "trh se nepohnul ve smeru", "counterfactual": "kratsi horizont / prisnejsi filtr trendu"}

    if state == "SEQUENCE_UNKNOWN":
        return {"family": "data", "case": "sequence not provable at available granularity",
                "root_cause": "SL a TP1 ve stejne svicce", "counterfactual": "jemnejsi (1min) cesta v archivu"}

    if state == "UNRESOLVED":
        return {"family": "data", "case": "path gap", "root_cause": "chybejici svicky v ceste",
                "counterfactual": "doplnit data (backfill)"}

    return None


def taxonomy_table(trades: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}

    for trade in trades:
        error = classify(trade)

        if error:
            key = f"{error['family']}: {error['case']}"
            counts[key] = counts.get(key, 0) + 1

    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))
