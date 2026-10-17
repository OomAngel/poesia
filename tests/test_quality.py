"""Shared poem-quality layer (poesia.quality)."""

from __future__ import annotations

import pytest

from poesia.phonology.spanish import SpanishPhonology
from poesia.quality import diversity, gates, rank, repair
from poesia.quality.gates import Defect, LineContext

pytest.importorskip("fonemas")


@pytest.fixture(scope="module")
def es() -> SpanishPhonology:
    return SpanishPhonology()


def test_metre_gate_uses_licensed_set(es: SpanishPhonology) -> None:
    scan = es.scan_line("Este suave incendio me sustenta")  # best 10; dieresis su-a-ve gives 11
    assert scan.metrical_syllable_count == 10
    assert gates.metre(scan, 11) is None
    assert gates.metre(scan, 8) is Defect.METRE


def test_rhyme_gate(es: SpanishPhonology) -> None:
    assert gates.rhyme("mas Lupita no venía", "buscando a Lupita un día", es) is None
    assert gates.rhyme("la historia", "con alegría", es) is Defect.RHYME
    assert gates.rhyme("en el día", "otro día", es) is Defect.RHYME  # same word
    assert (
        gates.rhyme("la tierra sola", "su casa nueva", es, loose=True) is Defect.RHYME
    )  # o-a vs e-a
    assert gates.rhyme("la luna clara", "una mañana", es, loose=True) is None


def test_line_defects(es: SpanishPhonology) -> None:
    ctx = LineContext(language="es", target=8, others=("Memo la pelota rueda",))
    defects, _ = gates.check_line("Memo sigue marcando gol", ctx, es)
    assert Defect.OPENING in defects
    defects, _ = gates.check_line("La Calaca llega, coche.", LineContext(language="es"), es)
    assert Defect.TACKED in defects
    defects, _ = gates.check_line("y la Muerte llegó con", LineContext(language="es"), es)
    assert Defect.DANGLING in defects
    defects, _ = gates.check_line("Andaba la Calavera", LineContext(language="es", target=8), es)
    assert defects == []


def test_rank_gate_beats_sense_and_absent_is_not_zero() -> None:
    weights = {"theme": 1.0, "fluency": 1.0}
    unrhymed = rank.Candidate("exact but unrhymed", [Defect.RHYME], 0, {"theme": 0.9})
    rhyming = rank.Candidate("rhymes, one syllable off", [], 1, {"theme": 0.2, "fluency": None})
    assert rank.best([unrhymed, rhyming], weights) is rhyming
    assert rhyming.absent() == ["fluency"]
    a = rank.Candidate("a", [], 0, {"theme": 0.5})
    b = rank.Candidate("b", [], 2, {"theme": 0.5})
    assert rank.rank([b, a], weights)[0] is a  # form distance only breaks ties


def test_diversity_measure() -> None:
    d = diversity.measure(["la muerte llega", "la muerte baila", "un gato duerme"])
    assert d.lines == 3 and d.distinct_openings == 2 and d.top_opening_share == pytest.approx(2 / 3)


def test_repair_instruction_offers_words() -> None:
    text = repair.instruction(
        "es",
        "una línea muy muy larga",
        [Defect.METRE, Defect.RHYME],
        count=11,
        target=8,
        rhyme_with="calavera",
        bank=["espera", "fiera"],
    )
    assert "quítale 3" in text and "otra tuya" in text and "exactamente" not in text


def test_poetics_2_near_copy_rhymes(es: SpanishPhonology) -> None:
    assert gates.near_copies("canta", "encanta")
    assert gates.near_copies("cantaba", "cantara")
    assert gates.near_copies("dulcemente", "tristemente")
    assert not gates.near_copies("calavera", "escalera")
    assert not gates.near_copies("día", "respondía")  # a real rhyme, not a prefixed copy
    assert gates.near_copies("hacer", "deshacer")
    assert gates.rhyme("y la gente encanta", "la Muerte canta", es) is Defect.NEAR_COPY_RHYME
    assert gates.rhyme("por pasillo y escalera", "Andaba la Calavera", es) is None


def test_poetics_3_repeated_content_words(es: SpanishPhonology) -> None:
    earlier = ("El inmenso mar de la noche", "y el cielo azul")
    assert gates.repeated_words("con un inmenso dolor", earlier, "es") == ["inmenso"]
    assert (
        gates.repeated_words("y la luna en el camino", earlier, "es") == []
    )  # function words free
    assert (
        gates.repeated_words("Lupita y Lupita", (), "es", frozenset({"lupita"})) == []
    )  # the name
    ctx = LineContext(language="es", earlier=earlier)
    defects, _ = gates.check_line("con un inmenso dolor", ctx, es)
    assert Defect.REPEATED_WORD in defects
