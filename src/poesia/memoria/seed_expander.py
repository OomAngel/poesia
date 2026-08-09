"""Seed word expansion across multiple dimensions.

Expands a root word into synonyms, antonyms, rhymes, semantic neighbors,
collocations, hypernyms, hyponyms, and cross-language equivalents.

Sources:
- WordNet (wn OR nltk) for synonyms, antonyms, hypernyms, hyponyms
- Phonology layer for rhymes (consonant and assonant)
- Embeddings for semantic neighbors
- Datamuse API for collocations (optional, online)
- spaCy for lemmatization and POS
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from poesia.memoria.records import SeedExpansion


@dataclass
class SeedExpander:
    """Expands seed words across multiple dimensions."""

    language: str = "es"
    _wn_loaded: bool = field(default=False, repr=False)
    _nlp: Any = field(default=None, repr=False)

    def __post_init__(self):
        """Lazy-load spaCy model when first needed."""
        if self._nlp is None:
            try:
                import spacy

                self._nlp = spacy.load("es_core_news_sm")
            except Exception:
                self._nlp = None

    def expand(
        self,
        word: str,
        include_datamuse: bool = False,
        embedding_client=None,
        reference_corpus: list[str] | None = None,
    ) -> SeedExpansion:
        """Expand a word across all available dimensions."""
        expansion = SeedExpansion()

        # WordNet expansions (synonyms, antonyms, hypernyms, hyponyms)
        wn_result = self._expand_wordnet(word)
        expansion.synonyms = wn_result.get("synonyms", [])
        expansion.antonyms = wn_result.get("antonyms", [])
        expansion.hypernyms = wn_result.get("hypernyms", [])
        expansion.hyponyms = wn_result.get("hyponyms", [])

        # Phonology expansions (rhymes)
        rhyme_result = self._expand_rhymes(word)
        expansion.rhymes_consonant = rhyme_result.get("consonant", {})
        expansion.rhymes_assonant = rhyme_result.get("assonant", {})

        # Semantic neighbors (via embeddings)
        if embedding_client and reference_corpus:
            expansion.semantic_neighbors = self._expand_semantic(
                word, embedding_client, reference_corpus
            )

        # Collocations (via Datamuse, optional)
        if include_datamuse:
            dm_results = self._expand_datamuse(word)
            expansion.collocations = dm_results
            # If WordNet returned empty (e.g. Spanish with server down),
            # use Datamuse results as synonyms as well
            if not expansion.synonyms and dm_results:
                expansion.synonyms = dm_results

        # spaCy lemmatization
        if self._nlp:
            try:
                doc = self._nlp(word)
                if doc:
                    expansion.etymology = doc[0].lemma_
            except Exception:
                pass

        return expansion

    def _collect_wn_synset_relations(
        self, synset, result: dict[str, list[str]], seen: dict[str, set[str]]
    ) -> None:
        """Collect antonym/hypernym/hyponym lemmas for one ``wn`` synset."""
        for sense in synset.senses():
            for ant in sense.get_related("antonym"):
                w = ant.word().replace("_", " ")  # type: ignore[attr-defined]  # wn stubs say Word; runtime exposes replace
                if w.lower() not in seen["ant"]:
                    seen["ant"].add(w.lower())
                    result["antonyms"].append(w)
            for hyp in sense.get_related("hypernym"):
                w = hyp.word().replace("_", " ")  # type: ignore[attr-defined]
                if w.lower() not in seen["hyper"]:
                    seen["hyper"].add(w.lower())
                    result["hypernyms"].append(w)
            for hyp in sense.get_related("hyponym"):
                w = hyp.word().replace("_", " ")  # type: ignore[attr-defined]
                if w.lower() not in seen["hypo"]:
                    seen["hypo"].add(w.lower())
                    result["hyponyms"].append(w)

    def _expand_wordnet_wn(self, word: str) -> dict:
        """WordNet relations via the ``wn`` package (multilingual, offline)."""
        result: dict[str, list[str]] = {
            "synonyms": [],
            "antonyms": [],
            "hypernyms": [],
            "hyponyms": [],
        }
        import wn as _wn

        if not self._wn_loaded:
            try:
                _wn.download("ewn:2020")
                if self.language == "es":
                    _wn.download("omw-es:1.4")
            except Exception:
                pass
            self._wn_loaded = True

        wn_lang = "spa" if self.language == "es" else "eng"
        synsets = _wn.synsets(word, lang=wn_lang)
        seen: dict[str, set[str]] = {"syn": set(), "ant": set(), "hyper": set(), "hypo": set()}

        for synset in synsets[:3]:
            for lemma in synset.lemmas():
                w = lemma.word().replace("_", " ")  # type: ignore[attr-defined]  # wn stubs say str; runtime Lemma.word()
                if w.lower() != word.lower() and w.lower() not in seen["syn"]:
                    seen["syn"].add(w.lower())
                    result["synonyms"].append(w)
            self._collect_wn_synset_relations(synset, result, seen)

        for key in result:
            result[key] = list(dict.fromkeys(result[key]))[:15]
        return result

    def _collect_nltk_lemma(self, lemma, word: str, result: dict[str, list[str]]) -> None:
        """Collect one NLTK lemma + its first antonym into ``result``."""
        w = lemma.name().replace("_", " ")
        if w.lower() != word.lower() and w not in result["synonyms"]:
            result["synonyms"].append(w)
        if lemma.antonyms():
            ant = lemma.antonyms()[0].name().replace("_", " ")
            if ant not in result["antonyms"]:
                result["antonyms"].append(ant)

    def _collect_nltk_syn(self, syn, word: str, result: dict[str, list[str]]) -> None:
        """Collect lemma/antonym/hypernym/hyponym names for one NLTK synset."""
        for lemma in syn.lemmas():
            self._collect_nltk_lemma(lemma, word, result)
        for hyper in syn.hypernyms():
            for h_lemma in hyper.lemmas():
                w = h_lemma.name().replace("_", " ")
                if w not in result["hypernyms"]:
                    result["hypernyms"].append(w)
        for hypo in syn.hyponyms():
            for h_lemma in hypo.lemmas():
                w = h_lemma.name().replace("_", " ")
                if w not in result["hyponyms"]:
                    result["hyponyms"].append(w)

    def _expand_wordnet_nltk(self, word: str, result: dict[str, list[str]]) -> None:
        """English-only WordNet fallback via NLTK (fills ``result`` in place)."""
        from nltk.corpus import wordnet as nltk_wn

        if self.language != "en":
            return
        for syn in nltk_wn.synsets(word):
            self._collect_nltk_syn(syn, word, result)
        for key in result:
            result[key] = result[key][:15]

    def _expand_wordnet(self, word: str) -> dict:
        """Get synonyms, antonyms, hypernyms, hyponyms from WordNet.

        Tries ``wn`` (Open Multilingual Wordnet) first, falls back to
        NLTK WordNet (English only).
        """
        result: dict[str, list[str]] = {
            "synonyms": [],
            "antonyms": [],
            "hypernyms": [],
            "hyponyms": [],
        }

        try:
            return self._expand_wordnet_wn(word)
        except Exception:
            # Fallback: NLTK WordNet (English only)
            try:
                self._expand_wordnet_nltk(word, result)
            except Exception:
                pass

        return result

    def _expand_rhymes(self, word: str) -> dict:
        """Get consonant and assonant rhymes."""
        if self.language == "es":
            return self._expand_rhymes_spanish(word)
        elif self.language == "en":
            return self._expand_rhymes_english(word)
        return {"consonant": {}, "assonant": {}}

    @staticmethod
    def _spanish_rhyme_endings(
        word_lower: str, stressed_idx: int, vowels: str, vowel_map: dict[str, str]
    ) -> tuple[str, str]:
        """Consonant + assonant rhyme endings for a Spanish word."""
        consonant_ending = word_lower[stressed_idx:]
        for acc, norm in vowel_map.items():
            consonant_ending = consonant_ending.replace(acc, norm)
        assonant_ending = "".join(
            vowel_map.get(c, c) for c in word_lower[stressed_idx:] if c in vowels
        )
        return consonant_ending, assonant_ending

    def _expand_rhymes_spanish(self, word: str) -> dict:
        """Spanish rhyme expansion using vowel patterns."""
        result: dict[str, dict[str, list[str]]] = {"consonant": {}, "assonant": {}}
        vowels = "aeiouáéíóú"
        vowel_map = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u"}
        word_lower = word.lower()

        vowel_indices = [i for i, c in enumerate(word_lower) if c in vowels]
        if not vowel_indices:
            return result

        # Find stressed vowel
        stressed_idx = vowel_indices[-1]
        for idx in vowel_indices:
            if word_lower[idx] in "áéíóú":
                stressed_idx = idx
                break

        consonant_ending, assonant_ending = self._spanish_rhyme_endings(
            word_lower, stressed_idx, vowels, vowel_map
        )

        if consonant_ending:
            result["consonant"][f"-{consonant_ending}"] = []
        if assonant_ending:
            result["assonant"][assonant_ending] = []

        return result

    def _expand_rhymes_english(self, word: str) -> dict:
        """English rhyme expansion using pronouncing library."""
        result: dict[str, dict[str, list[str]]] = {"consonant": {}, "assonant": {}}
        try:
            import pronouncing

            rhymes = pronouncing.rhymes(word.lower())
            if rhymes:
                result["consonant"]["rhymes"] = rhymes[:20]
        except ImportError:
            pass
        return result

    def _expand_semantic(
        self, word: str, embedding_client, reference_corpus: list[str], top_k: int = 10
    ) -> list[str]:
        """Find semantically similar words from a reference corpus."""
        import math

        if not reference_corpus:
            return []

        word_emb = embedding_client.embed_one(word)
        corpus_embs = embedding_client.embed(reference_corpus)

        scores = []
        for ref_word, ref_emb in zip(reference_corpus, corpus_embs, strict=True):
            if ref_word.lower() == word.lower():
                continue
            dot = sum(a * b for a, b in zip(word_emb, ref_emb, strict=True))
            norm_a = math.sqrt(sum(a * a for a in word_emb))
            norm_b = math.sqrt(sum(b * b for b in ref_emb))
            if norm_a > 0 and norm_b > 0:
                scores.append((ref_word, dot / (norm_a * norm_b)))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [w for w, _ in scores[:top_k]]

    def _expand_datamuse(self, word: str) -> list[str]:
        """Get collocations from Datamuse API."""
        try:
            import json
            import urllib.request

            url = f"https://api.datamuse.com/words?ml={word}&max=10"
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
                return [item["word"] for item in data]
        except Exception:
            return []
