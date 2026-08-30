"""Unit tests for candidate cleaning (prompt-echo artifacts + repeats)."""

from __future__ import annotations

from poesia.generation.constrained_loop import _clean_candidate, _clean_candidates


def test_strips_leading_numbering() -> None:
    cleaned = _clean_candidate("3. a la canción que te despierta el viento,")
    assert cleaned == "a la canción que te despierta el viento,"
    assert _clean_candidate("13: Es mole y canaria el mole acompañe") == (
        "Es mole y canaria el mole acompañe"
    )


def test_strips_echo_prefixes() -> None:
    assert (
        _clean_candidate("AE ánimo, muchacho, que te mueves,") == "ánimo, muchacho, que te mueves,"
    )
    assert _clean_candidate("FLO a la canción que te despierta el viento,") == (
        "a la canción que te despierta el viento,"
    )
    assert _clean_candidate("Line content: mueves el aire y el mar") == "mueves el aire y el mar"


def test_lowercases_all_caps_echo_token() -> None:
    assert (
        _clean_candidate("MUEVE mole, que te diera el hervor")
        == "mueve mole, que te diera el hervor"
    )
    assert _clean_candidate("MOMENTO que anima tu voluntad") == "momento que anima tu voluntad"


def test_deduplicates_against_prior_and_within_batch() -> None:
    prior = ["mueve mole, que te diera el hervor"]
    cands = [
        "MUEVE mole, que te diera el hervor",  # repeat of a committed line
        "a la canción que te despierta el viento,",
        "a la canción que te despierta el viento,",  # in-batch repeat
        "AE ánimo, muchacho, que te mueves,",
    ]
    assert _clean_candidates(cands, prior) == [
        "a la canción que te despierta el viento,",
        "ánimo, muchacho, que te mueves,",
    ]


def test_fail_open_when_everything_cleaned() -> None:
    cands = ["3. ", "7.", ""]
    assert _clean_candidates(cands, []) == cands


def test_repair_description_includes_targets() -> None:
    from poesia.generation.constrained_loop import _repair_defect_description

    desc = _repair_defect_description(
        actual_syllables=13, target_syllables=11, target_rhyme_key=None
    )
    assert "13" in desc
    assert "exactly 11" in desc

    desc2 = _repair_defect_description(
        actual_syllables=9, target_syllables=11, target_rhyme_key="ento"
    )
    assert "exactly 11" in desc2
    assert "rhyme key 'ento'" in desc2


def test_strips_trailing_rhyme_scheme_letter() -> None:
    """Draft prompts embed the scheme literally ("Rhyme scheme: ABBA...") and the
    model sometimes echoes its own letter back at the end of a line."""
    assert _clean_candidate("la niebla sube a los jardines, (B)") == (
        "la niebla sube a los jardines,"
    )
    assert _clean_candidate("iluminando el mudo acorazón (A)") == ("iluminando el mudo acorazón")
    assert _clean_candidate("es el nido que busca el destierro (a)") == (
        "es el nido que busca el destierro"
    )
    assert _clean_candidate("acorazón **(A)**") == "acorazón"


def test_preserves_real_parentheticals() -> None:
    """Only a single bare letter in parens is an echo artifact; real asides
    (longer, or containing words) must survive untouched."""
    assert _clean_candidate("un verso normal (risas)") == "un verso normal (risas)"
    assert _clean_candidate("otro verso (o eso creía)") == "otro verso (o eso creía)"
    assert _clean_candidate("la vida es (breve)") == "la vida es (breve)"
