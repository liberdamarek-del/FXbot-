# FXBOT oprava B3.1 – testy už nečtou váš soubor .env

Vyžaduje Blok B3.

Problém: test `test_b6` očekával varování o sdíleném klíči `demo`, ale po uložení vašeho
osobního klíče do `.env` se varování (správně) nezobrazí a test selhal. Program samotný
byl v pořádku.

| Soubor | Změna |
|---|---|
| src/config.py | volitelně ignoruje `.env` (jen když je nastaveno `FXBOT_IGNORE_DOTENV`) |
| scripts/run_tests.py | testy běží v čistém prostředí: bez osobního klíče a bez vašich nastavení |
| test_b6_scripts.py | nezávisí na `.env` |

Běžné spuštění programů se nemění – `.env` se čte jako dosud.

Vrácení zpět: `python …/apply_block_b3_1.py --rollback backup_block_b3_1_<časová_značka>`
