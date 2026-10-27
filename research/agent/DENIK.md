# Deník výzkumných běhů

* **2026-10-13 (založení):** složka a protokol vytvořeny. Zatím žádný výzkumný běh, žádný zdroj. První řádný běh podle plánu (út, čt, ne 07:23 Praha).

* **2026-10-13 (běh 1):** směry pamet-stav, sebehodnoceni-kalibrace, průzkumně experimentovani-falesne-objevy. 3 vyhledávání + 3 stažení (jen abstrakty arXiv). Nalezeno: 3 zdroje (2x B, 1x C), návrhy N-002 až N-004. Žádný experiment nespuštěn. Slabé: žádný zdroj nebyl přečten celý; čísla z vyhledávání nepřebrána.

* **2026-10-15 (běh 2):** hlavní směr nastroje-robustnost, průzkumně planovani-rozpocet. 3 vyhledávání + 3 stažení (abstrakty). Nalezeno: 2 zdroje (B), návrh N-005 (kontrola čerstvosti vstupů a výstupů rutiny). Rozpočet tokenů: v hledání jen názvy/úryvky (CliffCompaction 2609.26779, ContextBudget 2604.01664), nečteno, nezapsáno jako zjištění; naše sezení jsou čerstvá, takže kompakce kontextu se nás týká málo. Žádný experiment. Slabé: jen abstrakty, mitigace z cizích systémů.

* **2026-10-18 (běh 3):** hlavní směr pamet-stav, průzkumně uceni-ze-zpetne-vazby. 2 vyhledávání + 2 stažení (abstrakty). Nalezeno: 2 zdroje (B), nový návrh N-006 (informační monitor driftu, vzorek zatím chybí). Pamět-stav: 2607.01988 jen potvrzuje stávající návrh (oddělené vrstvy, hash řetěz), nic nového k použití -> 1 prázdný běh. Žádný experiment. Slabé: jen abstrakty, syntetické/teoretické výsledky.

* **2026-10-20 (běh 4):** hlavní směr experimentovani-falesne-objevy, průzkumně pruzkum-neobvykle. 3 vyhledávání + 2 stažení (abstrakty arXiv). Nalezeno: 2 zdroje (B): 2608.27734 (počítadlo pokusů + deflace, podporuje N-004), 2606.21024 (paměť neúspěchů -> nový návrh N-007). Žádný experiment. Slabé: jen abstrakty, vzorce a čísla nepřečteny, jiné domény než FX; druhé vyhledávání (hash-řetězové deníky) nedalo nic použitelného (jen komunitní projekty, třída C, nezapsáno).

* **2026-10-22 (běh 5):** hlavní směr sebehodnoceni-kalibrace, průzkumně planovani-rozpocet. 2 vyhledávání + 2 stažení (abstrakty arXiv). Nalezeno: 2 zdroje (B): 2605.26703 (teorie proper kalibrace, bez dat) a 2606.00198 (BAGEN: modely rozpočet odhadují špatně, r=0.35, pokrytí intervalů max 47 %). Oba jen potvrzují stávající návrhy (N-003, N-001), žádný nový návrh ani experiment -> oba směry počítány jako prázdný běh. Slabé: jen abstrakty; BAGEN řeší dlouhé agentní úlohy, ne naše krátké rutiny.

* **2026-10-27 (běh 6):** hlavní směr pamet-stav, průzkumně nastroje-robustnost. 2 vyhledávání + 2 stažení (abstrakty arXiv). Nalezeno: 2 zdroje (B): 2605.06527 (STALE, zastarávání paměti, podporuje N-002) a 2602.16666 (spolehlivost agentů vícerozměrně, podporuje N-001). Nic skutečně nového: žádný nový návrh ani experiment, oba směry počítány jako prázdný běh (pamet-stav 2, nastroje-robustnost 1). Slabé: jen abstrakty, cizí domény, žádné údaje o cron rutinách (to vyhledávání výslovně nic nenašlo).
