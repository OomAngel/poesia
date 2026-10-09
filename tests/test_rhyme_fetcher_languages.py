"""The prompt's rhyme word bank stays in the poem's language (2026-10-09 benchmark bug)."""

import pytest

from poesia.generation.rhyme_fetcher import fetch_rhyme_words
from poesia.webapp import _phonology


@pytest.mark.parametrize(
    ("word", "language"), [("Zeit", "de"), ("silence", "fr"), ("cuore", "it"), ("mar", "es")]
)
def test_word_bank_rhymes_in_the_poems_language(word, language, monkeypatch):
    import poesia.generation.rhyme_fetcher as rf

    def no_network(*_a, **_k):  # Datamuse (English-only) must not be asked for these languages
        raise AssertionError("Datamuse called")

    monkeypatch.setattr(rf, "_fetch_datamuse", no_network)
    words = fetch_rhyme_words(word, language=language)
    assert len(words) >= 4
    phon = _phonology(language)
    key = phon.rhyme_key(word).consonant
    assert all(phon.rhyme_key(w).consonant == key for w in words)


def test_german_nouns_keep_their_capital():
    assert "Arbeit" in fetch_rhyme_words("Zeit", language="de", max_results=40)
