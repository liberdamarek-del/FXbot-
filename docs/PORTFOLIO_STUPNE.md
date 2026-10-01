# Odstupnovane portfolio: patecni propad + rozchazejici se sazby

_Obchod po obchodu na hodinovych BID/ASK FXCM 2012-2026 (25 paru), naklady + swap, slozene uroceni, jedna pozice na par, soucet marzi <= 100 % uctu. Velikosti stupnu vybrane jen na 2012-2022 (nejvyssi rocni vynos pri propadu <= 20%); 2023-2026 = test._

## Stupne

* **T1 sazby >= 0.25 p.b. + carry** - marze **8% uctu** na obchod; 143 obchodu 2013-2026
* **T2 sazby >= 0.25 p.b. (F1)** - marze **8% uctu** na obchod; 267 obchodu 2013-2026
* **T3 sazby >= 0.10 p.b.** - marze **3% uctu** na obchod; 510 obchodu 2013-2026
* **T4 sazby >= 0 p.b.** - marze **2% uctu** na obchod; 1002 obchodu 2013-2026

## Vysledek zvolenych velikosti

| obdobi | obchodu/rok | uspesnost | zisk/obchod (% marze) | ziskovych obchodu/mesic | mesicu s >= 2 ziskovymi | ziskovych mesicu | **rocne (slozene)** | max. propad | max. vazana marze / pozic |
|---|---|---|---|---|---|---|---|---|---|
| 2012-2022 (vyber) | 80 | 85% | +5.4 % | 5.6 | 89% | 70% | **+23.5%** | 19.2% | 78% / 14 |
| **2023-2026 (test)** | 63 | 85% | +6.0 % | 4.3 | 80% | 65% | **+24.2%** | 16.1% | 59% / 10 |
| cele 2012-2026 | 76 | 85% | +5.5 % | 5.3 | 87% | 69% | **+23.7%** | 19.2% | 78% / 14 |

Dalsi nejlepsi velikosti z vyberu (pro kontrolu, ze nejde o nahodu jedne kombinace):

| marze T1 / T2 / T3 / T4 | 2012-2022 rocne / propad | 2023-2026 rocne / propad |
|---|---|---|
| 8% / 8% / 3% / 2% | +23.5% / 19% | +24.2% / 16% |
| 8% / 6% / 4% / 2% | +23.0% / 19% | +22.6% / 19% |
| 6% / 6% / 5% / 3% | +22.5% / 20% | +19.1% / 24% |
| 8% / 8% / 3% / 1% | +22.3% / 19% | +22.8% / 16% |
| 8% / 4% / 4% / 3% | +22.2% / 20% | +22.6% / 18% |
| 8% / 8% / 2% / 2% | +22.2% / 18% | +24.4% / 14% |

## Srovnani: jednotlive stupne samostatne (stejna pravidla velikosti, propad <= 20 % na 2012-2022)

| pravidlo | obchodu/rok | zisk/obchod | marze | 2012-2022 rocne / propad | 2023-2026 rocne / propad | mesicu s >= 2 ziskovymi |
|---|---|---|---|---|---|---|
| T1 sazby >= 0.25 p.b. + carry | 11 | +13.2 % | 10% | +14.7% / 19% | +20.8% / 11% | 21% |
| T2 sazby >= 0.25 p.b. (F1) | 19 | +11.2 % | 10% | +21.7% / 19% | +28.0% / 16% | 32% |
| T3 sazby >= 0.10 p.b. | 36 | +9.0 % | 5% | +16.8% / 17% | +12.8% / 24% | 56% |
| T4 sazby >= 0 p.b. | 80 | +5.4 % | 2% | +8.7% / 14% | +7.5% / 10% | 89% |

## Rok po roku (zvolene velikosti)

| rok | obchodu | uspesnost | vynos roku | propad v roce | ziskovych obchodu/mesic | mesicu s >= 2 ziskovymi |
|---|---|---|---|---|---|---|
| 2013 | 63 | 81% | +8.2% | 8.0% | 3.9 | 77% |
| 2014 | 62 | 92% | +22.5% | 4.5% | 4.4 | 85% |
| 2015 | 62 | 84% | +26.5% | 7.4% | 4.7 | 100% |
| 2016 | 95 | 91% | +60.2% | 13.4% | 6.6 | 85% |
| 2017 | 74 | 78% | -2.1% | 8.1% | 4.5 | 85% |
| 2018 | 87 | 83% | +8.0% | 12.5% | 6.5 | 100% |
| 2019 | 80 | 92% | +44.6% | 3.5% | 5.7 | 85% |
| 2020 | 88 | 78% | +34.7% | 16.1% | 5.3 | 77% |
| 2021 | 103 | 87% | +14.2% | 7.6% | 6.9 | 92% |
| 2022 | 86 | 80% | +29.9% | 19.2% | 5.3 | 100% |
| 2023 | 71 | 90% | +70.2% | 14.4% | 4.9 | 92% |
| 2024 | 64 | 75% | -9.8% | 16.1% | 4.4 | 73% |
| 2025 | 49 | 86% | +18.0% | 6.2% | 3.5 | 75% |
| 2026 | 18 | 94% | +11.2% | 5.7% | 4.2 | 100% |

Nejhorsi mesic: -19.2%. Nahodne preskladane mesice (4 000 desetiletych drah): propad median 19%, v 5 % drah >= 28%, v 1 % drah >= 32%; rocni vynos 5. / 50. / 95. percentil +14% / +23% / +34%.

## Odolnost (stejne velikosti stupnu)

| varianta | 2012-2022 rocne / propad | 2023-2026 rocne / propad |
|---|---|---|
| naklady 2x | +19.9% / 19% | +22.8% / 16% |
| rozhodnuti a vstup 1 h pred patecnim zaverem | +22.8% / 19% | +19.1% / 15% |
| vstup az po vikendu (nedelni otevreni) | +18.6% / 34% | +28.0% / 14% |
| sazby CB o 2 mesice zpet misto OECD | +17.9% / 26% | +31.0% / 20% |
| sazby zname o 3 mesice zpet | +18.1% / 24% | +19.4% / 14% |
| cil >= 15 % marze (jen volatilnejsi trhy) | +20.3% / 17% | +21.0% / 14% |

_vypocet 18 s_
