# Word lists for rhyme-word suggestions

`es.txt`, `en.txt`, `it.txt`: the 40,000 most frequent words per language, most frequent
first, one per line, letters only. Used by `poesia.word_ideas` to offer common rhyme words.

Derived on 2026-10-07 from [wordfreq](https://github.com/rspeer/wordfreq) 3.1.1
(`top_n_list(lang, 80000, wordlist="best")`, filtered to words of letters only). wordfreq's
code is Apache-2.0; its data is licensed **CC BY-SA 4.0** (Robyn Speer and contributors,
built from Wikipedia, subtitles, news, books, web text and other sources listed in its
README). These three files are therefore CC BY-SA 4.0, not MIT like the rest of PoesIA; if you
change them, share the result under the same licence.
