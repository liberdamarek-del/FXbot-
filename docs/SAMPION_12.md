# Sampion samouceni - 12 paru (profil max)

_CH-009 (12 paru) + velikost_podle_volatility + signal_i_rsi3. Velikosti vybrane jen na 2012-2022 (max. propad <= 20 %); roky 2023-2026 jsou test. Obchod po obchodu na hodinovych BID/ASK FXCM, naklady, swap, slozene uroceni._

## Pravidla

* rozhodnuti v patek pri dennim zaveru (23:00 Praha), 12 paru; TP 0.75 x ATR(14), SL 3.0 x ATR(14), nejdele 20 obchodnich dni; jedna pozice na par
* signal RSI2<5 nebo RSI3<15 (SELL zrcadlove), sazby se rozchazeji >= 0.25 p.b. + kladny carry -> marze **20% uctu**
* signal RSI2<5 (SELL zrcadlove), sazby se rozchazeji >= 0.25 p.b. -> marze **20% uctu**
* signal RSI2<5 (SELL zrcadlove), sazby se rozchazeji >= 0.1 p.b. -> marze **3% uctu**
* signal RSI2<5 (SELL zrcadlove), sazby se rozchazeji >= 0.0 p.b. -> marze **3% uctu**
* marze se nasobi 84 % / (stop obchodu v % marze), v mezich 0.5-2x: siroky stop = mensi pozice

## Vysledky

| obdobi | obchodu/rok | uspesnost | zisk/obchod (% marze) | ziskovych/mesic | mesicu s >= 2 ziskovymi | **rocne** | max. propad | max. vazana marze |
|---|---|---|---|---|---|---|---|---|
| 2012-2022 (vyber) | 40 | 87% | +7.7 % | 2.9 | 73% | **+36.7%** | 19.3% | 97% |
| **2023-2026 (test)** | 32 | 84% | +4.8 % | 2.2 | 62% | **+28.6%** | 20.3% | 97% |
| cele 2012-2026 | 38 | 87% | +7.1 % | 2.7 | 71% | **+34.6%** | 20.3% | 97% |

| rok | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| vynos | +6% | +1% | +37% | +100% | +6% | +12% | +95% | +73% | +22% | +58% | +57% | -11% | +37% | +18% |
| obchodu | 35 | 31 | 33 | 48 | 43 | 36 | 45 | 39 | 44 | 48 | 31 | 33 | 27 | 12 |
| propad | 7% | 15% | 3% | 3% | 6% | 7% | 1% | 10% | 8% | 19% | 18% | 17% | 17% | 17% |

Nejhorsi mesic -17.8%. Nahodne preskladane mesice (4 000 desetiletych drah): propad median 20%, v 5 % drah >= 31%, v 1 % >= 37%; rocne 5. / 50. / 95. percentil +20% / +34% / +49%.

## Odolnost (stejne velikosti)

| zmena | 2012-2022 rocne / propad | 2023-2026 rocne / propad |
|---|---|---|
| naklady 2x | +31.5% / 33% | +27.0% / 23% |
| rozhodnuti a vstup 1 h pred patecnim zaverem | +28.0% / 19% | +24.6% / 19% |
| vstup az po vikendu | +32.4% / 22% | +34.5% / 27% |
| sazby centralnich bank (o 2 mesice zpet) misto OECD | +19.7% / 53% | +45.6% / 36% |
| polovicni velikosti pozic | +17.5% / 10% | +14.3% / 10% |
