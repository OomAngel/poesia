"""Seed word expansion across multiple dimensions.

Expands a root word into synonyms, antonyms, rhymes, semantic neighbors,
collocations, hypernyms, hyponyms, and cross-language equivalents.

Sources:
- WordNet (`wn` package) for synonyms, antonyms, hypernyms, hyponyms
- Phonology layer for rhymes (consonant and assonant)
- Embeddings for semantic neighbors
- Datamuse API for collocations (optional, online)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from poesia.memoria.records import SeedExpansion


@dataclass
class SeedExpander:
    """Expands seed words across multiple dimensions."""

    language: str = "es"
    _wn_loaded: bool = field(default=False, repr=False)

    def expand(
        self,
        word: str,
        include_datamuse: bool = False,
        embedding_client=None,
        reference_corpus: list[str] | None = None,
    ) -> SeedExpansion:
        """Expand a word across all available dimensions."""
        expansion = SeedExpansion()

        # WordNet expansions
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
            expansion.collocations = self._expand_datamuse(word)

        return expansion

    def _expand_wordnet(self, word: str) -> dict:
        """Get synonyms, antonyms, hypernyms, hyponyms from WordNet."""
        try:
            import wn
        except ImportError:
            return {}

        result = {"synonyms": [], "antonyms": [], "hypernyms": [], "hyponyms": []}
        wn_lang = "spa" if self.language == "es" else "eng"

        try:
            if not self._wn_loaded:
                try:
                    wn.download("ewn:2020", progress=False)
                    if self.language == "es":
                        wn.download("omw-es31:1.4", progress=False)
                except Exception:
                    pass
                self._wn_loaded = True

            synsets = wn.synsets(word, lang=wn_lang)
            seen = {"syn": set(), "ant": set(), "hyper": set(), "hypo": set()}

            for synset in synsets[:3]:
                for lemma in synset.lemmas():
                    w = lemma.word().replace("_", " ")
                    if w.lower() != word.lower() and w.lower() not in seen["syn"]:
                        seen["syn"].add(w.lower())
                        result["synonyms"].append(w)

                for sense in synset.senses():
                    for ant in sense.get_related("antonym"):
                        w = ant.word().replace("_", " ")
                        if w.lower() not in seen["ant"]:
                            seen["ant"].add(w.lower())
                            result["antonyms"].append(w)

                for hyper in synset.hypernyms():
                    for lemma in hyper.lemmas()[:2]:
                        w = lemma.word().replace("_", " ")
                        if w.lower() not in seen["hyper"]:
                            seen["hyper"].add(w.lower())
                            result["hypernyms"].append(w)

                for hypo in synset.hyponyms()[:5]:
                    for lemma in hypo.lemmas()[:1]:
                        w = lemma.word().replace("_", " ")
                        if w.lower() not in seen["hypo"]:
                            seen["hypo"].add(w.lower())
                            result["hyponyms"].append(w)
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

    def _expand_rhymes_spanish(self, word: str) -> dict:
        """Spanish rhyme expansion using vowel patterns."""
        result = {"consonant": {}, "assonant": {}}
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

        # Consonant rhyme: from stressed vowel to end
        consonant_ending = word_lower[stressed_idx:]
        for acc, norm in vowel_map.items():
            consonant_ending = consonant_ending.replace(acc, norm)

        # Assonant rhyme: just the vowels
        assonant_ending = "".join(
            vowel_map.get(c, c) for c in word_lower[stressed_idx:] if c in vowels
        )

        if consonant_ending:
            result["consonant"][f"-{consonant_ending}"] = []
        if assonant_ending:
            result["assonant"][assonant_ending] = []

        return result

    def _expand_rhymes_english(self, word: str) -> dict:
        """English rhyme expansion using pronouncing library."""
        result = {"consonant": {}, "assonant": {}}
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
        for ref_word, ref_emb in zip(reference_corpus, corpus_embs):
            if ref_word.lower() == word.lower():
                continue
            dot = sum(a * b for a, b in zip(word_emb, ref_emb))
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

            url = f"https://api.datamuse.com/words?rel_trg={word}&max=20"
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
                return [item["word"] for item in data]
        except Exception:
            return []
