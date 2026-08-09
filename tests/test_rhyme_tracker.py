"""Unit tests for RhymeTracker."""

from __future__ import annotations

from unittest.mock import MagicMock

from poesia.generation.rhyme_tracker import RhymeTracker
from poesia.phonology.base import RhymeKey


def _make_phonology(rhyme_map: dict[str, str]) -> MagicMock:
    """Return a mock phonology whose rhyme_key() uses rhyme_map[line]."""
    phon = MagicMock()

    def rhyme_key(line: str) -> RhymeKey:
        key = rhyme_map.get(line, "")
        return RhymeKey(consonant=key, assonant=key)

    phon.rhyme_key.side_effect = rhyme_key
    return phon


class TestRhymeTrackerBasics:
    def test_letter_for_line_simple(self) -> None:
        t = RhymeTracker("ABBA", _make_phonology({}))
        assert t.letter_for_line(0) == "A"
        assert t.letter_for_line(1) == "B"
        assert t.letter_for_line(2) == "B"
        assert t.letter_for_line(3) == "A"

    def test_letter_for_line_with_spaces(self) -> None:
        t = RhymeTracker("ABBA ABBA", _make_phonology({}))
        assert t.letter_for_line(4) == "A"
        assert t.letter_for_line(5) == "B"

    def test_letter_for_free_line(self) -> None:
        t = RhymeTracker("-A-A", _make_phonology({}))
        assert t.letter_for_line(0) is None
        assert t.letter_for_line(1) == "A"

    def test_letter_out_of_range(self) -> None:
        t = RhymeTracker("AB", _make_phonology({}))
        assert t.letter_for_line(99) is None

    def test_is_new_rhyme_and_target_none_before_commit(self) -> None:
        t = RhymeTracker("ABBA", _make_phonology({}))
        assert t.is_new_rhyme(0) is True
        assert t.is_new_rhyme(1) is True
        assert t.target_key_for_line(0) is None
        assert t.example_word_for_line(0) is None


class TestRhymeTrackerCommit:
    def test_commit_records_key(self) -> None:
        phon = _make_phonology({"la noche oscura": "ura"})
        t = RhymeTracker("ABBA", phon)
        t.commit(0, "la noche oscura")
        assert t.committed_keys["A"] == "ura"

    def test_commit_records_example_word(self) -> None:
        phon = _make_phonology({"la noche oscura": "ura"})
        t = RhymeTracker("ABBA", phon)
        t.commit(0, "la noche oscura")
        assert t.example_words["A"] == "oscura"

    def test_commit_strips_trailing_punctuation(self) -> None:
        phon = _make_phonology({"ver el mar,": "ar"})
        t = RhymeTracker("AA", phon)
        t.commit(0, "ver el mar,")
        assert t.example_words["A"] == "mar"

    def test_target_key_after_commit(self) -> None:
        phon = _make_phonology({"la noche oscura": "ura"})
        t = RhymeTracker("ABBA", phon)
        t.commit(0, "la noche oscura")
        assert t.target_key_for_line(3) == "ura"

    def test_example_word_after_commit(self) -> None:
        phon = _make_phonology({"la noche oscura": "ura"})
        t = RhymeTracker("ABBA", phon)
        t.commit(0, "la noche oscura")
        assert t.example_word_for_line(3) == "oscura"

    def test_is_new_rhyme_false_after_commit(self) -> None:
        phon = _make_phonology({"la noche oscura": "ura"})
        t = RhymeTracker("ABBA", phon)
        t.commit(0, "la noche oscura")
        assert t.is_new_rhyme(0) is False
        assert t.is_new_rhyme(3) is False

    def test_second_commit_to_same_letter_is_ignored(self) -> None:
        phon = _make_phonology({"primera oscura": "ura", "segunda dura": "ura"})
        t = RhymeTracker("AA", phon)
        t.commit(0, "primera oscura")
        t.commit(1, "segunda dura")
        assert t.example_words["A"] == "oscura"  # first wins

    def test_free_line_commit_is_ignored(self) -> None:
        phon = _make_phonology({"una línea libre": "ibre"})
        t = RhymeTracker("-A", phon)
        t.commit(0, "una línea libre")
        assert t.committed_keys == {}

    def test_empty_rhyme_key_not_committed(self) -> None:
        phon = _make_phonology({"x": ""})
        t = RhymeTracker("AA", phon)
        t.commit(0, "x")
        assert t.committed_keys == {}


class TestRhymeTrackerSoneto:
    """Simulate the 14-line ABBAABBACDCDCD Petrarchan soneto scheme."""

    SCHEME = "ABBAABBACDCDCD"

    def _make_tracker(self) -> RhymeTracker:
        mapping = {
            "ver el sistema entero y oscura": "ura",  # A
            "buscar el patrón en la interior": "or",  # B
            "seguir el rastro hasta el exterior": "or",
            "canario en la mina que perdura": "ura",
            "construyo solo ante la fractura": "ura",
            "me importa el resultado y el fervor": "or",
            "franqueza que corta sin temor": "or",
            "lo que queda dentro es la hechura": "ura",
            "voy ancho en un collage fecundo": "undo",  # C
            "hacia algo que sostenga y vital": "al",  # D
            "aunque el poder ignore lo profundo": "undo",
            "quiero ideas fuertes eternal": "al",
            "en la amplitud lo más segundo": "undo",
            "servir con alcance y final": "al",
        }
        return RhymeTracker(self.SCHEME, _make_phonology(mapping))

    def test_scheme_letters(self) -> None:
        t = self._make_tracker()
        expected = list("ABBAABBACDCDCD")
        for i, letter in enumerate(expected):
            assert t.letter_for_line(i) == letter, f"line {i}"

    def test_groups_committed_in_sequence(self) -> None:
        lines = [
            "ver el sistema entero y oscura",
            "buscar el patrón en la interior",
            "seguir el rastro hasta el exterior",
            "canario en la mina que perdura",
            "construyo solo ante la fractura",
            "me importa el resultado y el fervor",
            "franqueza que corta sin temor",
            "lo que queda dentro es la hechura",
            "voy ancho en un collage fecundo",
            "hacia algo que sostenga y vital",
            "aunque el poder ignore lo profundo",
            "quiero ideas fuertes eternal",
            "en la amplitud lo más segundo",
            "servir con alcance y final",
        ]
        t = self._make_tracker()
        for i, line in enumerate(lines):
            t.commit(i, line)

        assert t.committed_keys.get("A") == "ura"
        assert t.committed_keys.get("B") == "or"
        assert t.committed_keys.get("C") == "undo"
        assert t.committed_keys.get("D") == "al"

    def test_target_key_returned_for_repeat_letters(self) -> None:
        t = self._make_tracker()
        t.commit(0, "ver el sistema entero y oscura")  # A=ura
        t.commit(1, "buscar el patrón en la interior")  # B=or
        # line 2 is B, should get target=or
        assert t.target_key_for_line(2) == "or"
        # line 3 is A, should get target=ura
        assert t.target_key_for_line(3) == "ura"
