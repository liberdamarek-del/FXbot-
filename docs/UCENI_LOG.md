# Denik uceni modelu

_Kazdy pokus o zlepseni: co se zkousi, vysledek ve dvou testovacich obdobich (vyber velikosti vzdy jen na starsich datech) a rozhodnuti. Prijato jen, kdyz roste rocni vynos o >= 1% v obou testech a propad se nezhorsi o vic nez 3%._

## 2026-10-01 - vychozi sampion CH-009 (41 paru)

2019-22: **+17.8%** rocne, propad 35% (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21% (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - jen_sazby_carry: PRIJATO

* jen nejsilnejsi stupen (sazby >= 0.25 + carry) - ostatni na 41 parech neprezily
* kandidat: 2019-22: **+19.7%** rocne, propad 24% (marze 8%); 2023-26: **+13.3%** rocne, propad 10% (marze 6%)
* sampion:  2019-22: **+17.8%** rocne, propad 35% (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21% (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - denni_limit_stupne: zamitnuto

* pridat stupne: denni limit 0.5 ATR po RSI(2) < 5, sazby >= 0.25 / 0.10, stop 4 ATR
* kandidat: 2019-22: **+10.7%** rocne, propad 42% (marze 10% / 3% / 2%); 2023-26: **+13.3%** rocne, propad 10% (marze 6% / 0% / 0%)
* sampion:  2019-22: **+19.7%** rocne, propad 24% (marze 8%); 2023-26: **+13.3%** rocne, propad 10% (marze 6%)

### 2026-10-01 - denni_limit_r14: zamitnuto

* pridat stupen: denni limit 0.5 ATR po %R14 < 10, sazby >= 0.25, stop 4 ATR
* kandidat: 2019-22: **+3.6%** rocne, propad 35% (marze 5% / 4%); 2023-26: **+13.3%** rocne, propad 10% (marze 6% / 0%)
* sampion:  2019-22: **+19.7%** rocne, propad 24% (marze 8%); 2023-26: **+13.3%** rocne, propad 10% (marze 6%)

### 2026-10-01 - cil_15_procent: zamitnuto

* obchodovat jen kdyz cil >= 15 % marze (volatilnejsi trhy)
* kandidat: 2019-22: **+18.8%** rocne, propad 26% (marze 8%); 2023-26: **+12.6%** rocne, propad 10% (marze 6%)
* sampion:  2019-22: **+19.7%** rocne, propad 24% (marze 8%); 2023-26: **+13.3%** rocne, propad 10% (marze 6%)

### 2026-10-01 - velikost_podle_volatility: PRIJATO

* marze obchodu neprimo umerna sirce stopu (stejne riziko na obchod, 0.5-2x)
* kandidat: 2019-22: **+22.9%** rocne, propad 22% (marze 12%); 2023-26: **+19.1%** rocne, propad 20% (marze 10%)
* sampion:  2019-22: **+19.7%** rocne, propad 24% (marze 8%); 2023-26: **+13.3%** rocne, propad 10% (marze 6%)

### 2026-10-01 - limit_meny_3: zamitnuto

* nejvyse 3 otevrene obchody dlouhe (kratke) v jedne mene
* kandidat: 2019-22: **+18.9%** rocne, propad 22% (marze 12%); 2023-26: **+17.6%** rocne, propad 20% (marze 10%)
* sampion:  2019-22: **+22.9%** rocne, propad 22% (marze 12%); 2023-26: **+19.1%** rocne, propad 20% (marze 10%)

### 2026-10-01 - limit_meny_2: zamitnuto

* nejvyse 2 otevrene obchody dlouhe (kratke) v jedne mene
* kandidat: 2019-22: **+19.5%** rocne, propad 24% (marze 12%); 2023-26: **+12.4%** rocne, propad 16% (marze 8%)
* sampion:  2019-22: **+22.9%** rocne, propad 22% (marze 12%); 2023-26: **+19.1%** rocne, propad 20% (marze 10%)

### 2026-10-01 - bez_extremnich_stopu: zamitnuto

* neobchodovat, kdyz stop > 150 % marze (extremni volatilita)
* kandidat: 2019-22: **+19.2%** rocne, propad 22% (marze 12%); 2023-26: **+19.1%** rocne, propad 20% (marze 10%)
* sampion:  2019-22: **+22.9%** rocne, propad 22% (marze 12%); 2023-26: **+19.1%** rocne, propad 20% (marze 10%)

### 2026-10-01 - slabe_stupne_i_rsi3: zamitnuto

* slabsi stupne (2 posledni) berou i signal RSI(3) < 15
* kandidat: 2019-22: **+14.8%** rocne, propad 23% (marze 8%); 2023-26: **+15.0%** rocne, propad 17% (marze 6%)
* sampion:  2019-22: **+22.9%** rocne, propad 22% (marze 12%); 2023-26: **+19.1%** rocne, propad 20% (marze 10%)

### 2026-10-01 - drzeni_10_dni: zamitnuto

* nejdele 10 obchodnich dni misto 20
* kandidat: 2019-22: **+19.7%** rocne, propad 22% (marze 12%); 2023-26: **+0.9%** rocne, propad 34% (marze 10%)
* sampion:  2019-22: **+22.9%** rocne, propad 22% (marze 12%); 2023-26: **+19.1%** rocne, propad 20% (marze 10%)

### 2026-10-01 - tp_1_atr: zamitnuto

* cil 1.0 ATR misto 0.75
* kandidat: 2019-22: **+15.5%** rocne, propad 21% (marze 8%); 2023-26: **+13.5%** rocne, propad 11% (marze 6%)
* sampion:  2019-22: **+22.9%** rocne, propad 22% (marze 12%); 2023-26: **+19.1%** rocne, propad 20% (marze 10%)

### 2026-10-01 - stop_4_atr: zamitnuto

* stop 4 ATR misto 3
* kandidat: 2019-22: **+15.6%** rocne, propad 19% (marze 10%); 2023-26: **+20.6%** rocne, propad 9% (marze 10%)
* sampion:  2019-22: **+22.9%** rocne, propad 22% (marze 12%); 2023-26: **+19.1%** rocne, propad 20% (marze 10%)

### 2026-10-01 - stupen_carry_bez_sazeb: zamitnuto

* dalsi nejslabsi stupen: jen carry ve smeru obchodu (sazby se nemeni)
* kandidat: 2019-22: **+22.9%** rocne, propad 22% (marze 12% / 0%); 2023-26: **+19.1%** rocne, propad 20% (marze 10% / 0%)
* sampion:  2019-22: **+22.9%** rocne, propad 22% (marze 12%); 2023-26: **+19.1%** rocne, propad 20% (marze 10%)

### 2026-10-01 - stupen_sazby_cb: zamitnuto

* dalsi stupen: totez se sazbami centralnich bank (o 2 mesice zpet) misto OECD
* kandidat: 2019-22: **+22.9%** rocne, propad 22% (marze 12% / 0%); 2023-26: **+19.1%** rocne, propad 20% (marze 10% / 0%)
* sampion:  2019-22: **+22.9%** rocne, propad 22% (marze 12%); 2023-26: **+19.1%** rocne, propad 20% (marze 10%)

### 2026-10-01 - signal_i_rsi3: zamitnuto

* nejsilnejsi stupen bere i signal RSI(3) < 15
* kandidat: 2019-22: **+14.8%** rocne, propad 23% (marze 8%); 2023-26: **+15.0%** rocne, propad 17% (marze 6%)
* sampion:  2019-22: **+22.9%** rocne, propad 22% (marze 12%); 2023-26: **+19.1%** rocne, propad 20% (marze 10%)

### 2026-10-01 - signal_i_r14: zamitnuto

* nejsilnejsi stupen bere i signal %R14 < 10
* kandidat: 2019-22: **+14.5%** rocne, propad 19% (marze 6%); 2023-26: **+23.4%** rocne, propad 11% (marze 6%)
* sampion:  2019-22: **+22.9%** rocne, propad 22% (marze 12%); 2023-26: **+19.1%** rocne, propad 20% (marze 10%)

### 2026-10-01 - prah_sazeb_015: zamitnuto

* nejsilnejsi stupen: zmena sazeb >= 0.15 p.b. misto 0.25
* kandidat: 2019-22: **+10.0%** rocne, propad 17% (marze 6%); 2023-26: **+12.1%** rocne, propad 16% (marze 6%)
* sampion:  2019-22: **+22.9%** rocne, propad 22% (marze 12%); 2023-26: **+19.1%** rocne, propad 20% (marze 10%)

### 2026-10-01 - patek_limit_05: zamitnuto

* patecni vstup limitem 0.5 ATR pod zaverem (platny tyden) misto trhu
* kandidat: 2019-22: **+19.6%** rocne, propad 23% (marze 8%); 2023-26: **+7.7%** rocne, propad 10% (marze 6%)
* sampion:  2019-22: **+22.9%** rocne, propad 22% (marze 12%); 2023-26: **+19.1%** rocne, propad 20% (marze 10%)

### 2026-10-01 - denni_sazby_carry: zamitnuto

* dalsi stupen: denni limit 0.5 ATR po RSI(2) < 5 se sazbami >= 0.25 + carry
* kandidat: 2019-22: **+22.9%** rocne, propad 22% (marze 12% / 0%); 2023-26: **+19.1%** rocne, propad 20% (marze 10% / 0%)
* sampion:  2019-22: **+22.9%** rocne, propad 22% (marze 12%); 2023-26: **+19.1%** rocne, propad 20% (marze 10%)

### 2026-10-01 - vix_pod_30: zamitnuto

* neotevirat, kdyz je VIX nad 30 (panika na trzich)
* kandidat: 2019-22: **+9.7%** rocne, propad 32% (marze 12%); 2023-26: **+10.3%** rocne, propad 12% (marze 6%)
* sampion:  2019-22: **+22.9%** rocne, propad 22% (marze 12%); 2023-26: **+19.1%** rocne, propad 20% (marze 10%)

### 2026-10-01 - vix_pod_25: zamitnuto

* neotevirat, kdyz je VIX nad 25
* kandidat: 2019-22: **+10.6%** rocne, propad 22% (marze 12%); 2023-26: **+17.1%** rocne, propad 20% (marze 10%)
* sampion:  2019-22: **+22.9%** rocne, propad 22% (marze 12%); 2023-26: **+19.1%** rocne, propad 20% (marze 10%)

### 2026-10-01 - vix_bez_skoku: zamitnuto

* neotevirat, kdyz VIX za 5 dni vzrostl o vic nez 5 bodu
* kandidat: 2019-22: **+19.6%** rocne, propad 19% (marze 10%); 2023-26: **+14.4%** rocne, propad 20% (marze 10%)
* sampion:  2019-22: **+22.9%** rocne, propad 22% (marze 12%); 2023-26: **+19.1%** rocne, propad 20% (marze 10%)

## 2026-10-01 - profil mesicne: vychozi sampion CH-009 (41 paru)

2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] jen_sazby_carry: zamitnuto

* jen nejsilnejsi stupen (sazby >= 0.25 + carry) - ostatni na 41 parech neprezily
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] denni_limit_stupne: zamitnuto

* pridat stupne: denni limit 0.5 ATR po RSI(2) < 5, sazby >= 0.25 / 0.10, stop 4 ATR
* kandidat: 2019-22: **+4.3%** rocne, propad 40%, 12.0 ziskovych/mesic (marze 8% / 6% / 2% / 2% / 2% / 2%); 2023-26: **+11.6%** rocne, propad 12%, 4.5 ziskovych/mesic (marze 6% / 2% / 2% / 0% / 0% / 0%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] denni_limit_r14: zamitnuto

* pridat stupen: denni limit 0.5 ATR po %R14 < 10, sazby >= 0.25, stop 4 ATR
* kandidat: 2019-22: **+16.5%** rocne, propad 36%, 9.0 ziskovych/mesic (marze 6% / 6% / 4% / 2% / 0%); 2023-26: **+11.6%** rocne, propad 12%, 4.5 ziskovych/mesic (marze 6% / 2% / 2% / 0% / 0%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] cil_15_procent: zamitnuto

* obchodovat jen kdyz cil >= 15 % marze (volatilnejsi trhy)
* kandidat: 2019-22: **+15.2%** rocne, propad 38%, 6.0 ziskovych/mesic (marze 8% / 6% / 2% / 2%); 2023-26: **+11.9%** rocne, propad 19%, 4.3 ziskovych/mesic (marze 5% / 3% / 3% / 1%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] velikost_podle_volatility: zamitnuto

* marze obchodu neprimo umerna sirce stopu (stejne riziko na obchod, 0.5-2x)
* kandidat: 2019-22: **+33.9%** rocne, propad 31%, 5.1 ziskovych/mesic (marze 8% / 8% / 8% / 0%); 2023-26: **+7.8%** rocne, propad 37%, 6.2 ziskovych/mesic (marze 6% / 6% / 4% / 1%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] limit_meny_3: zamitnuto

* nejvyse 3 otevrene obchody dlouhe (kratke) v jedne mene
* kandidat: 2019-22: **+11.5%** rocne, propad 33%, 7.6 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+14.2%** rocne, propad 17%, 4.1 ziskovych/mesic (marze 8% / 3% / 3% / 0%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] limit_meny_2: zamitnuto

* nejvyse 2 otevrene obchody dlouhe (kratke) v jedne mene
* kandidat: 2019-22: **+10.9%** rocne, propad 32%, 6.3 ziskovych/mesic (marze 6% / 6% / 3% / 1%); 2023-26: **+10.3%** rocne, propad 15%, 4.6 ziskovych/mesic (marze 6% / 3% / 3% / 1%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] bez_extremnich_stopu: zamitnuto

* neobchodovat, kdyz stop > 150 % marze (extremni volatilita)
* kandidat: 2019-22: **+34.3%** rocne, propad 32%, 8.7 ziskovych/mesic (marze 10% / 8% / 8% / 1%); 2023-26: **+15.6%** rocne, propad 28%, 4.5 ziskovych/mesic (marze 8% / 8% / 2% / 0%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] slabe_stupne_i_rsi3: zamitnuto

* slabsi stupne (2 posledni) berou i signal RSI(3) < 15
* kandidat: 2019-22: **+24.8%** rocne, propad 32%, 6.8 ziskovych/mesic (marze 10% / 5% / 1% / 0%); 2023-26: **+11.5%** rocne, propad 12%, 6.1 ziskovych/mesic (marze 5% / 3% / 1% / 0%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] drzeni_10_dni: zamitnuto

* nejdele 10 obchodnich dni misto 20
* kandidat: 2019-22: **+33.2%** rocne, propad 24%, 9.0 ziskovych/mesic (marze 8% / 8% / 4% / 1%); 2023-26: **+6.5%** rocne, propad 27%, 4.9 ziskovych/mesic (marze 6% / 6% / 4% / 0%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] tp_1_atr: zamitnuto

* cil 1.0 ATR misto 0.75
* kandidat: 2019-22: **+10.7%** rocne, propad 17%, 4.7 ziskovych/mesic (marze 5% / 2% / 1% / 0%); 2023-26: **+11.5%** rocne, propad 10%, 4.3 ziskovych/mesic (marze 5% / 2% / 1% / 0%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] stop_4_atr: zamitnuto

* stop 4 ATR misto 3
* kandidat: 2019-22: **+23.5%** rocne, propad 41%, 5.0 ziskovych/mesic (marze 8% / 8% / 6% / 0%); 2023-26: **+13.8%** rocne, propad 19%, 4.5 ziskovych/mesic (marze 5% / 3% / 3% / 0%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] stupen_carry_bez_sazeb: zamitnuto

* dalsi nejslabsi stupen: jen carry ve smeru obchodu (sazby se nemeni)
* kandidat: 2019-22: **+16.5%** rocne, propad 36%, 9.0 ziskovych/mesic (marze 6% / 6% / 4% / 2% / 0%); 2023-26: **+11.6%** rocne, propad 12%, 4.5 ziskovych/mesic (marze 6% / 2% / 2% / 0% / 0%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] stupen_sazby_cb: zamitnuto

* dalsi stupen: totez se sazbami centralnich bank (o 2 mesice zpet) misto OECD
* kandidat: 2019-22: **+17.3%** rocne, propad 36%, 9.2 ziskovych/mesic (marze 6% / 6% / 4% / 2% / 2%); 2023-26: **+11.6%** rocne, propad 12%, 4.5 ziskovych/mesic (marze 6% / 2% / 2% / 0% / 0%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] signal_i_rsi3: zamitnuto

* nejsilnejsi stupen bere i signal RSI(3) < 15
* kandidat: 2019-22: **+25.9%** rocne, propad 41%, 9.8 ziskovych/mesic (marze 8% / 8% / 4% / 1%); 2023-26: **+8.1%** rocne, propad 21%, 5.0 ziskovych/mesic (marze 4% / 3% / 3% / 0%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] signal_i_r14: zamitnuto

* nejsilnejsi stupen bere i signal %R14 < 10
* kandidat: 2019-22: **+24.2%** rocne, propad 34%, 10.1 ziskovych/mesic (marze 6% / 6% / 3% / 1%); 2023-26: **+12.0%** rocne, propad 22%, 5.4 ziskovych/mesic (marze 4% / 3% / 3% / 0%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] prah_sazeb_015: zamitnuto

* nejsilnejsi stupen: zmena sazeb >= 0.15 p.b. misto 0.25
* kandidat: 2019-22: **+21.8%** rocne, propad 32%, 9.0 ziskovych/mesic (marze 8% / 6% / 2% / 1%); 2023-26: **+11.7%** rocne, propad 24%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] patek_limit_05: zamitnuto

* patecni vstup limitem 0.5 ATR pod zaverem (platny tyden) misto trhu
* kandidat: 2019-22: **+27.6%** rocne, propad 39%, 9.3 ziskovych/mesic (marze 20% / 6% / 5% / 2%); 2023-26: **+6.2%** rocne, propad 25%, 4.6 ziskovych/mesic (marze 8% / 3% / 3% / 0%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] denni_sazby_carry: zamitnuto

* dalsi stupen: denni limit 0.5 ATR po RSI(2) < 5 se sazbami >= 0.25 + carry
* kandidat: 2019-22: **+16.5%** rocne, propad 36%, 9.0 ziskovych/mesic (marze 6% / 6% / 4% / 2% / 0%); 2023-26: **+11.6%** rocne, propad 12%, 4.5 ziskovych/mesic (marze 6% / 2% / 2% / 0% / 0%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] vix_pod_30: zamitnuto

* neotevirat, kdyz je VIX nad 30 (panika na trzich)
* kandidat: 2019-22: **+8.8%** rocne, propad 35%, 8.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+5.2%** rocne, propad 23%, 4.2 ziskovych/mesic (marze 4% / 3% / 3% / 0%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] vix_pod_25: zamitnuto

* neotevirat, kdyz je VIX nad 25
* kandidat: 2019-22: **+27.9%** rocne, propad 31%, 6.6 ziskovych/mesic (marze 8% / 8% / 8% / 1%); 2023-26: **+4.4%** rocne, propad 35%, 5.5 ziskovych/mesic (marze 6% / 5% / 5% / 1%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

### 2026-10-01 - [champion_mesicne] vix_bez_skoku: zamitnuto

* neotevirat, kdyz VIX za 5 dni vzrostl o vic nez 5 bodu
* kandidat: 2019-22: **+27.5%** rocne, propad 41%, 8.0 ziskovych/mesic (marze 8% / 8% / 8% / 1%); 2023-26: **+7.2%** rocne, propad 24%, 4.0 ziskovych/mesic (marze 6% / 3% / 3% / 0%)
* sampion:  2019-22: **+17.8%** rocne, propad 35%, 9.0 ziskovych/mesic (marze 6% / 6% / 5% / 2%); 2023-26: **+10.7%** rocne, propad 21%, 4.5 ziskovych/mesic (marze 6% / 3% / 3% / 0%)

## 2026-10-01 - profil max: vychozi sampion CH-009 (12 paru)

2019-22: **+64.5%** rocne, propad 30%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: **+9.7%** rocne, propad 26%, 2.0 ziskovych/mesic (marze 12% / 12% / 6% / 6%)

### 2026-10-01 - [champion_12] jen_sazby_carry: zamitnuto

* jen nejsilnejsi stupen (sazby >= 0.25 + carry) - ostatni na 41 parech neprezily
* kandidat: 2019-22: **+22.9%** rocne, propad 24%, 0.6 ziskovych/mesic (marze 20%); 2023-26: **+9.1%** rocne, propad 11%, 0.4 ziskovych/mesic (marze 15%)
* sampion:  2019-22: **+64.5%** rocne, propad 30%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: **+9.7%** rocne, propad 26%, 2.0 ziskovych/mesic (marze 12% / 12% / 6% / 6%)

### 2026-10-01 - [champion_12] denni_limit_stupne: zamitnuto

* pridat stupne: denni limit 0.5 ATR po RSI(2) < 5, sazby >= 0.25 / 0.10, stop 4 ATR
* kandidat: 2019-22: **+51.9%** rocne, propad 24%, 3.1 ziskovych/mesic (marze 15% / 15% / 8% / 6% / 0% / 0%); 2023-26: **+9.5%** rocne, propad 35%, 2.4 ziskovych/mesic (marze 15% / 15% / 8% / 6% / 6% / 0%)
* sampion:  2019-22: **+64.5%** rocne, propad 30%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: **+9.7%** rocne, propad 26%, 2.0 ziskovych/mesic (marze 12% / 12% / 6% / 6%)

### 2026-10-01 - [champion_12] denni_limit_r14: zamitnuto

* pridat stupen: denni limit 0.5 ATR po %R14 < 10, sazby >= 0.25, stop 4 ATR
* kandidat: 2019-22: **+51.9%** rocne, propad 24%, 3.1 ziskovych/mesic (marze 15% / 15% / 8% / 6% / 0%); 2023-26: **+7.3%** rocne, propad 29%, 2.0 ziskovych/mesic (marze 10% / 10% / 8% / 6% / 0%)
* sampion:  2019-22: **+64.5%** rocne, propad 30%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: **+9.7%** rocne, propad 26%, 2.0 ziskovych/mesic (marze 12% / 12% / 6% / 6%)

### 2026-10-01 - [champion_12] cil_15_procent: zamitnuto

* obchodovat jen kdyz cil >= 15 % marze (volatilnejsi trhy)
* kandidat: 2019-22: **+44.3%** rocne, propad 31%, 1.9 ziskovych/mesic (marze 20% / 20% / 10% / 6%); 2023-26: **+3.9%** rocne, propad 28%, 1.3 ziskovych/mesic (marze 12% / 12% / 6% / 6%)
* sampion:  2019-22: **+64.5%** rocne, propad 30%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: **+9.7%** rocne, propad 26%, 2.0 ziskovych/mesic (marze 12% / 12% / 6% / 6%)

### 2026-10-01 - [champion_12] velikost_podle_volatility: PRIJATO

* marze obchodu neprimo umerna sirce stopu (stejne riziko na obchod, 0.5-2x)
* kandidat: 2019-22: **+71.6%** rocne, propad 25%, 3.1 ziskovych/mesic (marze 20% / 20% / 10% / 5%); 2023-26: **+17.3%** rocne, propad 24%, 2.0 ziskovych/mesic (marze 20% / 20% / 3% / 3%)
* sampion:  2019-22: **+64.5%** rocne, propad 30%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: **+9.7%** rocne, propad 26%, 2.0 ziskovych/mesic (marze 12% / 12% / 6% / 6%)

### 2026-10-01 - [champion_12] limit_meny_3: zamitnuto

* nejvyse 3 otevrene obchody dlouhe (kratke) v jedne mene
* kandidat: 2019-22: **+67.1%** rocne, propad 23%, 3.0 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: **+7.8%** rocne, propad 38%, 1.9 ziskovych/mesic (marze 15% / 15% / 8% / 6%)
* sampion:  2019-22: **+71.6%** rocne, propad 25%, 3.1 ziskovych/mesic (marze 20% / 20% / 10% / 5%); 2023-26: **+17.3%** rocne, propad 24%, 2.0 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] limit_meny_2: zamitnuto

* nejvyse 2 otevrene obchody dlouhe (kratke) v jedne mene
* kandidat: 2019-22: **+60.4%** rocne, propad 23%, 2.7 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: **+5.2%** rocne, propad 37%, 1.7 ziskovych/mesic (marze 15% / 15% / 8% / 6%)
* sampion:  2019-22: **+71.6%** rocne, propad 25%, 3.1 ziskovych/mesic (marze 20% / 20% / 10% / 5%); 2023-26: **+17.3%** rocne, propad 24%, 2.0 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] bez_extremnich_stopu: zamitnuto

