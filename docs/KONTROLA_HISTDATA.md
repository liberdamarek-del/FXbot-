# Kontrola na 16 párech HistData (povinná, jen report)

_Vytvořeno 2026-10-20 (`scripts/kontrola_histdata.py`). Šampion se stejnými maržemi jako dnes, žádné nové ladění ani výběr; není to kritérium brány. Data HistData jsou jen BID (ASK = BID, spread páru se přičítá na obou stranách), páka 1:20 pro nehlavní páry, data od 2026-10-01 jsou v trezoru. Pro srovnání jsou na stejných maržích i 12 živých párů._

## Profil max: CH-009 (12 paru) + velikost_podle_volatility + signal_i_rsi3 + zavrit_pred_cb_zisk

Marže šampiona (stupně): [0.15, 0.15, 0.06, 0.06]

| období | skupina | obchodů / rok | úspěšnost | průměr (% marže) | ročně | propad | ziskových / měsíc |
|---|---|---|---|---|---|---|---|
| 2012-2018 | 16 HistData | 37 | 78% | -2.3 | -4.9% | 50% | 2.4 |
| 2012-2018 | 12 živých | 38 | 85% | +5.1 | +23.5% | 18% | 2.7 |
| 2019-2022 | 16 HistData | 43 | 77% | +0.5 | -8.1% | 72% | 2.7 |
| 2019-2022 | 12 živých | 42 | 89% | +6.7 | +51.1% | 19% | 3.1 |
| 2023-2026-09 | 16 HistData | 34 | 79% | -0.4 | -7.9% | 59% | 2.2 |
| 2023-2026-09 | 12 živých | 29 | 85% | +4.1 | +19.7% | 28% | 2.0 |

Po párech (celé období, jen obchody šampiona):

| pár | obchodů | úspěšnost | průměr (% marže) | data do |
|---|---|---|---|---|
| USD/NOK | 97 | 79% | +2.8 | 2026-09-30 |
| EUR/NOK | 81 | 77% | +0.4 | 2026-09-30 |
| USD/SEK | 56 | 91% | +10.7 | 2026-09-30 |
| EUR/SEK | 39 | 92% | +6.0 | 2026-09-30 |
| USD/MXN | 105 | 72% | -3.1 | 2026-09-30 |
| USD/ZAR | 98 | 82% | +4.3 | 2026-09-30 |
| ZAR/JPY | 104 | 65% | -15.7 | 2026-09-30 |
| USD/PLN | 104 | 78% | -0.0 | 2026-09-30 |
| EUR/PLN | 33 | 76% | -2.7 | 2026-09-30 |
| USD/HUF | 42 | 74% | -3.5 | 2026-09-30 |
| EUR/HUF | 16 | 100% | +8.9 | 2018-12-14 |
| USD/CZK | 96 | 85% | +4.9 | 2026-09-30 |
| EUR/CZK | 11 | 64% | -9.9 | 2026-09-30 |
| CHF/JPY | 90 | 70% | -6.5 | 2026-09-30 |
| EUR/CAD | 85 | 81% | +1.1 | 2026-09-30 |
| GBP/AUD | 60 | 77% | -0.8 | 2026-09-30 |

## Profil mesicne: CH-009 (12 paru) + stop_4_atr + signal_i_rsi3 + v3_zavrit_pred_cb_zisk

Marže šampiona (stupně): [0.2, 0.2, 0.04, 0.04]

| období | skupina | obchodů / rok | úspěšnost | průměr (% marže) | ročně | propad | ziskových / měsíc |
|---|---|---|---|---|---|---|---|
| 2012-2018 | 16 HistData | 37 | 81% | +0.1 | -5.2% | 53% | 2.4 |
| 2012-2018 | 12 živých | 38 | 88% | +5.9 | +29.1% | 18% | 2.8 |
| 2019-2022 | 16 HistData | 42 | 78% | +0.3 | -11.5% | 84% | 2.7 |
| 2019-2022 | 12 živých | 43 | 90% | +6.2 | +53.3% | 19% | 3.1 |
| 2023-2026-09 | 16 HistData | 33 | 81% | +1.4 | -1.5% | 43% | 2.2 |
| 2023-2026-09 | 12 živých | 29 | 86% | +5.5 | +28.2% | 24% | 2.0 |

Po párech (celé období, jen obchody šampiona):

| pár | obchodů | úspěšnost | průměr (% marže) | data do |
|---|---|---|---|---|
| USD/NOK | 94 | 80% | +1.4 | 2026-09-30 |
| EUR/NOK | 81 | 81% | +2.8 | 2026-09-30 |
| USD/SEK | 56 | 91% | +10.5 | 2026-09-30 |
| EUR/SEK | 39 | 97% | +8.6 | 2026-09-30 |
| USD/MXN | 102 | 78% | +0.7 | 2026-09-30 |
| USD/ZAR | 97 | 84% | +4.4 | 2026-09-30 |
| ZAR/JPY | 96 | 66% | -11.3 | 2026-09-30 |
| USD/PLN | 100 | 78% | -0.4 | 2026-09-30 |
| EUR/PLN | 33 | 76% | -5.4 | 2026-09-30 |
| USD/HUF | 42 | 76% | -2.7 | 2026-09-30 |
| EUR/HUF | 16 | 100% | +8.9 | 2018-12-14 |
| USD/CZK | 96 | 85% | +4.6 | 2026-09-30 |
| EUR/CZK | 11 | 64% | -16.2 | 2026-09-30 |
| CHF/JPY | 87 | 72% | -3.6 | 2026-09-30 |
| EUR/CAD | 85 | 82% | +0.6 | 2026-09-30 |
| GBP/AUD | 58 | 76% | -0.6 | 2026-09-30 |

