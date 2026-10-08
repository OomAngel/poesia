# Phonology data

`it_stress.tsv`: Italian word stress, the stressed syllable counted from the end (0 = last),
for 44,272 words; 7,131 of them are words the scanner's spelling rule (second-to-last syllable
unless a written accent says otherwise) gets wrong. The scanner uses the table before the rule;
the rhyme-word suggestions offer a longer Italian word only when its stress is in the table.
Built by `scripts/build_italian_stress.py` from Wiktionary's hyphenations and IPA as published
by kaikki.org (download of 2026-10-08), for the words of `src/poesia/wordlists/it.txt` and the
Biblioteca Italiana gold lines. Words whose Wiktionary entries disagree (*àncora* / *ancóra*)
are left out. Effect on the 10,001 expert-annotated endecasillabi: stress recall 80.2% → 82.3%,
precision 90.0% → 92.3%; exact syllable count 79.5% → 79.6%.

**Licence:** Wiktionary content, CC BY-SA 4.0 (Wiktionary contributors, via kaikki.org,
Tatu Ylonen's wiktextract). This file keeps that licence, not PoesIA's MIT.