* neobchodovat, kdyz stop > 150 % marze (extremni volatilita)
* kandidat: 2019-22: **+69.0%** rocne, propad 25%, 3.0 ziskovych/mesic (marze 20% / 20% / 10% / 5%); 2023-26: **+17.3%** rocne, propad 24%, 2.0 ziskovych/mesic (marze 20% / 20% / 3% / 3%)
* sampion:  2019-22: **+71.6%** rocne, propad 25%, 3.1 ziskovych/mesic (marze 20% / 20% / 10% / 5%); 2023-26: **+17.3%** rocne, propad 24%, 2.0 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] slabe_stupne_i_rsi3: zamitnuto

* slabsi stupne (2 posledni) berou i signal RSI(3) < 15
* kandidat: 2019-22: **+53.4%** rocne, propad 20%, 3.9 ziskovych/mesic (marze 20% / 20% / 4% / 4%); 2023-26: **+16.8%** rocne, propad 29%, 2.7 ziskovych/mesic (marze 20% / 20% / 3% / 3%)
* sampion:  2019-22: **+71.6%** rocne, propad 25%, 3.1 ziskovych/mesic (marze 20% / 20% / 10% / 5%); 2023-26: **+17.3%** rocne, propad 24%, 2.0 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] drzeni_10_dni: zamitnuto

* nejdele 10 obchodnich dni misto 20
* kandidat: 2019-22: **+65.3%** rocne, propad 25%, 3.0 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+3.2%** rocne, propad 37%, 2.1 ziskovych/mesic (marze 20% / 20% / 3% / 3%)
* sampion:  2019-22: **+71.6%** rocne, propad 25%, 3.1 ziskovych/mesic (marze 20% / 20% / 10% / 5%); 2023-26: **+17.3%** rocne, propad 24%, 2.0 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] tp_1_atr: zamitnuto

* cil 1.0 ATR misto 0.75
* kandidat: 2019-22: **+24.3%** rocne, propad 36%, 0.8 ziskovych/mesic (marze 20% / 20% / 0% / 0%); 2023-26: **+13.7%** rocne, propad 29%, 1.9 ziskovych/mesic (marze 20% / 10% / 3% / 3%)
* sampion:  2019-22: **+71.6%** rocne, propad 25%, 3.1 ziskovych/mesic (marze 20% / 20% / 10% / 5%); 2023-26: **+17.3%** rocne, propad 24%, 2.0 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] stop_4_atr: zamitnuto

* stop 4 ATR misto 3
* kandidat: 2019-22: **+50.1%** rocne, propad 17%, 3.1 ziskovych/mesic (marze 20% / 20% / 6% / 5%); 2023-26: **+21.0%** rocne, propad 16%, 2.0 ziskovych/mesic (marze 20% / 20% / 6% / 5%)
* sampion:  2019-22: **+71.6%** rocne, propad 25%, 3.1 ziskovych/mesic (marze 20% / 20% / 10% / 5%); 2023-26: **+17.3%** rocne, propad 24%, 2.0 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] stupen_carry_bez_sazeb: zamitnuto

* dalsi nejslabsi stupen: jen carry ve smeru obchodu (sazby se nemeni)
* kandidat: 2019-22: **+55.5%** rocne, propad 21%, 3.1 ziskovych/mesic (marze 15% / 15% / 10% / 4% / 0%); 2023-26: **+9.8%** rocne, propad 37%, 2.0 ziskovych/mesic (marze 15% / 15% / 8% / 4% / 0%)
* sampion:  2019-22: **+71.6%** rocne, propad 25%, 3.1 ziskovych/mesic (marze 20% / 20% / 10% / 5%); 2023-26: **+17.3%** rocne, propad 24%, 2.0 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] stupen_sazby_cb: zamitnuto

* dalsi stupen: totez se sazbami centralnich bank (o 2 mesice zpet) misto OECD
* kandidat: 2019-22: **+55.5%** rocne, propad 21%, 3.1 ziskovych/mesic (marze 15% / 15% / 10% / 4% / 0%); 2023-26: **+10.4%** rocne, propad 37%, 2.1 ziskovych/mesic (marze 15% / 15% / 8% / 4% / 4%)
* sampion:  2019-22: **+71.6%** rocne, propad 25%, 3.1 ziskovych/mesic (marze 20% / 20% / 10% / 5%); 2023-26: **+17.3%** rocne, propad 24%, 2.0 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] signal_i_rsi3: PRIJATO

