# Rutiny (R-044, 11. 10. 2026)

_22. 10. 2026 (R-050): stejné úlohy běží i na GitHub Actions (`docs/GITHUB_PROVOZ.md`). Po týdnu souběhu se rutiny Claude
vypnou a GitHub přejde do ostrého režimu._

Každá rutina končí v **novém krátkém sezení** s připojeným repozitářem `liberdamarek-del/FXbot-` a modelem Sonnet.
Dřív se všechny spouštěly v jednom dlouhém rozhovoru. Ten měl přes 300 000 tokenů paměti, které se četly v každém
kroku, a to spotřebovávalo týdenní limit.

## Jak to funguje (dispečer)

1. Rutina v naplánovaný čas probudí malé sezení **„FXBOT dispečer rutin“** (session_01YNGCbnnfv62WR65DLXU9Ku, Sonnet).
2. Dispečer jen zavolá `create_session`: založí nové sezení s repozitářem a předá mu text úlohy (mezi
   `PROMPT_START` a `PROMPT_END` v rutině). Pak skončí. Za jedno probuzení přibude jen asi 3 000 tokenů.
3. Nové pracovní sezení udělá práci, uloží ji do gitu a pošle uživateli krátké shrnutí, také jako push notifikaci.

Proč přes dispečera:
* Rutina založená nástrojem nemá připojený repozitář, takže nemůže ukládat do gitu.
* Na telefonu se repozitář k rutině připojit nedá.
* Sezení založené přes `create_session` repozitář mít může.

Ověřeno 11. 10. 2026: denní aktualizace celá za 70 s, push v pořádku. Stála asi 0,05 USD za dispečera a 0,18 USD
za pracovní sezení, zhruba 7× méně než dřív.

## Rutiny

| Rutina | Kdy | Co dělá pracovní sezení |
|---|---|---|
| FXBOT denní aktualizace (23:07, přes dispečera) | po–pá 17:07 New York | `rutina.py denni`, deník, přehled, commit |
| FXBOT páteční signály (22:05, přes dispečera) | pá 16:05 New York | totéž a k tomu signály pro uživatele |
| FXBOT učení – středa (17:40, přes dispečera) | st 17:40 Praha | `rutina.py uceni`, průzkum, přehled; **od 20. 10. 2026 bez nových pokusů** (R-047, viz níže) |
| FXBOT učení – sobota (8:57, přes dispečera) | so 8:57 Praha | navíc heuristiky, týdenní výzkum a souhrn týdne |
| FXBOT výzkum agenta (07:23, přes dispečera; R-045) | út, čt, ne 07:23 Praha | webový průzkum zlepšení řídicí vrstvy, zápis do `research/agent/` (viz tamní README.md), 1 věta uživateli |

Staré rutiny, které chodily do hlavního rozhovoru, jsou vypnuté, ne smazané: „FXBOT aktualizace jednou denně
(23:07)“, „FXBOT páteční signály“, „FXBOT učení ve středu …“ a „FXBOT sobotní učení …“. V nouzi je jde znovu
zapnout.

## Kontrola a údržba

* Každý běh zapíše `learning/provoz/posledni_beh.json`: čas, typ rutiny a výsledek diagnostiky. Když tento soubor
  v gitu dlouho nepřibývá, rutina neběží.
* Dispečer roste asi o 25 000 tokenů týdně. Až přesáhne asi 300 000 (za několik měsíců), založí se nový dispečer
  se stejným `append_system_prompt` a rutiny se na něj přepojí. To se dělá vytvořením nových rutin, protože
  `persistent_session_id` nejde změnit.

## Zmrazení nových pokusů (R-047, od 20. 10. 2026)

Testovací roky 2019–26 jsou opotřebované, proto učení **nepřidává nové pokusy** do `scripts/self_learn.py`
(`EXPERIMENTS`). Učení dál stahuje data, obnovuje sazby, fundamenty, heuristiky a týdenní výzkum a přehodnotí
šampiona na nových datech (`python scripts/self_learn.py`, oba profily; nic nového nespustí). Kdyby rutina nový
pokus přesto přidala, `self_learn.py` skončí kódem 3 a diagnostika hlásí VAROVÁNÍ. Zrušit zmrazení smí jen
uživatel (`learning/zmrazeni_pokusu.json`, `docs/CHANGE_LOG.md` R-047). Platí pro rutiny, až se větev
`architektura-v2` sloučí do `main`.
