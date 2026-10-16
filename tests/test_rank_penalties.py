"""Ranking penalties for repeated content words and reused openings (evaluation/rank_penalties)."""

from __future__ import annotations

from poesia.evaluation.rank_penalties import RankPenalties, content_words, opening_word
from poesia.evaluation.scorer import LineScorer
from poesia.phonology.spanish import SpanishPhonology

PRIOR = ["La luna despierta sobre el viejo mar", "El silencio gira cerca del faro"]


def test_opening_word_is_lowercase_and_unpunctuated() -> None:
    assert opening_word("«Sobre el mar,") == "sobre"
    assert opening_word("   ") is None


def test_content_words_skip_frequent_words() -> None:
    words = content_words("La luna despierta sobre el viejo mar", "es")
    assert {"luna", "despierta", "viejo"} <= words
    assert "la" not in words and "el" not in words and "sobre" not in words


def test_defaults_penalise_nothing() -> None:
    assert RankPenalties().penalty("La luna vuelve al mar", PRIOR, "es") == 0.0


def test_repeat_weight_counts_reused_content_words_up_to_a_cap() -> None:
    pen = RankPenalties(repeat_weight=0.1)
    fresh = pen.penalty("Un pájaro cruza la tarde", PRIOR, "es")
    reused = pen.penalty("Luna y silencio sobre el faro del mar", PRIOR, "es")
    assert fresh == 0.0
    assert reused > fresh
    assert reused <= 0.1 * 4 + 1e-9  # capped at four reused words


def test_opening_weight_looks_at_the_poem_and_at_recent_poems() -> None:
    pen = RankPenalties(opening_weight=0.2, recent_openings={"entre"})
    assert pen.penalty("La noche cae despacio", PRIOR, "es") == 0.2  # "la" opens a prior line
    assert pen.penalty("Entre las ramas duerme el sol", PRIOR, "es") == 0.2  # recent poem
    assert pen.penalty("Bajo la sombra espera el sol", PRIOR, "es") == 0.0


def test_scorer_ranks_the_reusing_candidate_lower_only_when_penalties_are_set() -> None:
    cands = ["La luna despierta sobre el mar", "Bajo la sombra espera un barco"]

    def order(penalties: RankPenalties | None) -> list[str]:
        scorer = LineScorer(SpanishPhonology(), 11, language="es", rank_penalties=penalties)
        return [c.line for c in scorer.score_candidates(cands, prior_lines=PRIOR)]

    penalised = order(RankPenalties(repeat_weight=0.5, opening_weight=0.5))
    assert penalised[0] == "Bajo la sombra espera un barco"
    # no penalties: the score does not depend on them
    plain = LineScorer(SpanishPhonology(), 11, language="es").score_candidates(
        cands, prior_lines=PRIOR
    )
    again = LineScorer(
        SpanishPhonology(), 11, language="es", rank_penalties=RankPenalties()
    ).score_candidates(cands, prior_lines=PRIOR)
    assert [(c.line, c.score) for c in plain] == [(c.line, c.score) for c in again]