* nejsilnejsi stupen bere i signal RSI(3) < 15
* kandidat: 2019-22: **+74.2%** rocne, propad 25%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+28.6%** rocne, propad 20%, 2.2 ziskovych/mesic (marze 20% / 20% / 3% / 3%)
* sampion:  2019-22: **+71.6%** rocne, propad 25%, 3.1 ziskovych/mesic (marze 20% / 20% / 10% / 5%); 2023-26: **+17.3%** rocne, propad 24%, 2.0 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] signal_i_r14: zamitnuto

* nejsilnejsi stupen bere i signal %R14 < 10
* kandidat: 2019-22: **+69.4%** rocne, propad 25%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 5%); 2023-26: **+25.0%** rocne, propad 32%, 2.4 ziskovych/mesic (marze 15% / 15% / 8% / 5%)
* sampion:  2019-22: **+74.2%** rocne, propad 25%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+28.6%** rocne, propad 20%, 2.2 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] prah_sazeb_015: zamitnuto

* nejsilnejsi stupen: zmena sazeb >= 0.15 p.b. misto 0.25
* kandidat: 2019-22: **+51.2%** rocne, propad 25%, 3.4 ziskovych/mesic (marze 15% / 15% / 4% / 4%); 2023-26: **+11.7%** rocne, propad 40%, 2.3 ziskovych/mesic (marze 10% / 10% / 10% / 4%)
* sampion:  2019-22: **+74.2%** rocne, propad 25%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+28.6%** rocne, propad 20%, 2.2 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] patek_limit_05: zamitnuto

* patecni vstup limitem 0.5 ATR pod zaverem (platny tyden) misto trhu
* kandidat: 2019-22: **+66.8%** rocne, propad 30%, 3.2 ziskovych/mesic (marze 20% / 20% / 10% / 5%); 2023-26: **+12.2%** rocne, propad 37%, 2.1 ziskovych/mesic (marze 20% / 20% / 2% / 2%)
* sampion:  2019-22: **+74.2%** rocne, propad 25%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+28.6%** rocne, propad 20%, 2.2 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] denni_sazby_carry: zamitnuto

* dalsi stupen: denni limit 0.5 ATR po RSI(2) < 5 se sazbami >= 0.25 + carry
* kandidat: 2019-22: **+59.9%** rocne, propad 21%, 3.3 ziskovych/mesic (marze 15% / 15% / 10% / 4% / 0%); 2023-26: **+17.6%** rocne, propad 34%, 2.2 ziskovych/mesic (marze 15% / 15% / 8% / 4% / 0%)
* sampion:  2019-22: **+74.2%** rocne, propad 25%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+28.6%** rocne, propad 20%, 2.2 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] vix_pod_30: zamitnuto

* neotevirat, kdyz je VIX nad 30 (panika na trzich)
* kandidat: 2019-22: **+64.1%** rocne, propad 25%, 3.0 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+24.9%** rocne, propad 20%, 2.2 ziskovych/mesic (marze 20% / 20% / 3% / 3%)
* sampion:  2019-22: **+74.2%** rocne, propad 25%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+28.6%** rocne, propad 20%, 2.2 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] vix_pod_25: zamitnuto

* neotevirat, kdyz je VIX nad 25
* kandidat: 2019-22: **+64.5%** rocne, propad 17%, 2.6 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+13.8%** rocne, propad 42%, 2.1 ziskovych/mesic (marze 20% / 20% / 10% / 4%)
* sampion:  2019-22: **+74.2%** rocne, propad 25%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+28.6%** rocne, propad 20%, 2.2 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] vix_bez_skoku: zamitnuto

* neotevirat, kdyz VIX za 5 dni vzrostl o vic nez 5 bodu
* kandidat: 2019-22: **+71.6%** rocne, propad 22%, 2.9 ziskovych/mesic (marze 20% / 20% / 6% / 5%); 2023-26: **+22.5%** rocne, propad 21%, 2.0 ziskovych/mesic (marze 20% / 20% / 3% / 3%)
* sampion:  2019-22: **+74.2%** rocne, propad 25%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+28.6%** rocne, propad 20%, 2.2 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

## 2026-10-01 - profil mesicne: vychozi sampion CH-009 (12 paru)

2019-22: **+64.5%** rocne, propad 30%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: -

### 2026-10-01 - [champion_12_mesicne] jen_sazby_carry: zamitnuto

* jen nejsilnejsi stupen (sazby >= 0.25 + carry) - ostatni na 41 parech neprezily
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+64.5%** rocne, propad 30%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: -

### 2026-10-01 - [champion_12_mesicne] denni_limit_stupne: zamitnuto

* pridat stupne: denni limit 0.5 ATR po RSI(2) < 5, sazby >= 0.25 / 0.10, stop 4 ATR
* kandidat: 2019-22: **+51.9%** rocne, propad 24%, 3.1 ziskovych/mesic (marze 15% / 15% / 8% / 6% / 0% / 0%); 2023-26: **+9.5%** rocne, propad 35%, 2.4 ziskovych/mesic (marze 15% / 15% / 8% / 6% / 6% / 0%)
* sampion:  2019-22: **+64.5%** rocne, propad 30%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: -

### 2026-10-01 - [champion_12_mesicne] denni_limit_r14: zamitnuto

* pridat stupen: denni limit 0.5 ATR po %R14 < 10, sazby >= 0.25, stop 4 ATR
* kandidat: 2019-22: **+51.9%** rocne, propad 24%, 3.1 ziskovych/mesic (marze 15% / 15% / 8% / 6% / 0%); 2023-26: **+10.5%** rocne, propad 21%, 3.2 ziskovych/mesic (marze 10% / 10% / 8% / 6% / 2%)
* sampion:  2019-22: **+64.5%** rocne, propad 30%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: -

### 2026-10-01 - [champion_12_mesicne] cil_15_procent: zamitnuto

* obchodovat jen kdyz cil >= 15 % marze (volatilnejsi trhy)
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+64.5%** rocne, propad 30%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: -

### 2026-10-01 - [champion_12_mesicne] velikost_podle_volatility: zamitnuto

* marze obchodu neprimo umerna sirce stopu (stejne riziko na obchod, 0.5-2x)
* kandidat: 2019-22: **+71.6%** rocne, propad 25%, 3.1 ziskovych/mesic (marze 20% / 20% / 10% / 5%); 2023-26: -
* sampion:  2019-22: **+64.5%** rocne, propad 30%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: -

### 2026-10-01 - [champion_12_mesicne] limit_meny_3: zamitnuto

* nejvyse 3 otevrene obchody dlouhe (kratke) v jedne mene
* kandidat: 2019-22: **+60.8%** rocne, propad 30%, 3.0 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: -
* sampion:  2019-22: **+64.5%** rocne, propad 30%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: -

### 2026-10-01 - [champion_12_mesicne] limit_meny_2: zamitnuto

* nejvyse 2 otevrene obchody dlouhe (kratke) v jedne mene
* kandidat: 2019-22: **+53.4%** rocne, propad 30%, 2.7 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: -
* sampion:  2019-22: **+64.5%** rocne, propad 30%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: -

### 2026-10-01 - [champion_12_mesicne] bez_extremnich_stopu: zamitnuto

* neobchodovat, kdyz stop > 150 % marze (extremni volatilita)
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+64.5%** rocne, propad 30%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: -

### 2026-10-01 - [champion_12_mesicne] slabe_stupne_i_rsi3: zamitnuto

* slabsi stupne (2 posledni) berou i signal RSI(3) < 15
* kandidat: 2019-22: **+54.4%** rocne, propad 28%, 3.9 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+11.4%** rocne, propad 23%, 2.8 ziskovych/mesic (marze 15% / 15% / 2% / 2%)
* sampion:  2019-22: **+64.5%** rocne, propad 30%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: -

### 2026-10-01 - [champion_12_mesicne] drzeni_10_dni: zamitnuto

* nejdele 10 obchodnich dni misto 20
* kandidat: 2019-22: **+60.6%** rocne, propad 30%, 3.0 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: -
* sampion:  2019-22: **+64.5%** rocne, propad 30%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: -

### 2026-10-01 - [champion_12_mesicne] tp_1_atr: zamitnuto

* cil 1.0 ATR misto 0.75
* kandidat: 2019-22: **+31.7%** rocne, propad 31%, 2.9 ziskovych/mesic (marze 20% / 15% / 1% / 1%); 2023-26: **+11.6%** rocne, propad 20%, 1.9 ziskovych/mesic (marze 15% / 8% / 2% / 2%)
* sampion:  2019-22: **+64.5%** rocne, propad 30%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: -

### 2026-10-01 - [champion_12_mesicne] stop_4_atr: PRIJATO

* stop 4 ATR misto 3
* kandidat: 2019-22: **+67.0%** rocne, propad 26%, 3.1 ziskovych/mesic (marze 20% / 20% / 6% / 5%); 2023-26: **+17.0%** rocne, propad 23%, 2.0 ziskovych/mesic (marze 15% / 15% / 6% / 5%)
* sampion:  2019-22: **+64.5%** rocne, propad 30%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 6%); 2023-26: -

### 2026-10-01 - [champion_12_mesicne] stupen_carry_bez_sazeb: zamitnuto

* dalsi nejslabsi stupen: jen carry ve smeru obchodu (sazby se nemeni)
* kandidat: 2019-22: **+50.2%** rocne, propad 19%, 3.1 ziskovych/mesic (marze 15% / 15% / 6% / 4% / 0%); 2023-26: **+17.1%** rocne, propad 29%, 2.7 ziskovych/mesic (marze 15% / 15% / 8% / 4% / 2%)
* sampion:  2019-22: **+67.0%** rocne, propad 26%, 3.1 ziskovych/mesic (marze 20% / 20% / 6% / 5%); 2023-26: **+17.0%** rocne, propad 23%, 2.0 ziskovych/mesic (marze 15% / 15% / 6% / 5%)

### 2026-10-01 - [champion_12_mesicne] stupen_sazby_cb: zamitnuto

* dalsi stupen: totez se sazbami centralnich bank (o 2 mesice zpet) misto OECD
* kandidat: 2019-22: **+50.2%** rocne, propad 19%, 3.1 ziskovych/mesic (marze 15% / 15% / 6% / 4% / 0%); 2023-26: **+16.4%** rocne, propad 25%, 2.1 ziskovych/mesic (marze 15% / 15% / 6% / 4% / 4%)
* sampion:  2019-22: **+67.0%** rocne, propad 26%, 3.1 ziskovych/mesic (marze 20% / 20% / 6% / 5%); 2023-26: **+17.0%** rocne, propad 23%, 2.0 ziskovych/mesic (marze 15% / 15% / 6% / 5%)

### 2026-10-01 - [champion_12_mesicne] signal_i_rsi3: PRIJATO

* nejsilnejsi stupen bere i signal RSI(3) < 15
* kandidat: 2019-22: **+75.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+26.6%** rocne, propad 22%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 6%)
* sampion:  2019-22: **+67.0%** rocne, propad 26%, 3.1 ziskovych/mesic (marze 20% / 20% / 6% / 5%); 2023-26: **+17.0%** rocne, propad 23%, 2.0 ziskovych/mesic (marze 15% / 15% / 6% / 5%)

### 2026-10-01 - [champion_12_mesicne] signal_i_r14: zamitnuto

* nejsilnejsi stupen bere i signal %R14 < 10
* kandidat: 2019-22: **+67.4%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%); 2023-26: **+28.8%** rocne, propad 22%, 2.4 ziskovych/mesic (marze 15% / 15% / 6% / 5%)
* sampion:  2019-22: **+75.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+26.6%** rocne, propad 22%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 6%)

### 2026-10-01 - [champion_12_mesicne] prah_sazeb_015: zamitnuto

* nejsilnejsi stupen: zmena sazeb >= 0.15 p.b. misto 0.25
* kandidat: 2019-22: **+48.1%** rocne, propad 15%, 3.4 ziskovych/mesic (marze 12% / 12% / 5% / 5%); 2023-26: **+23.6%** rocne, propad 19%, 2.3 ziskovych/mesic (marze 12% / 12% / 5% / 5%)
* sampion:  2019-22: **+75.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+26.6%** rocne, propad 22%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 6%)

### 2026-10-01 - [champion_12_mesicne] patek_limit_05: zamitnuto

* patecni vstup limitem 0.5 ATR pod zaverem (platny tyden) misto trhu
* kandidat: 2019-22: **+75.3%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+18.8%** rocne, propad 30%, 2.1 ziskovych/mesic (marze 20% / 15% / 6% / 6%)
* sampion:  2019-22: **+75.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+26.6%** rocne, propad 22%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 6%)

### 2026-10-01 - [champion_12_mesicne] denni_sazby_carry: zamitnuto

* dalsi stupen: denni limit 0.5 ATR po RSI(2) < 5 se sazbami >= 0.25 + carry
* kandidat: 2019-22: **+58.4%** rocne, propad 19%, 3.3 ziskovych/mesic (marze 15% / 15% / 6% / 6% / 0%); 2023-26: **+26.6%** rocne, propad 22%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 6% / 0%)
* sampion:  2019-22: **+75.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+26.6%** rocne, propad 22%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 6%)

### 2026-10-01 - [champion_12_mesicne] vix_pod_30: zamitnuto

* neotevirat, kdyz je VIX nad 30 (panika na trzich)
* kandidat: 2019-22: **+64.1%** rocne, propad 26%, 3.0 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: -
* sampion:  2019-22: **+75.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+26.6%** rocne, propad 22%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 6%)

### 2026-10-01 - [champion_12_mesicne] vix_pod_25: zamitnuto

* neotevirat, kdyz je VIX nad 25
* kandidat: 2019-22: **+52.5%** rocne, propad 26%, 2.6 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: -
* sampion:  2019-22: **+75.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+26.6%** rocne, propad 22%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 6%)

### 2026-10-01 - [champion_12_mesicne] vix_bez_skoku: zamitnuto

* neotevirat, kdyz VIX za 5 dni vzrostl o vic nez 5 bodu
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+75.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+26.6%** rocne, propad 22%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 6%)

### 2026-10-01 - [champion_12] stop_na_vstup_05: zamitnuto

