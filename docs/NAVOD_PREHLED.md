# Jak pracovat s FXBOT přehledem

**Odkaz:** https://claude.ai/artifact/9Z9eEZr8Ni6uVBa4zrmwuU (otevři v aplikaci Claude nebo na claude.ai,
přihlášený svým účtem; v mobilu i na počítači, nic se neinstaluje).

## Co na stránce je
1. **Signály k obchodu** – každý pátek ve 22:05 (náš čas) model spočítá, které páry obchodovat:
   směr (KOUPIT / PRODAT), vstup, take profit, stop loss, velikost (marže v % účtu), sílu signálu a důvod.
   Když zadáš velikost účtu v Kč, přepočte marži na Kč a přibližně na loty.
2. **Sledované páry** – všech 12 párů: kterým směrem dovolují obchod sazby, síla, RSI(2) a při jaké ceně by signál nastal.
3. **Fundamenty** – úrokové sazby 8 měn a jejich změna za 3 měsíce (z toho model bere směr), index strachu VIX.
4. **Můj deník** – tlačítko „Vstoupil jsem“ (zapíše obchod), u otevřeného obchodu „Vystoupil jsem“ (zadáš výstupní cenu).
5. **Výsledky** – tvoje uzavřené obchody (úspěšnost, průměr v % marže, Kč) a obchody modelu (dopředný test).

## Týdenní postup
1. Pátek po 22:05: otevři stránku, podívej se na Signály.
2. Do 23:00 zadej obchod u brokera přesně podle karty (vstup, SL, TP, velikost).
3. Zapiš ho tlačítkem „Zapsat podle signálu“ → „Vstoupil jsem“.
4. Obchod se uzavře sám na TP nebo SL; jinak ho zavři nejpozději v uvedený den.
5. Po uzavření „Vystoupil jsem“ + výstupní cena.

V sobotu ráno se model sám učí (zkouší nové nápady na historii) a výsledky zapisuje do `docs/UCENI_LOG.md`.
