# FXBOT Blok D – vyhodnocení zamčených predikcí

Vyžaduje Blok C.

## Co je nové

| Soubor | Účel |
|---|---|
| src/resolver.py | z uložených minutových svíček zjistí, co se s predikcí stalo, a zapíše to do evidence |
| scripts/resolve.py | český výpis všech predikcí a jejich výsledků |
| test_d1_resolver.py | ručně sestavené cenové průběhy pro všechny případy |

## Pravidla vyhodnocení

- použijí se jen svíčky, které se otevřely **po** zamčení predikce (žádný zpětný pohled)
- CEKAT NA NAKUP/PRODEJ: vstup je splněn, když cena dosáhne vstupní úrovně; když dřív dosáhne cíle TP1, je to **bez vstupu**
- KOUPIT/PRODAT TED: vstup za cenu v okamžiku zamčení
- SL i TP1 ve **stejné minutě** = **pořadí neznámé**, nikdy se nehádá
- konec horizontu (24 h) bez výsledku = vyprselo; nevstoupilo se = neaktivováno
- chybějící minuty před rozhodnutím = **nerozhodnuto**, po opravě dat se rozhodne
- data ještě nedosahují do konce horizontu = predikce zůstává otevřená
- do evidence se stavy a výsledky jen **přidávají**, opakované spuštění nic nezdvojí

Předpoklady jsou provizorní: střední ceny bez spreadu a slippage (výsledky jsou optimistické),
data mají zpoždění asi 2–3 minuty, u vzorku pod 20 uzavřených predikcí jsou čísla jen popisná.

## Použití

    python scripts/update_data.py     # data musí sahat do současnosti
    python scripts/resolve.py         # vyhodnotí a ukáže všechny predikce
    python scripts/resolve.py --open  # jen otevřené

Vrácení zpět: `python …/apply_block_d.py --rollback backup_block_d_<časová_značka>`