* po pohybu 0.5 ATR ve smeru obchodu se stop posune na vstupni cenu
* kandidat: 2019-22: **+63.6%** rocne, propad 25%, 2.6 ziskovych/mesic (marze 20% / 20% / 10% / 6%); 2023-26: **+14.3%** rocne, propad 26%, 1.9 ziskovych/mesic (marze 15% / 15% / 8% / 6%)
* sampion:  2019-22: **+74.2%** rocne, propad 25%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+28.6%** rocne, propad 20%, 2.2 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] stop_na_vstup_06: zamitnuto

* po pohybu 0.6 ATR ve smeru obchodu se stop posune na vstupni cenu
* kandidat: 2019-22: **+71.1%** rocne, propad 22%, 2.9 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+24.1%** rocne, propad 27%, 2.0 ziskovych/mesic (marze 20% / 20% / 3% / 3%)
* sampion:  2019-22: **+74.2%** rocne, propad 25%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+28.6%** rocne, propad 20%, 2.2 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] stoji_5_dni: zamitnuto

* kdyz obchod po 5 obchodnich dnech neni v zisku, zavrit
* kandidat: 2019-22: **+28.9%** rocne, propad 18%, 1.0 ziskovych/mesic (marze 20% / 20% / 0% / 0%); 2023-26: **+23.8%** rocne, propad 18%, 1.9 ziskovych/mesic (marze 15% / 15% / 8% / 6%)
* sampion:  2019-22: **+74.2%** rocne, propad 25%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+28.6%** rocne, propad 20%, 2.2 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] stoji_10_dni: zamitnuto

* kdyz obchod po 10 obchodnich dnech neni v zisku, zavrit
* kandidat: 2019-22: **+70.3%** rocne, propad 25%, 3.1 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+28.2%** rocne, propad 23%, 2.1 ziskovych/mesic (marze 20% / 20% / 3% / 3%)
* sampion:  2019-22: **+74.2%** rocne, propad 25%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+28.6%** rocne, propad 20%, 2.2 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] potvrzeni_sazeb_cb: zamitnuto

* novy nejvyssi stupen: nejsilnejsi signal + sazby centralnich bank ukazuji stejnym smerem
* kandidat: 2019-22: **+54.5%** rocne, propad 21%, 3.3 ziskovych/mesic (marze 15% / 15% / 10% / 10% / 4%); 2023-26: **+16.1%** rocne, propad 32%, 2.2 ziskovych/mesic (marze 15% / 15% / 10% / 8% / 4%)
* sampion:  2019-22: **+74.2%** rocne, propad 25%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+28.6%** rocne, propad 20%, 2.2 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] cot_neprehustene: zamitnuto

* neobchodovat, kdyz jsou spekulanti (COT) presyceni ve smeru obchodu (rozdil z > 1)
* kandidat: 2019-22: **+38.2%** rocne, propad 22%, 2.2 ziskovych/mesic (marze 20% / 20% / 6% / 5%); 2023-26: **+15.9%** rocne, propad 31%, 1.8 ziskovych/mesic (marze 15% / 15% / 8% / 6%)
* sampion:  2019-22: **+74.2%** rocne, propad 25%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+28.6%** rocne, propad 20%, 2.2 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] trend_slabe_stupne: zamitnuto

* slabsi stupne jen ve smeru trendu (SMA200)
* kandidat: 2019-22: **+45.3%** rocne, propad 17%, 1.1 ziskovych/mesic (marze 20% / 20% / 0% / 0%); 2023-26: **+27.1%** rocne, propad 20%, 1.3 ziskovych/mesic (marze 20% / 20% / 6% / 6%)
* sampion:  2019-22: **+74.2%** rocne, propad 25%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+28.6%** rocne, propad 20%, 2.2 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] slabe_rsi3_i_r14: zamitnuto

* slabsi stupne berou i signaly RSI(3) < 15 a %R14 < 10
* kandidat: 2019-22: **+45.3%** rocne, propad 17%, 1.1 ziskovych/mesic (marze 20% / 20% / 0% / 0%); 2023-26: **+22.4%** rocne, propad 21%, 3.8 ziskovych/mesic (marze 20% / 20% / 2% / 2%)
* sampion:  2019-22: **+74.2%** rocne, propad 25%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+28.6%** rocne, propad 20%, 2.2 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12] druhy_stupen_rsi3: zamitnuto

* druhy stupen (sazby >= 0.25 bez carry) bere i RSI(3) < 15
* kandidat: 2019-22: **+67.5%** rocne, propad 25%, 3.4 ziskovych/mesic (marze 20% / 12% / 10% / 4%); 2023-26: **+18.4%** rocne, propad 32%, 2.3 ziskovych/mesic (marze 15% / 10% / 8% / 5%)
* sampion:  2019-22: **+74.2%** rocne, propad 25%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%); 2023-26: **+28.6%** rocne, propad 20%, 2.2 ziskovych/mesic (marze 20% / 20% / 3% / 3%)

### 2026-10-01 - [champion_12_mesicne] stop_na_vstup_05: zamitnuto

* po pohybu 0.5 ATR ve smeru obchodu se stop posune na vstupni cenu
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+75.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+26.6%** rocne, propad 22%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 6%)

### 2026-10-01 - [champion_12_mesicne] stop_na_vstup_06: zamitnuto

* po pohybu 0.6 ATR ve smeru obchodu se stop posune na vstupni cenu
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+75.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+26.6%** rocne, propad 22%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 6%)

### 2026-10-01 - [champion_12_mesicne] stoji_5_dni: zamitnuto

* kdyz obchod po 5 obchodnich dnech neni v zisku, zavrit
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+75.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+26.6%** rocne, propad 22%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 6%)

### 2026-10-01 - [champion_12_mesicne] stoji_10_dni: zamitnuto

* kdyz obchod po 10 obchodnich dnech neni v zisku, zavrit
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+75.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+26.6%** rocne, propad 22%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 6%)

### 2026-10-01 - [champion_12_mesicne] potvrzeni_sazeb_cb: zamitnuto

* novy nejvyssi stupen: nejsilnejsi signal + sazby centralnich bank ukazuji stejnym smerem
* kandidat: 2019-22: **+53.3%** rocne, propad 19%, 3.3 ziskovych/mesic (marze 15% / 15% / 10% / 6% / 6%); 2023-26: **+26.7%** rocne, propad 17%, 2.2 ziskovych/mesic (marze 15% / 15% / 10% / 6% / 6%)
* sampion:  2019-22: **+75.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+26.6%** rocne, propad 22%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 6%)

### 2026-10-01 - [champion_12_mesicne] cot_neprehustene: zamitnuto

* neobchodovat, kdyz jsou spekulanti (COT) presyceni ve smeru obchodu (rozdil z > 1)
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+75.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+26.6%** rocne, propad 22%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 6%)

### 2026-10-01 - [champion_12_mesicne] trend_slabe_stupne: zamitnuto

* slabsi stupne jen ve smeru trendu (SMA200)
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+75.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+26.6%** rocne, propad 22%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 6%)

### 2026-10-01 - [champion_12_mesicne] slabe_rsi3_i_r14: zamitnuto

* slabsi stupne berou i signaly RSI(3) < 15 a %R14 < 10
* kandidat: 2019-22: **+49.2%** rocne, propad 29%, 4.8 ziskovych/mesic (marze 20% / 20% / 4% / 4%); 2023-26: **+17.9%** rocne, propad 18%, 3.7 ziskovych/mesic (marze 12% / 12% / 3% / 3%)
* sampion:  2019-22: **+75.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+26.6%** rocne, propad 22%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 6%)

### 2026-10-01 - [champion_12_mesicne] druhy_stupen_rsi3: zamitnuto

* druhy stupen (sazby >= 0.25 bez carry) bere i RSI(3) < 15
* kandidat: 2019-22: **+74.9%** rocne, propad 42%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+18.7%** rocne, propad 13%, 2.3 ziskovych/mesic (marze 10% / 6% / 6% / 5%)
* sampion:  2019-22: **+75.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 6%); 2023-26: **+26.6%** rocne, propad 22%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 6%)

## 2026-10-02 - profil mesicne: sampion CH-009 (12 paru) + stop_4_atr + signal_i_rsi3 na datech do 2026-09-25 | AUD2026-08,CAD2026-08,CHF2026-08,CZK2026-08,EUR2026-08,GBP2026-08,HUF2026-08,JPY2026-08,MXN2026-08,NOK2026-08,NZD2026-08,PLN2026-07,SEK2026-08,USD2026-08,ZAR2026-08 | v2

2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12_mesicne] zpravy_cb_7_dni: zamitnuto

* neotevirat, kdyz centralni banka jedne z men rozhoduje do 7 dni (Fed, ECB, BoJ, BoE)
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12_mesicne] zpravy_cb_5_dni: zamitnuto

* neotevirat, kdyz centralni banka jedne z men rozhoduje do 5 dni
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12_mesicne] zpravy_cb_10_dni: zamitnuto

* neotevirat, kdyz centralni banka jedne z men rozhoduje do 10 dni
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12_mesicne] zpravy_cb_7_slabe: zamitnuto

* jen slabsi stupne: neotevirat 7 dni pred rozhodnutim centralni banky
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12_mesicne] zpravy_us_data: zamitnuto

* pary s USD: neotevirat v tydnu, kdy vysly NFP nebo CPI
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12_mesicne] zpravy_skok_075: zamitnuto

* neotevirat po zpravovem skoku (hodina za posledni 2 dny > 0.75 ATR)
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

## 2026-10-02 - profil max: sampion CH-009 (12 paru) + velikost_podle_volatility + signal_i_rsi3 na datech do 2026-09-25 | AUD2026-08,CAD2026-08,CHF2026-08,CZK2026-08,EUR2026-08,GBP2026-08,HUF2026-08,JPY2026-08,MXN2026-08,NOK2026-08,NZD2026-08,PLN2026-07,SEK2026-08,USD2026-08,ZAR2026-08 | v2

2019-22: **+71.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +107% / +43%; 2023-26: **+19.8%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +9% / +42%

### 2026-10-02 - [champion_12] zpravy_cb_7_dni: zamitnuto

* neotevirat, kdyz centralni banka jedne z men rozhoduje do 7 dni (Fed, ECB, BoJ, BoE)
* kandidat: 2019-22: **+53.6%** rocne, propad 26%, 1.4 ziskovych/mesic (marze 20% / 20% / 8% / 0%), po 2 letech +92% / +37%; 2023-26: **+20.9%** rocne, propad 26%, 1.7 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +13% / +37%
* sampion:  2019-22: **+71.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +107% / +43%; 2023-26: **+19.8%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +9% / +42%

### 2026-10-02 - [champion_12] zpravy_cb_5_dni: zamitnuto

* neotevirat, kdyz centralni banka jedne z men rozhoduje do 5 dni
* kandidat: 2019-22: **+43.3%** rocne, propad 21%, 1.0 ziskovych/mesic (marze 20% / 20% / 0% / 0%), po 2 letech +56% / +86%; 2023-26: **+23.7%** rocne, propad 25%, 1.9 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +41%
* sampion:  2019-22: **+71.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +107% / +43%; 2023-26: **+19.8%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +9% / +42%

### 2026-10-02 - [champion_12] zpravy_cb_10_dni: zamitnuto

* neotevirat, kdyz centralni banka jedne z men rozhoduje do 10 dni
* kandidat: 2019-22: **+53.6%** rocne, propad 26%, 1.4 ziskovych/mesic (marze 20% / 20% / 8% / 0%), po 2 letech +92% / +37%; 2023-26: **+20.9%** rocne, propad 26%, 1.7 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +13% / +37%
* sampion:  2019-22: **+71.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +107% / +43%; 2023-26: **+19.8%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +9% / +42%

### 2026-10-02 - [champion_12] zpravy_cb_7_slabe: zamitnuto

* jen slabsi stupne: neotevirat 7 dni pred rozhodnutim centralni banky
* kandidat: 2019-22: **+56.7%** rocne, propad 28%, 1.6 ziskovych/mesic (marze 20% / 20% / 10% / 0%), po 2 letech +108% / +32%; 2023-26: **+20.3%** rocne, propad 26%, 1.9 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +13% / +36%
* sampion:  2019-22: **+71.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +107% / +43%; 2023-26: **+19.8%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +9% / +42%

### 2026-10-02 - [champion_12] zpravy_us_data: zamitnuto

* pary s USD: neotevirat v tydnu, kdy vysly NFP nebo CPI
* kandidat: 2019-22: **+39.9%** rocne, propad 26%, 2.4 ziskovych/mesic (marze 20% / 20% / 8% / 5%), po 2 letech +54% / +28%; 2023-26: **+20.5%** rocne, propad 21%, 1.5 ziskovych/mesic (marze 15% / 15% / 6% / 6%), po 2 letech +37% / +2%
* sampion:  2019-22: **+71.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +107% / +43%; 2023-26: **+19.8%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +9% / +42%

### 2026-10-02 - [champion_12] zpravy_skok_075: zamitnuto

* neotevirat po zpravovem skoku (hodina za posledni 2 dny > 0.75 ATR)
* kandidat: 2019-22: **+41.7%** rocne, propad 21%, 1.2 ziskovych/mesic (marze 20% / 20% / 10% / 0%), po 2 letech +90% / +16%; 2023-26: **+17.1%** rocne, propad 37%, 1.7 ziskovych/mesic (marze 15% / 15% / 10% / 5%), po 2 letech +2% / +49%
* sampion:  2019-22: **+71.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +107% / +43%; 2023-26: **+19.8%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +9% / +42%

### 2026-10-02 - [champion_12_mesicne] zpravy_cb_7_polovina: zamitnuto

* 7 dni pred rozhodnutim centralni banky jedne z men jen polovicni pozice (obchodu stejne)
* kandidat: 2019-22: **+73.0%** rocne, propad 20%, 3.3 ziskovych/mesic (marze 20% / 20% / 5% / 5%), po 2 letech +82% / +68%; 2023-26: **+29.6%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 20% / 20% / 5% / 5%), po 2 letech +19% / +54%
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12_mesicne] zpravy_cb_7_polovina_slabe: zamitnuto

* jen slabsi stupne: 7 dni pred rozhodnutim centralni banky polovicni pozice
* kandidat: 2019-22: **+72.6%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +90% / +59%; 2023-26: **+20.1%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 4%), po 2 letech +13% / +36%
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12] zpravy_cb_7_polovina: zamitnuto

