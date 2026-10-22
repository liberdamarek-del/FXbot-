# Trezor testovacích dat (R-049)

**Proč.** Roky 2019–26 už o modelu rozhodly (332 zapsaných pokusů, R-047), takže nejsou čistý test. Jediná opravdu nová data
jsou ta, která přibývají od 1. 10. 2026 (začátek forward testu). Aby se neopotřebovala dřív, než o nich model nemůže
rozhodnout, jsou zamčená.

**Co je zamčené.** Obchodní dny s datem od **2026-10-01** (stav v `learning/trezor.json`). Funkce `market.series()` je ve výchozím
stavu odřízne: učení, simulátor, vyzkum, heuristiky a týdenní výzkum vidí jen starší historii (u 12 párů zatím 12 obchodních
dnů zamčeno, data do 2026-10-16; `python scripts/trezor.py stav`).

**Čeho se to netýká.** Živé signály, forward test a živé predikce heuristik berou ceny z Yahoo a trezor je nečte; denní
aktualizace běží dál. Stahování dat a diagnostika kvality taky.

**Kdo se může podívat za zámek.** Jen `scripts/trezor.py` (`series(..., vault=False)`); test `test_i1_hygiena.py` hlídá, že
to nedělá nikdo jiný.

**Otevření.** Jednou a jen s vyslovným souhlasem uživatele:
`python scripts/trezor.py otevri --souhlas "<citace souhlasu>"`. Zapíše se čas, text souhlasu a počet pokusů v registru do
`learning/trezor.json` (`historie`); zpět zavřít nejde. Otevřít by se mělo až s předem zapsaným jediným testem (jedno pravidlo,
jedna sada parametrů) v registru pokusů.

**Slabá místa.** Zámek je softwarový: kdo upraví `learning/trezor.json` nebo zavolá `series(vault=False)`, ho obejde; chrání
před nechtěným použitím, ne před úmyslným. Hranice je po obchodních dnech (den 2026-10-01 začíná 30. 9. v 17:00 New York).
