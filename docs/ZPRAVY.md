# Obchody modelu a zpravy

_Sampion CH-009 (12 paru) + stop_4_atr + signal_i_rsi3, vsechny stupne, 12 paru, hodinova data 2012-2026 s naklady a swapem; 916 obchodu. Zdroje terminu: scripts/fundamenty.py (Fed, ECB, BoJ, BoE od 2012; u BoE chybi 8/2015-12/2016; US NFP a CPI z ALFRED). Bunka = obchodu | uspesnost | prumer % marze. Jen popis - do modelu se filtr dostane jen pres testovaci branu._

| skupina | 2012-18 | 2019-22 | 2023-26 |
|---|---|---|---|
| vsechny obchody | 344 | 89% | +9.1 % | 335 | 94% | +13.2 % | 237 | 85% | +6.3 % |
| centralni banka rozhodovala v tydnu vstupu | 83 | 88% | +9.3 % | 76 | 95% | +13.8 % | 55 | 96% | +13.9 % |
| ... nerozhodovala | 261 | 89% | +9.1 % | 259 | 93% | +13.0 % | 182 | 81% | +4.1 % |
| centralni banka rozhodne do 7 dni po vstupu | 83 | 87% | +6.5 % | 68 | 84% | +2.2 % | 66 | 77% | +4.1 % |
| ... nerozhodne do 7 dni | 261 | 90% | +10.0 % | 267 | 96% | +16.0 % | 171 | 88% | +7.2 % |
| centralni banka rozhodne do 14 dni po vstupu | 138 | 86% | +6.5 % | 123 | 89% | +8.8 % | 97 | 80% | +5.9 % |
| USD par, v tydnu vstupu vysly NFP nebo CPI | 104 | 88% | +7.4 % | 93 | 98% | +19.5 % | 91 | 80% | -0.4 % |
| USD par, bez NFP / CPI v tydnu | 118 | 91% | +11.1 % | 119 | 98% | +17.1 % | 72 | 92% | +15.4 % |
| zpravovy skok > 0.5 ATR za hodinu (posledni 2 dny) | 253 | 89% | +9.1 % | 228 | 93% | +12.9 % | 161 | 86% | +6.9 % |
| bez skoku (<= 0.5 ATR) | 91 | 89% | +9.1 % | 107 | 95% | +13.7 % | 76 | 82% | +5.2 % |
| zpravovy skok > 0.75 ATR | 99 | 86% | +8.3 % | 89 | 97% | +20.1 % | 62 | 81% | +1.9 % |