* 7 dni pred rozhodnutim centralni banky jedne z men jen polovicni pozice (obchodu stejne)
* kandidat: 2019-22: **+72.2%** rocne, propad 28%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%), po 2 letech +106% / +46%; 2023-26: **+20.1%** rocne, propad 25%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +11% / +40%
* sampion:  2019-22: **+71.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +107% / +43%; 2023-26: **+19.8%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +9% / +42%

### 2026-10-02 - [champion_12] zpravy_cb_7_polovina_slabe: zamitnuto

* jen slabsi stupne: 7 dni pred rozhodnutim centralni banky polovicni pozice
* kandidat: 2019-22: **+72.5%** rocne, propad 28%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%), po 2 letech +110% / +44%; 2023-26: **+20.1%** rocne, propad 25%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +11% / +39%
* sampion:  2019-22: **+71.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +107% / +43%; 2023-26: **+19.8%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +9% / +42%

### 2026-10-02 - [champion_12_mesicne] zpravy_po_rozhodnuti_vetsi: zamitnuto

* kdyz centralni banka jedne z men rozhodla v tydnu vstupu, pozice 1.5x vetsi
* kandidat: 2019-22: **+64.5%** rocne, propad 20%, 3.3 ziskovych/mesic (marze 15% / 15% / 6% / 5%), po 2 letech +78% / +54%; 2023-26: **+26.2%** rocne, propad 18%, 2.2 ziskovych/mesic (marze 12% / 12% / 5% / 5%), po 2 letech +19% / +43%
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12_mesicne] slabe_stupne_s_carry: zamitnuto

* slabsi stupne jen s kladnym urokovym rozdilem ve smeru obchodu (swap pro nas)
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12_mesicne] zpravy_pred_polovina_po_vetsi: zamitnuto

* pred rozhodnutim centralni banky polovicni pozice, po rozhodnuti 1.5x vetsi
* kandidat: 2019-22: **+60.4%** rocne, propad 17%, 3.3 ziskovych/mesic (marze 15% / 15% / 5% / 4%), po 2 letech +66% / +57%; 2023-26: **+27.4%** rocne, propad 21%, 2.2 ziskovych/mesic (marze 15% / 15% / 5% / 4%), po 2 letech +20% / +45%
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12] zpravy_po_rozhodnuti_vetsi: zamitnuto

* kdyz centralni banka jedne z men rozhodla v tydnu vstupu, pozice 1.5x vetsi
* kandidat: 2019-22: **+69.7%** rocne, propad 34%, 3.3 ziskovych/mesic (marze 20% / 20% / 4% / 4%), po 2 letech +98% / +48%; 2023-26: **+19.1%** rocne, propad 18%, 2.2 ziskovych/mesic (marze 10% / 10% / 4% / 4%), po 2 letech +13% / +33%
* sampion:  2019-22: **+71.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +107% / +43%; 2023-26: **+19.8%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +9% / +42%

### 2026-10-02 - [champion_12] slabe_stupne_s_carry: zamitnuto

* slabsi stupne jen s kladnym urokovym rozdilem ve smeru obchodu (swap pro nas)
* kandidat: 2019-22: **+54.2%** rocne, propad 28%, 2.0 ziskovych/mesic (marze 20% / 20% / 10% / 6%), po 2 letech +73% / +46%; 2023-26: **+19.8%** rocne, propad 17%, 1.4 ziskovych/mesic (marze 15% / 15% / 6% / 6%), po 2 letech +15% / +32%
* sampion:  2019-22: **+71.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +107% / +43%; 2023-26: **+19.8%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +9% / +42%

### 2026-10-02 - [champion_12] zpravy_pred_polovina_po_vetsi: zamitnuto

* pred rozhodnutim centralni banky polovicni pozice, po rozhodnuti 1.5x vetsi
* kandidat: 2019-22: **+74.3%** rocne, propad 39%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +108% / +48%; 2023-26: **+21.4%** rocne, propad 10%, 2.2 ziskovych/mesic (marze 12% / 12% / 2% / 2%), po 2 letech +16% / +33%
* sampion:  2019-22: **+71.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +107% / +43%; 2023-26: **+19.8%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +9% / +42%

### 2026-10-02 - [champion_12_mesicne] adaptivni_par_3m: zamitnuto

* par se obchoduje, jen kdyz pravidlu na nem vychazelo poslednich 3 mesice
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12_mesicne] adaptivni_par_6m: zamitnuto

* par se obchoduje, jen kdyz pravidlu na nem vychazelo poslednich 6 mesicu
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12_mesicne] adaptivni_par_12m: zamitnuto

* par se obchoduje, jen kdyz pravidlu na nem vychazelo poslednich 12 mesicu
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12] adaptivni_par_3m: zamitnuto

* par se obchoduje, jen kdyz pravidlu na nem vychazelo poslednich 3 mesice
* kandidat: 2019-22: **+62.2%** rocne, propad 25%, 3.2 ziskovych/mesic (marze 20% / 20% / 4% / 4%), po 2 letech +92% / +39%; 2023-26: **+15.6%** rocne, propad 26%, 2.0 ziskovych/mesic (marze 15% / 15% / 4% / 4%), po 2 letech +5% / +36%
* sampion:  2019-22: **+71.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +107% / +43%; 2023-26: **+19.8%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +9% / +42%

### 2026-10-02 - [champion_12] adaptivni_par_6m: zamitnuto

* par se obchoduje, jen kdyz pravidlu na nem vychazelo poslednich 6 mesicu
* kandidat: 2019-22: **+72.8%** rocne, propad 29%, 3.0 ziskovych/mesic (marze 20% / 20% / 8% / 5%), po 2 letech +120% / +38%; 2023-26: **+12.2%** rocne, propad 25%, 1.8 ziskovych/mesic (marze 15% / 15% / 4% / 4%), po 2 letech +2% / +32%
* sampion:  2019-22: **+71.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +107% / +43%; 2023-26: **+19.8%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +9% / +42%

### 2026-10-02 - [champion_12] adaptivni_par_12m: zamitnuto

* par se obchoduje, jen kdyz pravidlu na nem vychazelo poslednich 12 mesicu
* kandidat: 2019-22: **+20.4%** rocne, propad 22%, 0.6 ziskovych/mesic (marze 20% / 0% / 0% / 0%), po 2 letech +27% / +35%; 2023-26: **+4.7%** rocne, propad 26%, 1.5 ziskovych/mesic (marze 15% / 15% / 4% / 4%), po 2 letech -2% / +17%
* sampion:  2019-22: **+71.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +107% / +43%; 2023-26: **+19.8%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +9% / +42%

### 2026-10-02 - [champion_12_mesicne] riziko_proti_akciim_5d: zamitnuto

* rizikove meny (AUD, NZD, CAD proti JPY, CHF) kupovat jen po 5dennim poklesu S&P 500, prodavat jen po rustu
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12_mesicne] eurgbp_navrat_stupen: zamitnuto

* novy slaby stupen jen pro EUR/GBP: navrat po propadu RSI(2) < 5 bez filtru sazeb
* kandidat: 2019-22: **+43.4%** rocne, propad 27%, 7.4 ziskovych/mesic (marze 15% / 15% / 4% / 4% / 2%), po 2 letech +66% / +24%; 2023-26: **+16.9%** rocne, propad 17%, 2.2 ziskovych/mesic (marze 10% / 10% / 6% / 4% / 0%), po 2 letech +9% / +33%
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12_mesicne] zavrit_pred_cb_zisk: zamitnuto

* obchod v zisku zavrit pri zavreni dne pred rozhodnutim centralni banky jedne z men
* kandidat: 2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12_mesicne] zavrit_pred_cb_vzdy: zamitnuto

* kazdy obchod zavrit pri zavreni dne pred rozhodnutim centralni banky jedne z men
* kandidat: 2019-22: **+69.2%** rocne, propad 19%, 3.1 ziskovych/mesic (marze 20% / 20% / 8% / 5%), po 2 letech +63% / +79%; 2023-26: **+26.6%** rocne, propad 31%, 2.1 ziskovych/mesic (marze 20% / 20% / 8% / 5%), po 2 letech +22% / +38%
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12] riziko_proti_akciim_5d: zamitnuto

* rizikove meny (AUD, NZD, CAD proti JPY, CHF) kupovat jen po 5dennim poklesu S&P 500, prodavat jen po rustu
* kandidat: 2019-22: **+38.8%** rocne, propad 28%, 2.5 ziskovych/mesic (marze 20% / 20% / 6% / 6%), po 2 letech +75% / +11%; 2023-26: **+18.8%** rocne, propad 18%, 1.8 ziskovych/mesic (marze 12% / 12% / 5% / 5%), po 2 letech +6% / +46%
* sampion:  2019-22: **+71.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +107% / +43%; 2023-26: **+19.8%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +9% / +42%

### 2026-10-02 - [champion_12] eurgbp_navrat_stupen: zamitnuto

* novy slaby stupen jen pro EUR/GBP: navrat po propadu RSI(2) < 5 bez filtru sazeb
* kandidat: 2019-22: **+59.9%** rocne, propad 23%, 3.3 ziskovych/mesic (marze 15% / 15% / 10% / 4% / 0%), po 2 letech +92% / +35%; 2023-26: **+19.8%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4% / 0%), po 2 letech +9% / +42%
* sampion:  2019-22: **+71.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +107% / +43%; 2023-26: **+19.8%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +9% / +42%

### 2026-10-02 - [champion_12] zavrit_pred_cb_zisk: PRIJATO

* obchod v zisku zavrit pri zavreni dne pred rozhodnutim centralni banky jedne z men
* kandidat: 2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%
* sampion:  2019-22: **+71.1%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +107% / +43%; 2023-26: **+19.8%** rocne, propad 27%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +9% / +42%

### 2026-10-02 - [champion_12] zavrit_pred_cb_vzdy: zamitnuto

* kazdy obchod zavrit pri zavreni dne pred rozhodnutim centralni banky jedne z men
* kandidat: 2019-22: **+67.0%** rocne, propad 28%, 3.1 ziskovych/mesic (marze 20% / 20% / 10% / 5%), po 2 letech +79% / +58%; 2023-26: **+21.8%** rocne, propad 26%, 2.1 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +19% / +30%
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%

### 2026-10-02 - [champion_12_mesicne] fomc_doplnek: zamitnuto

* doplnek: v den rozhodnuti Fedu proti dolaru (7 paru s USD), od zavreni den predem do zavreni
* kandidat: 2019-22: **+54.4%** rocne, propad 20%, 3.3 ziskovych/mesic (marze 15% / 15% / 6% / 4% / 0%), po 2 letech +69% / +43%; 2023-26: **+16.9%** rocne, propad 17%, 2.2 ziskovych/mesic (marze 10% / 10% / 6% / 4% / 0%), po 2 letech +9% / +33%
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12_mesicne] velikost_podle_vix: zamitnuto

* velikost pozice 17 / VIX (vic pri klidu, mene pri strachu, 0.5-1.5x)
* kandidat: 2019-22: **+51.3%** rocne, propad 20%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 1%), po 2 letech +67% / +39%; 2023-26: **+18.9%** rocne, propad 23%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 3%), po 2 letech +10% / +38%
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12_mesicne] zavrit_long_usd_pred_fomc: zamitnuto

* obchod sazejici na dolar zavrit pri zavreni dne pred rozhodnutim Fedu
* kandidat: 2019-22: **+63.7%** rocne, propad 27%, 3.2 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +75% / +56%; 2023-26: **+14.5%** rocne, propad 19%, 2.1 ziskovych/mesic (marze 12% / 12% / 6% / 4%), po 2 letech +10% / +24%
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12_mesicne] zavrit_pred_cb_zisk_silne: zamitnuto

* jen silne stupne: obchod v zisku zavrit den pred rozhodnutim centralni banky
* kandidat: 2019-22: **+87.6%** rocne, propad 19%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +83%; 2023-26: **+40.8%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +26% / +76%
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12] fomc_doplnek: zamitnuto

* doplnek: v den rozhodnuti Fedu proti dolaru (7 paru s USD), od zavreni den predem do zavreni
* kandidat: 2019-22: **+66.6%** rocne, propad 23%, 3.3 ziskovych/mesic (marze 15% / 15% / 10% / 4% / 0%), po 2 letech +97% / +43%; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4% / 0%), po 2 letech +16% / +48%
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%

### 2026-10-02 - [champion_12] velikost_podle_vix: zamitnuto

* velikost pozice 17 / VIX (vic pri klidu, mene pri strachu, 0.5-1.5x)
* kandidat: 2019-22: **+50.7%** rocne, propad 11%, 3.3 ziskovych/mesic (marze 15% / 15% / 6% / 3%), po 2 letech +71% / +34%; 2023-26: **+18.3%** rocne, propad 33%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 3%), po 2 letech +10% / +35%
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%

### 2026-10-02 - [champion_12] zavrit_long_usd_pred_fomc: zamitnuto

* obchod sazejici na dolar zavrit pri zavreni dne pred rozhodnutim Fedu
* kandidat: 2019-22: **+62.5%** rocne, propad 26%, 3.2 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +89% / +41%; 2023-26: **+19.3%** rocne, propad 25%, 2.1 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +11% / +37%
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%

### 2026-10-02 - [champion_12] zavrit_pred_cb_zisk_silne: zamitnuto

* jen silne stupne: obchod v zisku zavrit den pred rozhodnutim centralni banky
* kandidat: 2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%

### 2026-10-02 - [champion_12_mesicne] zavrit_pred_cb_zisk_marze15: zamitnuto

* obchod v zisku zavrit den pred rozhodnutim centralni banky; marze nejvys 15 % na obchod
* kandidat: 2019-22: **+65.5%** rocne, propad 17%, 3.4 ziskovych/mesic (marze 15% / 15% / 6% / 5%), po 2 letech +75% / +60%; 2023-26: **+29.6%** rocne, propad 22%, 2.3 ziskovych/mesic (marze 15% / 15% / 6% / 5%), po 2 letech +18% / +55%
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12_mesicne] zavrit_pred_cb_zisk_marze12: zamitnuto

* obchod v zisku zavrit den pred rozhodnutim centralni banky; marze nejvys 12 % na obchod
* kandidat: 2019-22: **+52.3%** rocne, propad 15%, 3.4 ziskovych/mesic (marze 12% / 12% / 5% / 5%), po 2 letech +60% / +47%; 2023-26: **+24.4%** rocne, propad 18%, 2.3 ziskovych/mesic (marze 12% / 12% / 5% / 5%), po 2 letech +16% / +44%
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%

