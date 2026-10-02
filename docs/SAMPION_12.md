# Sampion samouceni - 12 paru (profil mesicne)

_CH-009 (12 paru) + stop_4_atr + signal_i_rsi3 + v3_zavrit_pred_cb_zisk. Velikosti vybrane jen na 2012-2022 (max. propad <= 20 %); roky 2023-2026 jsou test. Obchod po obchodu na hodinovych BID/ASK FXCM, naklady, swap, slozene uroceni._

## Pravidla

* rozhodnuti v patek pri dennim zaveru (23:00 Praha), 12 paru; TP 0.75 x ATR(14), SL 4.0 x ATR(14), nejdele 20 obchodnich dni; jedna pozice na par
* signal RSI2<5 nebo RSI3<15 (SELL zrcadlove), sazby se rozchazeji >= 0.25 p.b. + kladny carry -> marze **20% uctu**
* signal RSI2<5 (SELL zrcadlove), sazby se rozchazeji >= 0.25 p.b. -> marze **20% uctu**
* signal RSI2<5 (SELL zrcadlove), sazby se rozchazeji >= 0.1 p.b. -> marze **6% uctu**
* signal RSI2<5 (SELL zrcadlove), sazby se rozchazeji >= 0.0 p.b. -> marze **5% uctu**

## Vysledky

| obdobi | obchodu/rok | uspesnost | zisk/obchod (% marze) | ziskovych/mesic | mesicu s >= 2 ziskovymi | **rocne** | max. propad | max. vazana marze |
|---|---|---|---|---|---|---|---|---|
| 2012-2022 (vyber) | 41 | 90% | +8.7 % | 3.0 | 75% | **+51.8%** | 19.4% | 91% |
| **2023-2026 (test)** | 32 | 88% | +7.0 % | 2.3 | 65% | **+39.5%** | 27.6% | 92% |
| cele 2012-2026 | 38 | 90% | +8.3 % | 2.8 | 73% | **+48.6%** | 27.6% | 92% |

| rok | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| vynos | +32% | +9% | +51% | +117% | -0% | +12% | +89% | +101% | +23% | +158% | +82% | -18% | +45% | +35% |
| obchodu | 36 | 31 | 33 | 47 | 43 | 36 | 45 | 39 | 45 | 48 | 32 | 32 | 27 | 13 |
| propad | 7% | 14% | 18% | 12% | 10% | 10% | 13% | 12% | 13% | 19% | 15% | 28% | 13% | 13% |

Nejhorsi mesic -20.8%. Nahodne preskladane mesice (4 000 desetiletych drah): propad median 22%, v 5 % drah >= 36%, v 1 % >= 45%; rocne 5. / 50. / 95. percentil +30% / +48% / +69%.

## Odolnost (stejne velikosti)

| zmena | 2012-2022 rocne / propad | 2023-2026 rocne / propad |
|---|---|---|
| naklady 2x | +48.5% / 20% | +34.7% / 28% |
| rozhodnuti a vstup 1 h pred patecnim zaverem | +39.9% / 29% | +28.7% / 29% |
| vstup az po vikendu | +29.4% / 60% | +26.6% / 42% |
| sazby centralnich bank (o 2 mesice zpet) misto OECD | +31.2% / 54% | +54.8% / 25% |
| polovicni velikosti pozic | +23.9% / 10% | +19.0% / 14% |
