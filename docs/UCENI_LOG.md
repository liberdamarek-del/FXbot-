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

