# Rutiny (R-044, 11. 10. 2026)

Každá rutina spouští **nové krátké sezení** s připojeným repozitářem `liberdamarek-del/FXbot-`. Dřív se všechny
spouštěly v jednom dlouhém rozhovoru. Ten měl přes 300 000 tokenů paměti, které se četly v každém kroku, a to
spotřebovávalo týdenní limit.

## Rutiny

| Rutina | Kdy | Co dělá |
|---|---|---|
| FXBOT denní aktualizace (nové sezení, 23:07) | po–pá 17:07 New York | `rutina.py denni`, deník, přehled, commit |
| FXBOT páteční signály (nové sezení, 22:05) | pá 16:05 New York | totéž a k tomu signály pro uživatele |
| FXBOT učení – středa (nové sezení, 17:40) | st 17:40 Praha | `rutina.py uceni`, pokusy, průzkum, přehled |
| FXBOT učení – sobota (nové sezení, 8:57) | so 8:57 Praha | navíc heuristiky, týdenní výzkum a souhrn týdne |

## Proč musí uživatel jednou kliknout

Rutiny jsem založil nástrojem a ten neumí připojit repozitář. Sezení bez repozitáře sice spustí aktualizaci, ale
nemůže uložit deník predikcí a forward test do gitu. Vyzkoušeno 11. 10. 2026: čtyři zkušební běhy bez repozitáře
nic neuložily. Běh s repozitářem připojeným od začátku prošel celý za 70 s.

Ve webu se repozitář doplní takto:

1. Otevři [claude.ai/code/routines](https://claude.ai/code/routines).
2. U každé ze čtyř rutin „FXBOT … (nové sezení …)“: otevři ji, v menu u názvu zvol **Edit**, v části
   **Repositories** přidej `liberdamarek-del/FXbot-` a ulož. Model může zůstat Sonnet, je levnější a na rutiny
   stačí.
3. Zapni ji přepínačem nahoře.
4. Vypni čtyři staré rutiny: „FXBOT aktualizace jednou denně (23:07)“, „FXBOT páteční signály“,
   „FXBOT učení ve středu (spolu se sobotou 2× týdně)“ a „FXBOT sobotní učení (s novými daty)“. Nebo napiš
   v hlavním rozhovoru „hotovo“ a vypnu je já.

Dokud se to nestane, běží staré rutiny jako dosud, takže se nic neztratí.

## Kontrola

Každý běh zapíše `learning/provoz/posledni_beh.json`: čas, typ rutiny a výsledek diagnostiky. Když tento soubor
v gitu dlouho nepřibývá, rutina neběží.
