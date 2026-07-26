"""Unit tests for SpanishPhonology rhyme key extraction and stanza classification."""

from __future__ import annotations

from poesia.phonology.spanish import SpanishPhonology


def test_spanish_rhyme_key_consonant_and_assonant() -> None:
    span = SpanishPhonology()
    rkey1 = span.rhyme_key("En la noche oscura de la piedra")
    assert rkey1.consonant == "edra"
    assert rkey1.assonant == "ea"

    rkey2 = span.rhyme_key("Bajo el sol de la ciudad")
    assert rkey2.consonant == "ad"
    assert rkey2.assonant == "a"


def test_spanish_classify_stanza_fallback() -> None:
    span = SpanishPhonology()
    assert span.classify_stanza(["l1", "l2"]) == "pareado"
    assert span.classify_stanza(["l1", "l2", "l3"]) == "terceto"
    assert span.classify_stanza(["l1", "l2", "l3", "l4"]) == "cuarteto / redondilla"
    assert span.classify_stanza(["l1"] * 14) == "soneto"
    assert span.classify_stanza([]) is None
