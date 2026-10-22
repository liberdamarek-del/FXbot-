# Provoz na GitHubu bez Claude (R-050, R-051, 22. 10. 2026)

_Rozhodnutí uživatele 22. 10. 2026: bot má běžet sám na serveru zdarma a přehled se má otevřít v obyčejném prohlížeči.
Deník obchodů je jen v prohlížeči. Týden běží GitHub souběžně s rutinami Claude, pak se rutiny Claude vypnou.
R-051 (téhož dne): v ostrém režimu obnova každou hodinu ve všední dny a oznámení na telefon přes ntfy._

## Co kde běží

| Část | Kde | Kdy |
|---|---|---|
| Denní běh (`rutina.py denni`: sazby, signály, dopředný test, heuristiky, diagnostika) | GitHub Actions, `.github/workflows/fxbot-denni.yml` | po–pá po zavření trhu (17:07 New York) |
| Páteční signály (totéž; rozhodnutí platí od 16:00 New York) | stejný workflow | pátek 16:05 New York |
| Hodinová obnova (totéž; R-051) | stejný workflow, jen v režimu **ostry** | po–pá každou hodinu v :12 UTC |
| Učení (historie FXCM, fundamenty, sazby, v sobotu heuristiky, přehodnocení šampiona, testy) | `.github/workflows/fxbot-uceni.yml` | středa a sobota |
| Testy při každé změně kódu | `.github/workflows/fxbot-testy.yml` | při push a pull requestu |
| Přehled | GitHub Pages, `index.html` + `stav.json` (`scripts/web_stranka.py`) | po každém běhu |
| Deník obchodů | prohlížeč uživatele (`localStorage`, klíč `fxbot.denik.v1`) | zálohu ukládá uživatel tlačítkem |
| Oznámení na telefon | ntfy.sh, jen když existuje secret `FXBOT_NTFY_TEMA` | denní a páteční běh vždy, učení s nízkou prioritou, hodinový běh jen při novince; selhání běhu |

Co na GitHubu **neběží**, protože potřebuje AI: výzkum agenta (`research/agent/`), krok průzkumu z `docs/VYZKUM_FRONTA.md`,
nové pokusy učení (ty jsou stejně zmrazené, R-047) a slovní týdenní souhrny. Týdenní výzkum trhu je pozastavený i u Claude
(trezor, R-049).

## Ověřené podmínky (dokumentace GitHubu, 22. 10. 2026)

* Actions jsou zdarma pro veřejné repozitáře na standardních serverech GitHubu (GitHub Actions billing).
* Pages jsou na tarifu GitHub Free jen pro veřejné repozitáře; web do 1 GB, měkký limit 100 GB přenosu za měsíc; nasazení
  musí skončit do 10 minut (GitHub Pages limits).
* Naplánované běhy se při vytížení GitHubu mohou zpozdit a fronta může běh zahodit; ve veřejném repozitáři se plánované
  běhy samy vypnou po 60 dnech bez aktivity v repozitáři (Events that trigger workflows / Disabling a workflow).
* Cron je v UTC (proto sloty pro letní i zimní čas).

## Jak se hlídá, že běh proběhl právě jednou

`scripts/github_beh.py plan` spočítá klíč běhu: `denni` = poslední už proběhlé zavření trhu (17:00 New York, po–pá),
`patek` = pátek od 16:00 New York, `uceni` = pražské datum, `hodina` = hodina UTC (jen v režimu ostry). Workflow si v cache GitHubu najde značku
`fxbot-beh-<druh>-<klíč>`; když existuje, běh vynechá, jinak poběží a po úspěchu značku uloží. Proto je v cronu víc slotů
(letní a zimní čas, záložní sloty) a zpožděný nebo vypadlý slot dožene další. Ruční spuštění (Actions → workflow → Run
workflow) běží vždy.

## Režim: stín / ostrý (`learning/provoz/github.json`)

* **stin** (od 22. 10. 2026): GitHub spočítá všechno a zveřejní přehled, ale **nic necommituje**. Deník predikcí heuristik
  (`learning/heuristiky/predikce|vyhodnoceni`) je řetězec otisků jen pro přidávání; dva zapisovatelé (rutina Claude a GitHub)
  by ho rozbili. Zápisy do `main` dělají dál rutiny Claude.
* **ostry**: GitHub je jediný zapisovatel; po běhu commituje `learning/` a `docs/` jako `github-actions[bot]`
  (`learning/provoz/github_beh.json` = kdy který běh proběhl). **Před přepnutím se musí vypnout rutiny Claude** (denní, páteční,
  učení středa a sobota, výzkum agenta), jinak hrozí dva zapisovatelé.

Přepnutí: změnit `"rezim"` na `"ostry"`, zapsat do `docs/CHANGE_LOG.md`, commit. Neznámá nebo chybějící hodnota = `stin`.

## Stránka

Adresa: **https://liberdamarek-del.github.io/FXbot-/** (zapnuto 22. 10. 2026: Settings → Pages → Source: GitHub Actions; přes API to
ze sezení Claude nejde). Zpráva o každém běhu je ve větvi `provoz-zprava` (logy jobů nejsou ze sezení Claude čitelné).

`scripts/web_stranka.py` vezme `data/live/stav.json`, **odstraní deník uživatele** (`denik_uzivatele`; stránka i repozitář jsou
veřejné), přidá ke každému páru nejbližší rozhodnutí centrálních bank (`rozhodnuti_cb`) a údaje o běhu (`provoz`: odkaz na běh,
termín další aktualizace = v režimu stin další zavření trhu + 6 h, v režimu ostry další hodinový slot + 3 h). Stránka (`web/prehled.html`, stejný soubor jako artefakt na claude.ai)
pozná, že neběží v Claude, načte `stav.json` sama a deník drží v prohlížeči:

