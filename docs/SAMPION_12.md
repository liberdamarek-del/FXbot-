# Sampion samouceni - 12 paru (profil mesicne)

_CH-009 (12 paru) + stop_4_atr + signal_i_rsi3 + v3_zavrit_pred_cb_zisk. Velikosti vybrane jen na 2012-2022 (max. propad <= 20 %); roky 2023-2026 jsou test. Obchod po obchodu na hodinovych strednich cenach FXCM, spread + skluz, swap, slozene uroceni._

## Pravidla

* rozhodnuti a vstup v patek v 16:00 New York (22:00 Praha), hodinu pred dennim zaverem, 12 paru; TP 0.75 x ATR(14), SL 4.0 x ATR(14), nejdele 20 obchodnich dni; jedna pozice na par
* signal RSI2<5 nebo RSI3<15 (SELL zrcadlove), sazby se rozchazeji >= 0.25 p.b. + kladny carry -> marze **20% uctu**
* signal RSI2<5 (SELL zrcadlove), sazby se rozchazeji >= 0.25 p.b. -> marze **20% uctu**
* signal RSI2<5 (SELL zrcadlove), sazby se rozchazeji >= 0.1 p.b. -> marze **4% uctu**
* signal RSI2<5 (SELL zrcadlove), sazby se rozchazeji >= 0.0 p.b. -> marze **4% uctu**

## Vysledky

| obdobi | obchodu/rok | uspesnost | zisk/obchod (% marze) | ziskovych/mesic | mesicu s >= 2 ziskovymi | **rocne** | max. propad | max. vazana marze |
|---|---|---|---|---|---|---|---|---|
| 2012-2022 (vyber) | 40 | 89% | +6.0 % | 2.9 | 72% | **+37.8%** | 19.2% | 88% |
| **2023-2026 (test)** | 29 | 86% | +5.5 % | 2.0 | 55% | **+28.2%** | 24.1% | 88% |
| cele 2012-2026 | 37 | 88% | +5.9 % | 2.7 | 68% | **+35.1%** | 24.1% | 88% |

| rok | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| vynos | +22% | +12% | +41% | +88% | +6% | +15% | +42% | +36% | +12% | +153% | +62% | -15% | +37% | +31% |
| obchodu | 38 | 28 | 33 | 48 | 41 | 35 | 43 | 34 | 44 | 49 | 30 | 32 | 26 | 16 |
| propad | 15% | 8% | 17% | 13% | 6% | 9% | 12% | 17% | 8% | 19% | 11% | 24% | 17% | 9% |

Nejhorsi mesic -19.8%. Nahodne preskladane mesice (4 000 desetiletych drah): propad median 20%, v 5 % drah >= 31%, v 1 % >= 38%; rocne 5. / 50. / 95. percentil +21% / +35% / +52%.

## Odolnost (stejne velikosti)

| zmena | 2012-2022 rocne / propad | 2023-2026 rocne / propad |
|---|---|---|
| naklady 2x | +34.9% / 20% | +27.0% / 24% |
| rozhodnuti a vstup az pri patecnim zaveru (17:00 New York, jen srovnani) | +41.6% / 19% | +36.8% / 24% |
| rozhodnuti a vstup o hodinu driv (15:00 New York) | +42.1% / 19% | +28.7% / 24% |
| vstup az po vikendu | +35.4% / 20% | +21.5% / 39% |
| sazby centralnich bank (o 2 mesice zpet) misto OECD | +14.0% / 66% | +46.8% / 26% |
| polovicni velikosti pozic | +17.8% / 10% | +13.8% / 12% |
