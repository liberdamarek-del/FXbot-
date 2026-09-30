# FXBOT Blok B3 – 12 párů, jen 1min ke stažení, ostatní dopočítané, historie

Vyžaduje nainstalovaný Blok A a Blok B. Blok B2 je v tomto balíku zahrnut (instaluje se sám,
ať ho už máte, nebo ne).

## Co se mění

| Soubor | Změna |
|---|---|
| src/data_update.py | výchozí seznam = 12 párů (7 hlavních + EUR/JPY, GBP/JPY, EUR/GBP, EUR/CHF, AUD/JPY), jen **1min**; větší dávka na jedno volání (4500 svíček, limit poskytovatele je 5000); **prodleva před uložením svíčky** (120 s); stahování starší historie (`--days`) |
| NOVÉ: src/resample.py | z minutových svíček se lokálně skládají **5min, 15min, 1h** (zdarma, bez volání API); neúplné okno se nikdy nepoužije |
| src/data_state.py | výchozí tolerance 240 s (prodleva 120 s + zpoždění poskytovatele 120 s) |
| scripts/update_data.py | přepínač `--days N`, odvozené časové rámce, přehledný výstup |
| src/update_service.py, scripts/run_updater.py | (z B2) průběžná aktualizace, max. 1 volání / 120 s; po nových minutových svíčkách dopočítá delší rámce |
| testy | test_b8 (skládání, včetně srovnání se skutečnými daty), test_b9 (prodleva, historie), upravené test_b3/b4/b6/b7 |

## Použití

    python scripts/update_data.py                 # dotáhne vše chybějící pro 12 párů + dopočítá 5min/15min/1h
    python scripts/update_data.py --days 30       # navíc zajistí 30 dní historie u každého páru
    python scripts/update_data.py --status        # jen stav, bez volání API
    python scripts/run_updater.py                 # průběžně, max. 1 volání za 120 s

Vrácení zpět: `python …/apply_block_b3.py --rollback backup_block_b3_<časová_značka>`