* zápis, výstup a smazání obchodu jako dřív; upozornění na rozhodnutí centrální banky počítá stránka sama podle stejného
  pravidla jako `aktualizace.journal_summary` (ověřeno shodou textu na stejném vstupu);
* **Uložit zálohu** stáhne JSON, **Nahrát zálohu** ho sloučí (podle id; uzavřený obchod starší záloha znovu neotevře);
* jednorázový přenos odkazem `…/#denik=<base64url zálohy>` (fragment se na server neposílá; po načtení se z adresy smaže);
* když je po termínu další aktualizace, ukáže varování s odkazem na seznam běhů.

V Claude (artefakt) se stránka chová jako dřív: deník v databázi artefaktu, stav zapisuje rutina.

Kontrola: workflow stránku před nasazením otevře ve skutečném prohlížeči (Playwright; nejdřív Chrome předinstalovaný na serveru,
když nejde, nainstaluje Chromium) a `web_stranka.py kontrola-prohlizec` ověří, že se stav vykreslil, skript nehlásí chybu a zápis
do deníku přežije obnovení stránky. Když kontrola selže, nová verze se nenasadí a zůstane předchozí.

## Hodinová obnova (R-051, jen režim ostry)

Rozhodnutí uživatele 22. 10. 2026. Ve stínovém režimu se nespouští: GitHub by nic neukládal a hodinové predikce heuristik by se
ztrácely. V ostrém režimu cron `12 * * * 1-5` (UTC, pondělí 00:12 až pátek 23:12) spustí běh, když pro danou hodinu ještě
neproběhl; denní a páteční běh se tím jen pojistí dalšími sloty. Co to dá: čerstvé ceny a varování na stránce, rychlejší zjištění
zavření obchodu modelu, heuristiky ze všech 4H svíček (při jednom běhu denně jen ze svíčky končící v 17:00 New York; kód živé
vrstvy byl psaný na hodinový běh, `heuristiky.live`). **Signály hlavního modelu to nemění** (rozhodnutí jednou týdně, pátek 16:00
New York). Učení zůstává středa a sobota: pokusy jsou zmrazené, trezor mu pouští jen data do 30. 9. 2026 a historie FXCM přibývá
po týdnech; častější učení by nic nepřineslo a další pokusy by zhoršily korekci (R-049).

## Oznámení na telefon (ntfy)

Bez Claude nechodí push notifikace. Náhrada: aplikace **ntfy** (Google Play, F-Droid) a tajné téma:
1. v aplikaci ntfy přidat odběr tématu s dlouhým náhodným názvem;
2. na GitHubu: repozitář → Settings → Secrets and variables → Actions → New repository secret, název `FXBOT_NTFY_TEMA`,
   hodnota = stejný název tématu.
Kdo zná název tématu, zprávy vidí; proto náhodný název a uložení jako secret (v logu se nevypíše). Bez secretu se nic neposílá.

Co přijde (`scripts/github_beh.py souhrn` → `zprava/oznameni.json`, `oznam`): denní a páteční běh vždy (signály, změny obchodů
modelu, stav modelu, CHYBA diagnostiky; pátek a chyby vysokou prioritou), učení s nízkou prioritou, hodinový běh **jen** když model
obchod otevřel nebo zavřel (proti poslednímu commitu `learning/forward_trades.json`) nebo se objevila CHYBA, kterou minulý běh neměl.
Selhání denního, pátečního běhu nebo učení a selhání zveřejnění stránky přijde vždy; selhání hodinového běhu ne (zkusí to další
hodina a stránka ukáže stará data). Na vlastní obchody uživatele oznámení neupozorní: jeho deník je jen v prohlížeči.
Limit ntfy.sh: 250 zpráv denně na odesílatele (dokumentace ntfy) – tady jednotky denně.

## Rizika a slabá místa

| Riziko | Dopad | Co s tím |
|---|---|---|
| Zpoždění nebo vypadnutí plánovaného běhu | páteční signál přijde pozdě (vstup je do 23:00) | víc slotů; stránka ukazuje čas aktualizace a varování; ruční spuštění |
| Yahoo omezí časté stahování (hodinové běhy) | hodinové běhy selhávají | **NEOVĚŘENO**; denní a páteční běh má druhý pokus; stránka po 3 h bez obnovy varuje |
| 60 dní bez aktivity → GitHub plány vypne | běhy přestanou | v ostrém režimu commituje bot denně; **zda commity bota počítají jako aktivita, NEOVĚŘENO**; stránka po termínu varuje, zapnout jde v Actions jedním tlačítkem |
| Yahoo / FRED / ForexFactory ze serverů GitHubu | běh selže nebo bez dat | **OVĚŘENO 22. 10. 2026** (denní běh: diagnostika 36 OK, 0 CHYBA); FXCM a fundamenty ověří první učení; druhý pokus za minutu; komu GitHub pošle e-mail o selhání plánovaného běhu, NEOVĚŘENO |
| Deník jen v jednom prohlížeči | ztráta při smazání dat prohlížeče, jiný telefon ho nevidí | záloha souborem, žádost o trvalé úložiště (`navigator.storage.persist`) |
| Veřejná stránka | signály a model vidí kdokoli s odkazem (repozitář je veřejný už dnes) | `noindex`; deník se nezveřejňuje |
| Rozdíl proti rutině Claude | jiné výsledky | týden souběhu: stejné signály a obchody modelu v obou přehledech |