### 2026-10-02 - [champion_12] zavrit_pred_cb_zisk_marze15: zamitnuto

* obchod v zisku zavrit den pred rozhodnutim centralni banky; marze nejvys 15 % na obchod
* kandidat: 2019-22: **+66.6%** rocne, propad 23%, 3.3 ziskovych/mesic (marze 15% / 15% / 10% / 4%), po 2 letech +97% / +43%; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%

### 2026-10-02 - [champion_12] zavrit_pred_cb_zisk_marze12: zamitnuto

* obchod v zisku zavrit den pred rozhodnutim centralni banky; marze nejvys 12 % na obchod
* kandidat: 2019-22: **+56.3%** rocne, propad 20%, 3.3 ziskovych/mesic (marze 12% / 12% / 10% / 4%), po 2 letech +82% / +36%; 2023-26: **+15.5%** rocne, propad 41%, 2.2 ziskovych/mesic (marze 12% / 12% / 10% / 4%), po 2 letech +2% / +42%
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%

## 2026-10-02 - profil mesicne: sampion CH-009 (12 paru) + stop_4_atr + signal_i_rsi3 na datech do 2026-09-25 | AUD2026-08,CAD2026-08,CHF2026-08,CZK2026-08,EUR2026-08,GBP2026-08,HUF2026-08,JPY2026-08,MXN2026-08,NOK2026-08,NZD2026-08,PLN2026-07,SEK2026-08,USD2026-08,ZAR2026-08 | v3

2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%, vynos/propad 2.69; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%, vynos/propad 1.09

### 2026-10-02 - [champion_12_mesicne] v3_zavrit_pred_cb_zisk: PRIJATO

* obchod v zisku zavrit den pred rozhodnutim centralni banky (znovu, brana v3)
* kandidat: 2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43
* sampion:  2019-22: **+72.8%** rocne, propad 27%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +92% / +58%, vynos/propad 2.69; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 12% / 12% / 6% / 5%), po 2 letech +12% / +39%, vynos/propad 1.09

### 2026-10-02 - [champion_12_mesicne] v3_zavrit_pred_cb_zisk_marze15: zamitnuto

* totez s marzi nejvys 15 % na obchod (brana v3)
* kandidat: 2019-22: **+65.5%** rocne, propad 17%, 3.4 ziskovych/mesic (marze 15% / 15% / 6% / 5%), po 2 letech +75% / +60%, vynos/propad 3.84; 2023-26: **+29.6%** rocne, propad 22%, 2.3 ziskovych/mesic (marze 15% / 15% / 6% / 5%), po 2 letech +18% / +55%, vynos/propad 1.33
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] v3_polovina_pred_cb: zamitnuto

* 7 dni pred rozhodnutim centralni banky polovicni pozice (znovu, brana v3)
* kandidat: 2019-22: **+78.4%** rocne, propad 20%, 3.4 ziskovych/mesic (marze 20% / 20% / 5% / 5%), po 2 letech +84% / +77%, vynos/propad 4.00; 2023-26: **+32.8%** rocne, propad 27%, 2.3 ziskovych/mesic (marze 20% / 20% / 5% / 5%), po 2 letech +22% / +59%, vynos/propad 1.23
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] tri_cile: zamitnuto

* pozice na 3 casti s cili 0.75 / 1.0 / 1.5 ATR (vybrat zisk postupne)
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] tri_cile_nechat_bezet: zamitnuto

* pozice na 3 casti s cili 0.75 / 1.5 / 3.0 ATR (cast nechat bezet)
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] padajici_nuz_20: zamitnuto

* nekupovat zaviraci cenu, ktera je nejnizsi za 20 dni (neprodavat nejvyssi)
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] silny_stupen_denne: zamitnuto

* nejsilnejsi stupen se vyhodnocuje kazdy den, ne jen v patek (vic obchodu)
* kandidat: 2019-22: **+42.0%** rocne, propad 27%, 4.1 ziskovych/mesic (marze 8% / 8% / 4% / 4%), po 2 letech +40% / +46%, vynos/propad 1.57; 2023-26: **+15.2%** rocne, propad 14%, 3.1 ziskovych/mesic (marze 6% / 6% / 4% / 3%), po 2 letech +14% / +19%, vynos/propad 1.09
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] silne_stupne_denne: zamitnuto

* oba silne stupne se vyhodnocuji kazdy den
* kandidat: 2019-22: **+28.4%** rocne, propad 26%, 4.4 ziskovych/mesic (marze 6% / 4% / 4% / 4%), po 2 letech +24% / +34%, vynos/propad 1.09; 2023-26: **+14.1%** rocne, propad 11%, 3.7 ziskovych/mesic (marze 4% / 4% / 4% / 4%), po 2 letech +14% / +16%, vynos/propad 1.29
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

## 2026-10-02 - profil max: sampion CH-009 (12 paru) + velikost_podle_volatility + signal_i_rsi3 + zavrit_pred_cb_zisk na datech do 2026-09-25 | AUD2026-08,CAD2026-08,CHF2026-08,CZK2026-08,EUR2026-08,GBP2026-08,HUF2026-08,JPY2026-08,MXN2026-08,NOK2026-08,NZD2026-08,PLN2026-07,SEK2026-08,USD2026-08,ZAR2026-08 | v3

2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] v3_zavrit_pred_cb_zisk: zamitnuto

* obchod v zisku zavrit den pred rozhodnutim centralni banky (znovu, brana v3)
* kandidat: 2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] v3_zavrit_pred_cb_zisk_marze15: zamitnuto

* totez s marzi nejvys 15 % na obchod (brana v3)
* kandidat: 2019-22: **+66.6%** rocne, propad 23%, 3.3 ziskovych/mesic (marze 15% / 15% / 10% / 4%), po 2 letech +97% / +43%, vynos/propad 2.91; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] v3_polovina_pred_cb: zamitnuto

* 7 dni pred rozhodnutim centralni banky polovicni pozice (znovu, brana v3)
* kandidat: 2019-22: **+76.0%** rocne, propad 28%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%), po 2 letech +109% / +51%, vynos/propad 2.74; 2023-26: **+23.3%** rocne, propad 26%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +14% / +42%, vynos/propad 0.91
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] tri_cile: zamitnuto

* pozice na 3 casti s cili 0.75 / 1.0 / 1.5 ATR (vybrat zisk postupne)
* kandidat: 2019-22: **+79.8%** rocne, propad 26%, 2.8 ziskovych/mesic (marze 20% / 20% / 8% / 5%), po 2 letech +87% / +72%, vynos/propad 3.06; 2023-26: **+24.0%** rocne, propad 30%, 0.9 ziskovych/mesic (marze 20% / 20% / 0% / 0%), po 2 letech +10% / +53%, vynos/propad 0.79
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] tri_cile_nechat_bezet: zamitnuto

* pozice na 3 casti s cili 0.75 / 1.5 / 3.0 ATR (cast nechat bezet)
* kandidat: 2019-22: **+55.0%** rocne, propad 20%, 0.9 ziskovych/mesic (marze 20% / 20% / 0% / 0%), po 2 letech +92% / +69%, vynos/propad 2.78; 2023-26: **+15.1%** rocne, propad 32%, 0.7 ziskovych/mesic (marze 20% / 20% / 0% / 0%), po 2 letech -1% / +46%, vynos/propad 0.47
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] padajici_nuz_20: zamitnuto

* nekupovat zaviraci cenu, ktera je nejnizsi za 20 dni (neprodavat nejvyssi)
* kandidat: 2019-22: **+20.0%** rocne, propad 7%, 0.4 ziskovych/mesic (marze 20% / 20% / 0% / 0%), po 2 letech +19% / +77%, vynos/propad 3.00; 2023-26: **+15.9%** rocne, propad 17%, 0.9 ziskovych/mesic (marze 20% / 20% / 8% / 8%), po 2 letech +15% / +21%, vynos/propad 0.93
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] silny_stupen_denne: zamitnuto

* nejsilnejsi stupen se vyhodnocuje kazdy den, ne jen v patek (vic obchodu)
* kandidat: 2019-22: **+41.5%** rocne, propad 20%, 4.2 ziskovych/mesic (marze 8% / 8% / 4% / 3%), po 2 letech +43% / +42%, vynos/propad 2.09; 2023-26: **+14.6%** rocne, propad 17%, 3.1 ziskovych/mesic (marze 8% / 8% / 4% / 3%), po 2 letech +9% / +26%, vynos/propad 0.86
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] silne_stupne_denne: zamitnuto

* oba silne stupne se vyhodnocuji kazdy den
* kandidat: 2019-22: **+32.1%** rocne, propad 23%, 4.6 ziskovych/mesic (marze 8% / 3% / 3% / 3%), po 2 letech +25% / +41%, vynos/propad 1.37; 2023-26: **+13.6%** rocne, propad 15%, 3.7 ziskovych/mesic (marze 6% / 4% / 4% / 4%), po 2 letech +11% / +20%, vynos/propad 0.88
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12_mesicne] zavrit_pred_us_data_zisk: zamitnuto

* pary s USD: obchod v zisku zavrit den pred zpravou NFP nebo CPI
* kandidat: 2019-22: **+88.3%** rocne, propad 21%, 3.4 ziskovych/mesic (marze 20% / 20% / 8% / 5%), po 2 letech +98% / +83%, vynos/propad 4.27; 2023-26: **+37.1%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +23% / +69%, vynos/propad 1.34
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] zavrit_v_zisku_patek: zamitnuto

* obchod v zisku zavrit v patek pri zavreni (riziko vikendove mezery)
* kandidat: 2019-22: **+79.2%** rocne, propad 20%, 3.3 ziskovych/mesic (marze 20% / 20% / 5% / 5%), po 2 letech +87% / +75%, vynos/propad 4.04; 2023-26: **+36.6%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +23% / +68%, vynos/propad 1.32
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12] zavrit_pred_us_data_zisk: zamitnuto

* pary s USD: obchod v zisku zavrit den pred zpravou NFP nebo CPI
* kandidat: 2019-22: **+78.2%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +106% / +57%, vynos/propad 3.00; 2023-26: **+24.3%** rocne, propad 27%, 2.3 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +44%, vynos/propad 0.90
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] zavrit_v_zisku_patek: zamitnuto

* obchod v zisku zavrit v patek pri zavreni (riziko vikendove mezery)
* kandidat: 2019-22: **+74.7%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +108% / +49%, vynos/propad 2.87; 2023-26: **+23.7%** rocne, propad 29%, 2.3 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +15% / +43%, vynos/propad 0.83
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12_mesicne] zavrit_pred_cb_zisk_i_snb_rba: zamitnuto

* obchod v zisku zavrit den pred rozhodnutim i SNB (CHF) a RBA (AUD)
* kandidat: 2019-22: **+84.5%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +94% / +79%, vynos/propad 4.35; 2023-26: **+38.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +23% / +75%, vynos/propad 1.40
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12] zavrit_pred_cb_zisk_i_snb_rba: zamitnuto

* obchod v zisku zavrit den pred rozhodnutim i SNB (CHF) a RBA (AUD)
* kandidat: 2019-22: **+78.2%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +111% / +53%, vynos/propad 3.00; 2023-26: **+25.4%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +15% / +48%, vynos/propad 0.92
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12_mesicne] dokup_15_atr: zamitnuto

* dokoupit stejnou pozici, kdyz cena jde o dalsich 1.5 ATR proti (lepsi prumerna cena), cil dokupu 0.75 ATR, stop stejny
* kandidat: 2019-22: **+85.6%** rocne, propad 30%, 4.0 ziskovych/mesic (marze 20% / 20% / 5% / 3%), po 2 letech +96% / +79%, vynos/propad 2.90; 2023-26: **+38.4%** rocne, propad 27%, 3.9 ziskovych/mesic (marze 12% / 12% / 4% / 3%), po 2 letech +20% / +80%, vynos/propad 1.41
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] dokup_2_atr_silne: zamitnuto

* jen silne stupne: dokoupit o 2 ATR niz, cil dokupu 0.75 ATR, stop stejny
* kandidat: 2019-22: **+86.6%** rocne, propad 28%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +81%, vynos/propad 3.08; 2023-26: **+26.2%** rocne, propad 19%, 2.4 ziskovych/mesic (marze 12% / 12% / 5% / 5%), po 2 letech +18% / +46%, vynos/propad 1.40
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] potvrzeni_obratu_3d: zamitnuto

* vstoupit az pri prvnim zavreni ve smeru obchodu (do 3 dni po signalu), ne do padajici ceny
* kandidat: 2019-22: -; 2023-26: **+6.4%** rocne, propad 9%, 2.3 ziskovych/mesic (marze 6% / 5% / 1% / 1%), po 2 letech +4% / +11%, vynos/propad 0.72
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] jedna_sazka_na_menu: zamitnuto

* vic signalu stejneho dne na stejnou menu = jedna sazka: velikost deleno odmocninou poctu
* kandidat: 2019-22: **+62.0%** rocne, propad 16%, 3.4 ziskovych/mesic (marze 20% / 20% / 8% / 6%), po 2 letech +69% / +58%, vynos/propad 3.94; 2023-26: **+32.8%** rocne, propad 21%, 2.3 ziskovych/mesic (marze 20% / 20% / 8% / 6%), po 2 letech +24% / +53%, vynos/propad 1.55
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] stupen_sazby_04: zamitnuto

* novy nejsilnejsi stupen: zmena sazeb >= 0.40 p.b. (99 % vyher), nejslabsi stupen (sazby >= 0) pryc
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12] dokup_15_atr: zamitnuto

* dokoupit stejnou pozici, kdyz cena jde o dalsich 1.5 ATR proti (lepsi prumerna cena), cil dokupu 0.75 ATR, stop stejny
* kandidat: 2019-22: **+39.5%** rocne, propad 53%, 1.2 ziskovych/mesic (marze 20% / 20% / 0% / 0%), po 2 letech +97% / +15%, vynos/propad 0.75; 2023-26: **+15.6%** rocne, propad 15%, 3.5 ziskovych/mesic (marze 6% / 6% / 1% / 1%), po 2 letech +12% / +24%, vynos/propad 1.05
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] dokup_2_atr_silne: zamitnuto

