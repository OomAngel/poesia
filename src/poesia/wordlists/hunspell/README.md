# Spanish (Mexico) Hunspell dictionary

`es_MX.dic` and `es_MX.aff` (not in git: run `python src/poesia/wordlists/fetch_hunspell.py`,
pinned to a commit and checked by SHA-256; the Calaveritas image does this when it is built) come from the RLA-ES project (Recursos Lingüísticos Abiertos del
Español), as shipped in LibreOffice's
dictionaries repository (`es/es_MX.{dic,aff}`, fetched 2026-11-08 from
https://github.com/LibreOffice/dictionaries/tree/master/es).

Licence: the project distributes the dictionaries under three disjoint licences, GNU GPL 3 or later,
GNU LGPL 3 or later, or MPL 1.1 or later, at the user's choice. PoesIA uses them under the **MPL
1.1** (`MPL-1.1.txt`), not under PoesIA's own licence; changes to these two files are shared under
the same terms.

Used by `poesia.calaveritas.quality.made_up` (read with spylls, MPL 2.0) to catch words that do not
exist, such as a name cut short to make a rhyme ("la Catrí").
