# FXBOT Blok B3.3 – svíčky mimo obchodní dobu

Vyžaduje B3.2.

## Proč

Poskytovatel vrací i víkendové kotace (u 10 párů 1 406 minutových svíček od soboty 21:34
do neděle 20:59 UTC). Jsou skutečné (cena se hýbe), ale je to tenký trh mimo obchodní dobu
s obrovským rozpětím jedné minuty – zkreslily by ATR, trend i hladiny.

## Co se mění

| Soubor | Změna |
|---|---|
| src/data_update.py | svíčky mimo obchodní dobu se **neukládají**, jen se spočítají a ve výpisu ukážou |
| NOVÉ scripts/quarantine_offsession.py | už uložené takové svíčky **přesune** (nemaže) do tabulky `raw_bars_offsession`; nejdřív zkouška bez změny, pak `--apply` s ověřenou zálohou |
| scripts/run_tests.py, NOVÉ test_b11_offsession.py | testy včetně vynuceného selhání, které se musí vrátit zpět |

Odvozené časové rámce se nemění (odvozují se jen z minut v obchodní době).

Použití:

    python scripts/quarantine_offsession.py            # zkouška, nic nemění
    python scripts/quarantine_offsession.py --apply    # přesun (záloha DB se udělá sama)

Vrácení zpět: `python …/apply_block_b3_3.py --rollback backup_block_b3_3_<časová_značka>`
(přesunuté svíčky lze vrátit z tabulky `raw_bars_offsession` nebo ze zálohy databáze).