* jen silne stupne: dokoupit o 2 ATR niz, cil dokupu 0.75 ATR, stop stejny
* kandidat: 2019-22: **+73.4%** rocne, propad 44%, 3.4 ziskovych/mesic (marze 20% / 20% / 10% / 4%), po 2 letech +122% / +37%, vynos/propad 1.66; 2023-26: **+8.0%** rocne, propad 22%, 2.3 ziskovych/mesic (marze 6% / 6% / 5% / 4%), po 2 letech +6% / +13%, vynos/propad 0.37
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] potvrzeni_obratu_3d: zamitnuto

* vstoupit az pri prvnim zavreni ve smeru obchodu (do 3 dni po signalu), ne do padajici ceny
* kandidat: 2019-22: **+15.3%** rocne, propad 25%, 0.7 ziskovych/mesic (marze 15% / 0% / 0% / 0%), po 2 letech +22% / +24%, vynos/propad 0.62; 2023-26: **+6.4%** rocne, propad 13%, 0.6 ziskovych/mesic (marze 12% / 0% / 0% / 0%), po 2 letech +4% / +17%, vynos/propad 0.48
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] jedna_sazka_na_menu: zamitnuto

* vic signalu stejneho dne na stejnou menu = jedna sazka: velikost deleno odmocninou poctu
* kandidat: 2019-22: **+62.5%** rocne, propad 16%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 6%), po 2 letech +82% / +47%, vynos/propad 3.93; 2023-26: **+29.6%** rocne, propad 25%, 2.2 ziskovych/mesic (marze 20% / 20% / 8% / 6%), po 2 letech +26% / +41%, vynos/propad 1.19
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] stupen_sazby_04: zamitnuto

* novy nejsilnejsi stupen: zmena sazeb >= 0.40 p.b. (99 % vyher), nejslabsi stupen (sazby >= 0) pryc
* kandidat: 2019-22: **+45.2%** rocne, propad 21%, 1.0 ziskovych/mesic (marze 20% / 20% / 0% / 0%), po 2 letech +62% / +83%, vynos/propad 2.12; 2023-26: **+21.5%** rocne, propad 27%, 1.8 ziskovych/mesic (marze 15% / 15% / 10% / 6%), po 2 letech +10% / +46%, vynos/propad 0.80
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12_mesicne] cil_06_atr: zamitnuto

* cil 0.6 ATR misto 0.75 (rychlejsi mensi zisky, casteji)
* kandidat: 2019-22: **+67.8%** rocne, propad 21%, 3.0 ziskovych/mesic (marze 20% / 20% / 8% / 6%), po 2 letech +77% / +62%, vynos/propad 3.24; 2023-26: **+33.5%** rocne, propad 20%, 2.0 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +31% / +44%, vynos/propad 1.68
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] cil_05_atr: zamitnuto

* cil 0.5 ATR misto 0.75
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] stop_5_atr: zamitnuto

* stop 5 ATR misto 4
* kandidat: 2019-22: **+81.8%** rocne, propad 23%, 3.4 ziskovych/mesic (marze 20% / 20% / 4% / 4%), po 2 letech +89% / +79%, vynos/propad 3.51; 2023-26: **+31.3%** rocne, propad 21%, 2.3 ziskovych/mesic (marze 15% / 15% / 5% / 4%), po 2 letech +20% / +58%, vynos/propad 1.49
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] drzeni_30_dni: zamitnuto

* nejdele 30 obchodnich dni misto 20
* kandidat: 2019-22: **+85.9%** rocne, propad 24%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%), po 2 letech +101% / +76%, vynos/propad 3.55; 2023-26: **+31.8%** rocne, propad 38%, 2.2 ziskovych/mesic (marze 20% / 20% / 6% / 4%), po 2 letech +20% / +59%, vynos/propad 0.84
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] cil_40_procent_poklesu: zamitnuto

* cil = 40 % poklesu za 5 dni (0.5-1.5 ATR): po hlubsim propadu vetsi odraz
* kandidat: 2019-22: **+49.4%** rocne, propad 43%, 2.9 ziskovych/mesic (marze 20% / 12% / 4% / 3%), po 2 letech +27% / +79%, vynos/propad 1.15; 2023-26: **+32.6%** rocne, propad 16%, 2.0 ziskovych/mesic (marze 20% / 3% / 1% / 1%), po 2 letech +31% / +41%, vynos/propad 2.02
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] ctvrtek_i_patek_silny: zamitnuto

* nejsilnejsi stupen se vyhodnocuje ve ctvrtek i v patek (vic obchodu)
* kandidat: 2019-22: **+73.4%** rocne, propad 53%, 3.5 ziskovych/mesic (marze 20% / 20% / 8% / 6%), po 2 letech +130% / +32%, vynos/propad 1.39; 2023-26: **+13.0%** rocne, propad 13%, 2.5 ziskovych/mesic (marze 6% / 6% / 5% / 5%), po 2 letech +9% / +22%, vynos/propad 0.96
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] ctvrtek_i_patek_silne: zamitnuto

* oba silne stupne se vyhodnocuji ve ctvrtek i v patek
* kandidat: 2019-22: **+59.2%** rocne, propad 53%, 3.6 ziskovych/mesic (marze 20% / 20% / 8% / 6%), po 2 letech +94% / +32%, vynos/propad 1.12; 2023-26: **+13.4%** rocne, propad 13%, 2.6 ziskovych/mesic (marze 6% / 6% / 5% / 5%), po 2 letech +9% / +22%, vynos/propad 1.00
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12] cil_06_atr: zamitnuto

* cil 0.6 ATR misto 0.75 (rychlejsi mensi zisky, casteji)
* kandidat: 2019-22: **+56.6%** rocne, propad 24%, 2.9 ziskovych/mesic (marze 20% / 20% / 6% / 6%), po 2 letech +78% / +40%, vynos/propad 2.32; 2023-26: **+17.0%** rocne, propad 19%, 2.0 ziskovych/mesic (marze 15% / 15% / 6% / 6%), po 2 letech +17% / +20%, vynos/propad 0.88
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] cil_05_atr: zamitnuto

* cil 0.5 ATR misto 0.75
* kandidat: 2019-22: **+33.1%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 20% / 20% / 10% / 6%), po 2 letech +46% / +23%, vynos/propad 1.19; 2023-26: **+11.7%** rocne, propad 22%, 1.6 ziskovych/mesic (marze 15% / 15% / 6% / 6%), po 2 letech +12% / +13%, vynos/propad 0.54
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] stop_5_atr: zamitnuto

* stop 5 ATR misto 4
* kandidat: 2019-22: **+49.0%** rocne, propad 18%, 3.4 ziskovych/mesic (marze 20% / 20% / 5% / 5%), po 2 letech +59% / +41%, vynos/propad 2.72; 2023-26: **+30.3%** rocne, propad 15%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +21% / +51%, vynos/propad 2.09
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] drzeni_30_dni: zamitnuto

* nejdele 30 obchodnich dni misto 20
* kandidat: 2019-22: **+81.0%** rocne, propad 28%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%), po 2 letech +114% / +56%, vynos/propad 2.92; 2023-26: **+21.3%** rocne, propad 31%, 2.1 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +15% / +37%, vynos/propad 0.68
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] cil_40_procent_poklesu: zamitnuto

* cil = 40 % poklesu za 5 dni (0.5-1.5 ATR): po hlubsim propadu vetsi odraz
* kandidat: 2019-22: **+30.5%** rocne, propad 21%, 0.7 ziskovych/mesic (marze 20% / 0% / 0% / 0%), po 2 letech +33% / +68%, vynos/propad 1.43; 2023-26: **+19.8%** rocne, propad 17%, 2.0 ziskovych/mesic (marze 15% / 5% / 4% / 3%), po 2 letech +19% / +24%, vynos/propad 1.13
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] ctvrtek_i_patek_silny: zamitnuto

* nejsilnejsi stupen se vyhodnocuje ve ctvrtek i v patek (vic obchodu)
* kandidat: 2019-22: **+60.0%** rocne, propad 36%, 3.5 ziskovych/mesic (marze 15% / 15% / 6% / 5%), po 2 letech +102% / +28%, vynos/propad 1.67; 2023-26: **+8.1%** rocne, propad 26%, 2.5 ziskovych/mesic (marze 6% / 6% / 6% / 5%), po 2 letech +2% / +20%, vynos/propad 0.32
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] ctvrtek_i_patek_silne: zamitnuto

* oba silne stupne se vyhodnocuji ve ctvrtek i v patek
* kandidat: 2019-22: **+51.1%** rocne, propad 36%, 3.6 ziskovych/mesic (marze 15% / 15% / 6% / 5%), po 2 letech +80% / +28%, vynos/propad 1.43; 2023-26: **+8.8%** rocne, propad 26%, 2.6 ziskovych/mesic (marze 6% / 6% / 6% / 5%), po 2 letech +2% / +21%, vynos/propad 0.35
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12_mesicne] pozdni_cil_5d_035: zamitnuto

* po 5 dnech bez cile se cil snizi na 0.35 ATR
* kandidat: 2019-22: **+78.6%** rocne, propad 20%, 3.4 ziskovych/mesic (marze 20% / 20% / 5% / 5%), po 2 letech +84% / +77%, vynos/propad 4.01; 2023-26: **+36.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +23% / +67%, vynos/propad 1.32
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] pozdni_cil_10d_025: zamitnuto

* po 10 dnech bez cile se cil snizi na 0.25 ATR
* kandidat: 2019-22: **+82.2%** rocne, propad 20%, 3.3 ziskovych/mesic (marze 20% / 20% / 5% / 5%), po 2 letech +83% / +85%, vynos/propad 4.19; 2023-26: **+42.5%** rocne, propad 28%, 2.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +33% / +66%, vynos/propad 1.54
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] pozdni_cil_7d_01: zamitnuto

* po 7 dnech bez cile vystoupit pri prvnim malem zisku (0.1 ATR)
* kandidat: 2019-22: **+78.7%** rocne, propad 20%, 3.3 ziskovych/mesic (marze 20% / 20% / 5% / 5%), po 2 letech +78% / +83%, vynos/propad 4.02; 2023-26: **+37.6%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +28% / +61%, vynos/propad 1.36
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12] pozdni_cil_5d_035: zamitnuto

* po 5 dnech bez cile se cil snizi na 0.35 ATR
* kandidat: 2019-22: **+67.0%** rocne, propad 23%, 3.4 ziskovych/mesic (marze 20% / 20% / 4% / 4%), po 2 letech +88% / +50%, vynos/propad 2.91; 2023-26: **+21.4%** rocne, propad 29%, 2.3 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +15% / +37%, vynos/propad 0.73
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] pozdni_cil_10d_025: zamitnuto

* po 10 dnech bez cile se cil snizi na 0.25 ATR
* kandidat: 2019-22: **+78.3%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +102% / +60%, vynos/propad 3.00; 2023-26: **+27.3%** rocne, propad 28%, 2.4 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +22% / +42%, vynos/propad 0.98
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] pozdni_cil_7d_01: zamitnuto

* po 7 dnech bez cile vystoupit pri prvnim malem zisku (0.1 ATR)
* kandidat: 2019-22: **+67.4%** rocne, propad 23%, 3.3 ziskovych/mesic (marze 20% / 20% / 4% / 4%), po 2 letech +82% / +56%, vynos/propad 2.97; 2023-26: **+21.5%** rocne, propad 29%, 2.3 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +17% / +33%, vynos/propad 0.74
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12_mesicne] silny_cil_1_atr: zamitnuto

* nejsilnejsi stupen: cil 1.0 ATR misto 0.75
* kandidat: 2019-22: **+108.8%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +108% / +115%, vynos/propad 5.58; 2023-26: **+32.0%** rocne, propad 32%, 2.2 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +7% / +90%, vynos/propad 1.01
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] silne_cil_1_atr: zamitnuto

* oba silne stupne: cil 1.0 ATR
* kandidat: 2019-22: **+79.9%** rocne, propad 31%, 3.3 ziskovych/mesic (marze 20% / 15% / 6% / 5%), po 2 letech +54% / +115%, vynos/propad 2.62; 2023-26: **+30.8%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 20% / 8% / 6% / 5%), po 2 letech +11% / +75%, vynos/propad 1.08
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] silny_dve_casti: zamitnuto

* nejsilnejsi stupen: pulka pozice s cilem 0.75 ATR, pulka 1.5 ATR
* kandidat: 2019-22: **+100.4%** rocne, propad 16%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +113% / +93%, vynos/propad 6.26; 2023-26: **+30.2%** rocne, propad 28%, 2.1 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +9% / +76%, vynos/propad 1.09
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] silny_i_pruraz: zamitnuto

* nejsilnejsi stupen bere i pruraz 20denniho maxima ve smeru sazeb (Donchian 20)
* kandidat: 2019-22: **+105.2%** rocne, propad 25%, 3.6 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +103% / +109%, vynos/propad 4.28; 2023-26: **+38.1%** rocne, propad 22%, 2.6 ziskovych/mesic (marze 15% / 15% / 6% / 5%), po 2 letech +38% / +45%, vynos/propad 1.71
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] silny_i_3_dny: zamitnuto

* nejsilnejsi stupen bere i 3 dny poklesu za sebou
* kandidat: 2019-22: **+73.8%** rocne, propad 46%, 3.6 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +84% / +69%, vynos/propad 1.60; 2023-26: **+17.9%** rocne, propad 12%, 2.6 ziskovych/mesic (marze 6% / 6% / 5% / 4%), po 2 letech +18% / +21%, vynos/propad 1.45
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12] silny_cil_1_atr: zamitnuto

* nejsilnejsi stupen: cil 1.0 ATR misto 0.75
* kandidat: 2019-22: **+102.6%** rocne, propad 30%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%), po 2 letech +136% / +77%, vynos/propad 3.40; 2023-26: **+23.2%** rocne, propad 21%, 2.2 ziskovych/mesic (marze 15% / 15% / 4% / 4%), po 2 letech +8% / +56%, vynos/propad 1.09
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] silne_cil_1_atr: zamitnuto

* oba silne stupne: cil 1.0 ATR
* kandidat: 2019-22: **+74.5%** rocne, propad 29%, 3.3 ziskovych/mesic (marze 20% / 15% / 8% / 4%), po 2 letech +75% / +77%, vynos/propad 2.61; 2023-26: **+21.3%** rocne, propad 31%, 2.2 ziskovych/mesic (marze 15% / 12% / 4% / 4%), po 2 letech +1% / +65%, vynos/propad 0.69
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] silny_dve_casti: zamitnuto

