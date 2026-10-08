"""The page's syllable display: split, stress, and merges across words."""

from __future__ import annotations

from poesia.scansion_view import syllable_view


def _render(line: str, lang: str) -> str:
    out = ""
    for w in syllable_view(line, lang):
        out += "·".join(s["t"].upper() if s["s"] else s["t"] for s in w["syl"])
        out += "‿" if w["join"] else " "
    return out.strip()


def test_spanish_split_stress_and_sinalefa() -> None:
    assert _render("La luna ilumina", "es") == "la LU·na‿i·lu·MI·na"


def test_italian_split_stress_and_sinalefe() -> None:
    assert (
        _render("mi ritrovai per una selva oscura,", "it")
        == "mi ri·tro·VAI per U·na SEL·va‿o·SCU·ra"
    )
    assert _render("Nel mezzo del cammin", "it") == "Nel MEZ·zo del cam·MIN"


def test_english_stress_from_cmudict() -> None:
    assert _render("The restless sea", "en") == "The REST·less SEA"


def test_empty_and_unknown() -> None:
    assert syllable_view("", "es") == []
    assert syllable_view("hola", "nl")[0]["syl"][0]["t"] == "hola"
