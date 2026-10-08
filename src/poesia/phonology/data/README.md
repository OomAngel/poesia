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

`fr_words.tsv`: French word classes the spelling cannot show, for 3,796 words: `v` a verb's
third-person plural whose *-ent* is silent (*chantent*), `n` an *-ent* word that is pronounced
(*souvent*, *patient*), `d` forms of *-ier* verbs that keep *i* apart (*ou-bli-er*, *en-vi-ez*),
`s` verb *-ions*/*-iez* forms that join it (*é-tions*). Built by `scripts/build_french_lexicon.py`
from kaikki.org's French Wiktionary extract (download of 2026-10-08), for the words of
`src/poesia/wordlists/fr.txt` and the Métrique en Ligne gold verses. The French scanner agrees
exactly with the experts' metre on 95.9% of 72,412 verses (`scripts/check_french_scansion.py`;
the rules were tuned on the same set).

`de_words.tsv`: German word stress for 5,904 words whose stressed syllable the scanner's rules
(unstressed prefixes *be- ge- er- ver- zer- ent- emp-*, a few stressed foreign suffixes, else
the first syllable) place wrongly: word, a syllable column kept at -1 (the rules count better
than Wiktionary's hyphenation), and the stressed syllable counted from the start. Read from
Wiktionary's IPA and passed from each lemma to its forms (*verlieren* -> *verliert*). Built by
`scripts/build_german_lexicon.py` (kaikki.org German extract, 2026-10-08) for the words of
`src/poesia/wordlists/de.txt` and the gold lines. On the 3,507 expert-annotated lines of
Haider et al. (`scripts/check_german_scansion.py`): syllables 99.1% exact; stress of words of
two or more syllables on a stressed position 91.7% (rules) -> 94.7% (with the table).

**Licence (all three files):** Wiktionary content, CC BY-SA 4.0 (Wiktionary contributors, via
kaikki.org, Tatu Ylonen's wiktextract). These files keep that licence, not PoesIA's MIT.
