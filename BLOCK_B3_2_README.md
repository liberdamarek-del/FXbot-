# FXBOT oprava B3.2 – rychlé ukládání svíček a odolnější testy

Vyžaduje Blok B3. Obsahuje i opravu B3.1 (osobní klíč v `.env` už testy neruší),
takže B3.1 instalovat nemusíte; pokud už je nainstalovaný, nevadí.

## Proč

Na telefonu test `test_b7` překročil časový limit. Příčina: program ukládal svíčky
**po jedné** (každá s vlastním zápisem do databáze). Při stažení pár tisíc svíček najednou
to znamená desetitisíce zápisů, u vás by to zpomalilo i skutečné stahování.

## Co se mění

| Soubor | Změna |
|---|---|
| src/storage.py | nová funkce `save_raw_bars`: celá dávka v **jedné transakci** (u mě 54 s → 2 s, 57 857 zápisů → 473) |
| src/data_update.py, src/resample.py | ukládají po dávkách |
| src/config.py, scripts/run_tests.py, test_b6 | testy nečtou váš `.env` ani osobní klíč (oprava B3.1) |
| scripts/run_tests.py | vypisuje dobu každého testu; časový limit testu 900 s; při vypršení jen označí selhání |
| NOVÉ test_b10_batch_storage.py | hlídá, že dávka = jeden zápis, nic se nepřepisuje a při chybě se neuloží nic |
| src/resample.py, scripts/update_data.py | začátek uložené historie uprostřed okna se už nehlásí jako „díra“; po `--days` se dopočítají i starší okna |
| tests/seed.py, test_b7, test_b8 | lehčí příprava dat, nový test okrajového okna |

Vrácení zpět: `python …/apply_block_b3_2.py --rollback backup_block_b3_2_<časová_značka>`