* nejsilnejsi stupen: pulka pozice s cilem 0.75 ATR, pulka 1.5 ATR
* kandidat: 2019-22: **+97.8%** rocne, propad 28%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 4%), po 2 letech +143% / +65%, vynos/propad 3.53; 2023-26: **+17.5%** rocne, propad 26%, 2.1 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +7% / +39%, vynos/propad 0.66
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] silny_i_pruraz: zamitnuto

* nejsilnejsi stupen bere i pruraz 20denniho maxima ve smeru sazeb (Donchian 20)
* kandidat: 2019-22: **+93.7%** rocne, propad 21%, 3.6 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +122% / +72%, vynos/propad 4.40; 2023-26: **+25.9%** rocne, propad 42%, 2.6 ziskovych/mesic (marze 15% / 15% / 10% / 4%), po 2 letech +21% / +39%, vynos/propad 0.62
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] silny_i_3_dny: zamitnuto

* nejsilnejsi stupen bere i 3 dny poklesu za sebou
* kandidat: 2019-22: **+59.3%** rocne, propad 52%, 3.6 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +92% / +34%, vynos/propad 1.13; 2023-26: **+14.8%** rocne, propad 20%, 2.6 ziskovych/mesic (marze 6% / 6% / 5% / 4%), po 2 letech +12% / +21%, vynos/propad 0.73
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12_mesicne] silny_trend: zamitnuto

* nejsilnejsi stupen jako trendovy obchodnik: propad i pruraz, pulka cil 0.75 ATR, pulka 1.5 ATR
* kandidat: 2019-22: **+104.9%** rocne, propad 26%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +106% / +101%, vynos/propad 4.08; 2023-26: **+22.5%** rocne, propad 27%, 2.5 ziskovych/mesic (marze 15% / 15% / 6% / 5%), po 2 letech +21% / +29%, vynos/propad 0.84
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12] silny_trend: zamitnuto

* nejsilnejsi stupen jako trendovy obchodnik: propad i pruraz, pulka cil 0.75 ATR, pulka 1.5 ATR
* kandidat: 2019-22: **+99.5%** rocne, propad 22%, 3.4 ziskovych/mesic (marze 20% / 20% / 10% / 4%), po 2 letech +142% / +69%, vynos/propad 4.45; 2023-26: **+23.2%** rocne, propad 39%, 2.4 ziskovych/mesic (marze 20% / 20% / 6% / 4%), po 2 letech +27% / +21%, vynos/propad 0.59
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12_mesicne] sazby_6m_potvrzeni: zamitnuto

* vsechny stupne: i zmena rozdilu sazeb za 6 mesicu ukazuje stejnym smerem
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] sazby_6m_potvrzeni_slabe: zamitnuto

* slabsi stupne: i zmena rozdilu sazeb za 6 mesicu ukazuje stejnym smerem
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] sazby_12m_potvrzeni_slabe: zamitnuto

* slabsi stupne: i zmena rozdilu sazeb za 12 mesicu ukazuje stejnym smerem
* kandidat: 2019-22: -; 2023-26: -
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] sazby_okno_6m: zamitnuto

* zmena rozdilu sazeb se meri za 6 mesicu misto 3 (prahy stejne)
* kandidat: 2019-22: **+15.3%** rocne, propad 18%, 3.3 ziskovych/mesic (marze 8% / 1% / 1% / 1%), po 2 letech +13% / +18%, vynos/propad 0.84; 2023-26: **+6.7%** rocne, propad 11%, 1.9 ziskovych/mesic (marze 6% / 3% / 2% / 2%), po 2 letech +4% / +13%, vynos/propad 0.63
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12] sazby_6m_potvrzeni: zamitnuto

* vsechny stupne: i zmena rozdilu sazeb za 6 mesicu ukazuje stejnym smerem
* kandidat: 2019-22: **+72.3%** rocne, propad 28%, 2.6 ziskovych/mesic (marze 20% / 20% / 10% / 4%), po 2 letech +107% / +45%, vynos/propad 2.61; 2023-26: **+16.9%** rocne, propad 27%, 1.7 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +7% / +37%, vynos/propad 0.62
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] sazby_6m_potvrzeni_slabe: zamitnuto

* slabsi stupne: i zmena rozdilu sazeb za 6 mesicu ukazuje stejnym smerem
* kandidat: 2019-22: **+74.1%** rocne, propad 28%, 2.7 ziskovych/mesic (marze 20% / 20% / 10% / 4%), po 2 letech +107% / +48%, vynos/propad 2.67; 2023-26: **+21.0%** rocne, propad 27%, 1.8 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +10% / +44%, vynos/propad 0.76
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] sazby_12m_potvrzeni_slabe: zamitnuto

* slabsi stupne: i zmena rozdilu sazeb za 12 mesicu ukazuje stejnym smerem
* kandidat: 2019-22: **+62.7%** rocne, propad 24%, 2.4 ziskovych/mesic (marze 20% / 20% / 5% / 5%), po 2 letech +85% / +45%, vynos/propad 2.66; 2023-26: **+26.1%** rocne, propad 18%, 1.6 ziskovych/mesic (marze 15% / 15% / 6% / 5%), po 2 letech +20% / +41%, vynos/propad 1.47
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] sazby_okno_6m: zamitnuto

* zmena rozdilu sazeb se meri za 6 mesicu misto 3 (prahy stejne)
* kandidat: 2019-22: **+9.6%** rocne, propad 21%, 0.9 ziskovych/mesic (marze 10% / 0% / 0% / 0%), po 2 letech +13% / +16%, vynos/propad 0.46; 2023-26: **+6.9%** rocne, propad 15%, 1.9 ziskovych/mesic (marze 8% / 2% / 2% / 2%), po 2 letech +5% / +10%, vynos/propad 0.46
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12_mesicne] brzda_10_polovina: zamitnuto

* kdyz je ucet modelu vic nez 10 % pod maximem, nove obchody polovicni
* kandidat: 2019-22: **+82.6%** rocne, propad 20%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 6%), po 2 letech +99% / +70%, vynos/propad 4.07; 2023-26: **+29.8%** rocne, propad 27%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +22% / +70%, vynos/propad 1.08
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] brzda_15_polovina: zamitnuto

* kdyz je ucet modelu vic nez 15 % pod maximem, nove obchody polovicni
* kandidat: 2019-22: **+86.8%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.47; 2023-26: **+32.1%** rocne, propad 27%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.17
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] brzda_5_dvetretiny: zamitnuto

* kdyz je ucet modelu vic nez 5 % pod maximem, nove obchody na 2/3
* kandidat: 2019-22: **+82.3%** rocne, propad 21%, 3.4 ziskovych/mesic (marze 20% / 20% / 8% / 6%), po 2 letech +97% / +72%, vynos/propad 3.89; 2023-26: **+26.6%** rocne, propad 31%, 2.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +13% / +66%, vynos/propad 0.86
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12] brzda_10_polovina: zamitnuto

* kdyz je ucet modelu vic nez 10 % pod maximem, nove obchody polovicni
* kandidat: 2019-22: **+71.3%** rocne, propad 24%, 3.3 ziskovych/mesic (marze 20% / 20% / 6% / 4%), po 2 letech +106% / +44%, vynos/propad 2.92; 2023-26: **+16.7%** rocne, propad 25%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 5%), po 2 letech +19% / +32%, vynos/propad 0.67
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] brzda_15_polovina: zamitnuto

* kdyz je ucet modelu vic nez 15 % pod maximem, nove obchody polovicni
* kandidat: 2019-22: **+79.4%** rocne, propad 24%, 3.3 ziskovych/mesic (marze 20% / 20% / 5% / 5%), po 2 letech +107% / +58%, vynos/propad 3.37; 2023-26: **+23.4%** rocne, propad 24%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 5%), po 2 letech +20% / +49%, vynos/propad 0.98
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] brzda_5_dvetretiny: zamitnuto

* kdyz je ucet modelu vic nez 5 % pod maximem, nove obchody na 2/3
* kandidat: 2019-22: **+71.5%** rocne, propad 24%, 3.3 ziskovych/mesic (marze 20% / 20% / 5% / 5%), po 2 letech +107% / +44%, vynos/propad 3.03; 2023-26: **+20.9%** rocne, propad 19%, 2.2 ziskovych/mesic (marze 15% / 15% / 5% / 5%), po 2 letech +21% / +35%, vynos/propad 1.08
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12_mesicne] stop_na_zavreni_15: zamitnuto

* stop 4 ATR plati jen pri zavreni dne (NY 17:00), behem dne jen nouzovy stop 6 ATR
* kandidat: 2019-22: **+88.1%** rocne, propad 24%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +94% / +86%, vynos/propad 3.72; 2023-26: **+31.3%** rocne, propad 22%, 2.3 ziskovych/mesic (marze 15% / 15% / 6% / 5%), po 2 letech +18% / +60%, vynos/propad 1.42
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] stop_na_zavreni_125: zamitnuto

* stop 4 ATR plati jen pri zavreni dne, behem dne nouzovy stop 5 ATR
* kandidat: 2019-22: **+86.6%** rocne, propad 24%, 3.4 ziskovych/mesic (marze 20% / 20% / 5% / 5%), po 2 letech +91% / +86%, vynos/propad 3.65; 2023-26: **+31.5%** rocne, propad 21%, 2.3 ziskovych/mesic (marze 15% / 15% / 5% / 5%), po 2 letech +19% / +59%, vynos/propad 1.49
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] stop_3_na_zavreni_2: zamitnuto

* stop 3 ATR pri zavreni dne, behem dne nouzovy stop 6 ATR
* kandidat: 2019-22: **+98.4%** rocne, propad 21%, 3.4 ziskovych/mesic (marze 20% / 20% / 8% / 5%), po 2 letech +104% / +98%, vynos/propad 4.76; 2023-26: **+34.7%** rocne, propad 30%, 2.2 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +17% / +75%, vynos/propad 1.14
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12] stop_na_zavreni_15: zamitnuto

* stop 4 ATR plati jen pri zavreni dne (NY 17:00), behem dne jen nouzovy stop 6 ATR
* kandidat: 2019-22: **+89.2%** rocne, propad 21%, 3.4 ziskovych/mesic (marze 20% / 20% / 10% / 3%), po 2 letech +115% / +69%, vynos/propad 4.19; 2023-26: **+20.3%** rocne, propad 46%, 2.2 ziskovych/mesic (marze 15% / 15% / 10% / 3%), po 2 letech +3% / +57%, vynos/propad 0.44
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] stop_na_zavreni_125: zamitnuto

* stop 4 ATR plati jen pri zavreni dne, behem dne nouzovy stop 5 ATR
* kandidat: 2019-22: **+89.9%** rocne, propad 21%, 3.4 ziskovych/mesic (marze 20% / 20% / 10% / 3%), po 2 letech +115% / +71%, vynos/propad 4.22; 2023-26: **+20.9%** rocne, propad 46%, 2.2 ziskovych/mesic (marze 15% / 15% / 10% / 3%), po 2 letech +2% / +61%, vynos/propad 0.45
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] stop_3_na_zavreni_2: zamitnuto

* stop 3 ATR pri zavreni dne, behem dne nouzovy stop 6 ATR
* kandidat: 2019-22: **+95.8%** rocne, propad 21%, 3.4 ziskovych/mesic (marze 20% / 20% / 10% / 3%), po 2 letech +115% / +82%, vynos/propad 4.50; 2023-26: **+21.4%** rocne, propad 46%, 2.2 ziskovych/mesic (marze 15% / 15% / 10% / 3%), po 2 letech +3% / +61%, vynos/propad 0.47
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12_mesicne] pred_cb_ztrata_stop_1_atr: zamitnuto

* obchod ve ztrate den pred rozhodnutim centralni banky: stop na 1 ATR od zavreni
* kandidat: 2019-22: **+90.6%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 8% / 5%), po 2 letech +103% / +83%, vynos/propad 4.75; 2023-26: **+28.4%** rocne, propad 30%, 2.2 ziskovych/mesic (marze 20% / 20% / 8% / 5%), po 2 letech +24% / +40%, vynos/propad 0.96
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12_mesicne] pred_cb_ztrata_stop_05_atr: zamitnuto

* obchod ve ztrate den pred rozhodnutim centralni banky: stop na 0.5 ATR od zavreni
* kandidat: 2019-22: **+68.5%** rocne, propad 19%, 3.2 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +63% / +78%, vynos/propad 3.53; 2023-26: **+26.8%** rocne, propad 30%, 2.2 ziskovych/mesic (marze 20% / 20% / 8% / 5%), po 2 letech +26% / +33%, vynos/propad 0.90
* sampion:  2019-22: **+87.2%** rocne, propad 19%, 3.4 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +96% / +82%, vynos/propad 4.49; 2023-26: **+39.5%** rocne, propad 28%, 2.3 ziskovych/mesic (marze 20% / 20% / 6% / 5%), po 2 letech +24% / +75%, vynos/propad 1.43

### 2026-10-02 - [champion_12] pred_cb_ztrata_stop_1_atr: zamitnuto

* obchod ve ztrate den pred rozhodnutim centralni banky: stop na 1 ATR od zavreni
* kandidat: 2019-22: **+90.4%** rocne, propad 28%, 3.3 ziskovych/mesic (marze 20% / 20% / 10% / 5%), po 2 letech +127% / +63%, vynos/propad 3.26; 2023-26: **+26.0%** rocne, propad 24%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 5%), po 2 letech +21% / +39%, vynos/propad 1.08
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

### 2026-10-02 - [champion_12] pred_cb_ztrata_stop_05_atr: zamitnuto

* obchod ve ztrate den pred rozhodnutim centralni banky: stop na 0.5 ATR od zavreni
* kandidat: 2019-22: **+70.4%** rocne, propad 28%, 3.2 ziskovych/mesic (marze 20% / 20% / 10% / 5%), po 2 letech +86% / +59%, vynos/propad 2.54; 2023-26: **+24.5%** rocne, propad 23%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 5%), po 2 letech +23% / +31%, vynos/propad 1.05
* sampion:  2019-22: **+81.0%** rocne, propad 26%, 3.3 ziskovych/mesic (marze 20% / 20% / 8% / 4%), po 2 letech +114% / +56%, vynos/propad 3.11; 2023-26: **+26.0%** rocne, propad 28%, 2.2 ziskovych/mesic (marze 15% / 15% / 6% / 4%), po 2 letech +16% / +48%, vynos/propad 0.94

