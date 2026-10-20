# FXBOT

Model, který na **12 měnových párech** hledá obchody s historicky vysokou šancí na zisk a dává uživateli signály.
Obchoduje uživatel sám; projekt **nikdy neposílá příkazy brokerovi** (broker je jen ke čtení).

Čtěte v tomto pořadí: [`CLAUDE.md`](CLAUDE.md) (pravidla projektu) → [`docs/STAV_PROJEKTU.md`](docs/STAV_PROJEKTU.md)
(co funguje, co je rozpracované a neověřené) → [`docs/RUTINY.md`](docs/RUTINY.md) (co běží samo a kdy).

## Kde co je

| složka | obsah |
|---|---|
| `src/core/` | **živé jádro**: ceny, sazby, indikátory, signály, výpočet vstupu / cíle / stopu (jediný vzorec pro backtest, živý plán i forward test) |
| `scripts/` | živé skripty (`rutina.py`, `aktualizace.py`, `signals_live.py`, `diagnostika.py`, `self_learn.py`, `heuristiky.py`, ...) a výzkumné laby, na kterých stojí nástroje učení |
| `src/` (ostatní) | infrastruktura: zdroje dat, archiv cest, fundamenty, registr statistik, broker (zatím jen rozhraní) |
| `learning/` | sledovaný stav: šampioni, forward test, heuristiky (deník s řetězcem otisků), týdenní výzkum |
| `docs/` | dokumentace, deník učení, audity, výsledky výzkumů |
| `research/agent/` | průběžný výzkum zlepšení řídicí vrstvy (R-045) |
| `web/` | přehled (dashboard) |
| `archive/` | kód V7.8.0 a nevolané výzkumné laby (nic se nemazalo, viz `archive/README.md`) |
| `data/` | tržní data a mezivýsledky; **mimo git**, stahují je skripty |

## Testy

```sh
python fxbot.py test            # všechny testy v dočasné složce, nikdy nesahají na data/
python fxbot.py test h1 f3      # jen testy, v jejichž názvu je jeden z řetězců
```

Testy běží i na čistém klonu bez `data/` (ceny, sazby a VIX pro ně vyrábí `tests/jadro_scenar.py`).
