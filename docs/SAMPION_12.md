# Sampion samouceni - 12 paru (profil mesicne)

_CH-009 (12 paru) + stop_4_atr + signal_i_rsi3. Velikosti vybrane jen na 2012-2022 (max. propad <= 20 %); roky 2023-2026 jsou test. Obchod po obchodu na hodinovych BID/ASK FXCM, naklady, swap, slozene uroceni._

## Pravidla

* rozhodnuti v patek pri dennim zaveru (23:00 Praha), 12 paru; TP 0.75 x ATR(14), SL 4.0 x ATR(14), nejdele 20 obchodnich dni; jedna pozice na par
* signal RSI2<5 nebo RSI3<15 (SELL zrcadlove), sazby se rozchazeji >= 0.25 p.b. + kladny carry -> marze **12% uctu**
* signal RSI2<5 (SELL zrcadlove), sazby se rozchazeji >= 0.25 p.b. -> marze **12% uctu**
* signal RSI2<5 (SELL zrcadlove), sazby se rozchazeji >= 0.1 p.b. -> marze **6% uctu**
* signal RSI2<5 (SELL zrcadlove), sazby se rozchazeji >= 0.0 p.b. -> marze **5% uctu**

## Vysledky

| obdobi | obchodu/rok | uspesnost | zisk/obchod (% marze) | ziskovych/mesic | mesicu s >= 2 ziskovymi | **rocne** | max. propad | max. vazana marze |
|---|---|---|---|---|---|---|---|---|
| 2012-2022 (vyber) | 40 | 89% | +8.4 % | 3.0 | 74% | **+31.5%** | 19.0% | 59% |
| **2023-2026 (test)** | 32 | 86% | +6.8 % | 2.2 | 65% | **+20.9%** | 19.1% | 60% |
| cele 2012-2026 | 38 | 88% | +8.1 % | 2.8 | 72% | **+28.7%** | 19.1% | 60% |

| rok | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| vynos | +24% | +8% | +37% | +67% | -3% | +10% | +62% | +58% | +22% | +48% | +40% | -12% | +23% | +21% |
| obchodu | 35 | 31 | 33 | 47 | 43 | 36 | 45 | 39 | 44 | 48 | 31 | 32 | 27 | 13 |
| propad | 12% | 14% | 13% | 10% | 10% | 10% | 8% | 8% | 13% | 16% | 15% | 19% | 9% | 8% |

Nejhorsi mesic -12.3%. Nahodne preskladane mesice (4 000 desetiletych drah): propad median 18%, v 5 % drah >= 28%, v 1 % >= 35%; rocne 5. / 50. / 95. percentil +18% / +28% / +39%.

## Odolnost (stejne velikosti)

| zmena | 2012-2022 rocne / propad | 2023-2026 rocne / propad |
|---|---|---|
| naklady 2x | +28.9% / 19% | +17.0% / 21% |
| rozhodnuti a vstup 1 h pred patecnim zaverem | +22.3% / 29% | +13.2% / 27% |
| vstup az po vikendu | +23.9% / 44% | +14.8% / 29% |
| sazby centralnich bank (o 2 mesice zpet) misto OECD | +18.1% / 45% | +25.5% / 22% |
| polovicni velikosti pozic | +15.0% / 10% | +10.4% / 10% |
