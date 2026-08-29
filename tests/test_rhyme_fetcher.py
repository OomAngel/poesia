"""Tests for RhymeFetcher — offline paths only (no real network calls)."""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from poesia.generation.rhyme_fetcher import (
    _fetch_datamuse,
    _fetch_pronouncing,
    _fetch_suffix_match_es,
    _spanish_rhyme_suffix,
    fetch_rhyme_words,
)


class TestSpanishRhymeSuffix:
    @pytest.mark.parametrize(
        ("word", "expected"),
        [
            ("oscura", "ura"),  # plain
            ("razón", "on"),  # accented stressed vowel
            ("oscura,", "ura"),  # punctuation stripped
            ("", ""),  # empty
            ("brr", ""),  # no vowels
        ],
    )
    def test_spanish_rhyme_suffix(self, word: str, expected: str) -> None:
        assert _spanish_rhyme_suffix(word) == expected


class TestSuffixMatchEs:
    def test_finds_words_ending_in_ura(self) -> None:
        results = _fetch_suffix_match_es("oscura")
        assert len(results) > 0
        assert all(w.endswith("ura") for w in results)

    def test_excludes_anchor_word(self) -> None:
        results = _fetch_suffix_match_es("oscura")
        assert "oscura" not in results

    def test_finds_or_rhymes(self) -> None:
        results = _fetch_suffix_match_es("amor")
        assert len(results) > 0
        assert all(w.endswith("or") for w in results)

    def test_short_suffix_returns_empty(self) -> None:
        # suffix would be just "a" — too broad, returns empty
        results = _fetch_suffix_match_es("a")
        assert results == []


class TestFetchPronouncing:
    """CMUdict has no case to filter proper nouns on (it's all-uppercase),
    so `_fetch_pronouncing` cross-checks a general-vocabulary wordlist
    instead. These mock both `pronouncing` and the wordlist loader so they
    don't depend on real CMUdict contents or a real nltk download."""

    def test_filters_out_words_missing_from_common_wordlist(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_pronouncing = MagicMock()
        fake_pronouncing.rhymes.return_value = ["harvest", "bartoli", "forecast"]
        monkeypatch.setitem(sys.modules, "pronouncing", fake_pronouncing)
        monkeypatch.setattr(
            "poesia.generation.rhyme_fetcher._load_common_english_words",
            lambda: {"harvest", "forecast"},
        )
        result = _fetch_pronouncing("contrast")
        assert result == ["harvest", "forecast"]
        assert "bartoli" not in result

    def test_falls_back_to_unfiltered_when_filtering_would_empty_result(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Every candidate is a proper noun — filtering to nothing would lose
        # rhyme coverage entirely, so the raw CMUdict list wins instead.
        fake_pronouncing = MagicMock()
        fake_pronouncing.rhymes.return_value = ["bartoli", "anatoli"]
        monkeypatch.setitem(sys.modules, "pronouncing", fake_pronouncing)
        monkeypatch.setattr(
            "poesia.generation.rhyme_fetcher._load_common_english_words",
            lambda: {"harvest"},
        )
        result = _fetch_pronouncing("boli")
        assert result == ["bartoli", "anatoli"]

    def test_falls_back_to_unfiltered_when_wordlist_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_pronouncing = MagicMock()
        fake_pronouncing.rhymes.return_value = ["bartoli", "harvest"]
        monkeypatch.setitem(sys.modules, "pronouncing", fake_pronouncing)
        monkeypatch.setattr(
            "poesia.generation.rhyme_fetcher._load_common_english_words",
            lambda: None,
        )
        result = _fetch_pronouncing("something")
        assert result == ["bartoli", "harvest"]

    def test_returns_empty_on_pronouncing_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_pronouncing = MagicMock()
        fake_pronouncing.rhymes.side_effect = RuntimeError("boom")
        monkeypatch.setitem(sys.modules, "pronouncing", fake_pronouncing)
        assert _fetch_pronouncing("anything") == []


class TestFetchDatamuse:
    def test_parses_response(self) -> None:
        mock = MagicMock()
        mock.read.return_value = json.dumps(
            [
                {"word": "moon", "score": 100},
                {"word": "tune", "score": 90},
            ]
        ).encode("utf-8")
        mock.__enter__ = MagicMock(return_value=mock)
        mock.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock):
            result = _fetch_datamuse("june")

        assert result == ["moon", "tune"]

    def test_returns_empty_on_network_error(self) -> None:
        with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
            result = _fetch_datamuse("luna")
        assert result == []

    def test_returns_empty_on_bad_json(self) -> None:
        mock = MagicMock()
        mock.read.return_value = b"not json"
        mock.__enter__ = MagicMock(return_value=mock)
        mock.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock):
            result = _fetch_datamuse("word")
        assert result == []


class TestFetchRhymeWords:
    def _mock_datamuse(self, words: list[str]) -> MagicMock:
        mock = MagicMock()
        mock.read.return_value = json.dumps([{"word": w} for w in words]).encode("utf-8")
        mock.__enter__ = MagicMock(return_value=mock)
        mock.__exit__ = MagicMock(return_value=False)
        return mock

    def test_deduplicates_results(self) -> None:
        with patch(
            "urllib.request.urlopen", return_value=self._mock_datamuse(["amor", "amor", "calor"])
        ):
            result = fetch_rhyme_words("fervor", language="es")
        assert result.count("amor") == 1

    def test_excludes_anchor_word(self) -> None:
        with patch("urllib.request.urlopen", return_value=self._mock_datamuse(["fervor", "amor"])):
            result = fetch_rhyme_words("fervor", language="es")
        assert "fervor" not in result

    def test_respects_max_results(self) -> None:
        many = [f"word{i}" for i in range(50)]
        with patch("urllib.request.urlopen", return_value=self._mock_datamuse(many)):
            result = fetch_rhyme_words("test", language="en", max_results=5)
        assert len(result) <= 5

    def test_es_falls_back_to_suffix_when_datamuse_empty(self) -> None:
        with patch("urllib.request.urlopen", return_value=self._mock_datamuse([])):
            result = fetch_rhyme_words("oscura", language="es")
        # Should have found suffix-match words from local list
        assert len(result) > 0
        assert all(w.endswith("ura") for w in result)

    def test_returns_empty_on_total_failure(self) -> None:
        with patch("urllib.request.urlopen", side_effect=OSError):
            result = fetch_rhyme_words("xyz", language="nl")
        assert isinstance(result, list)
