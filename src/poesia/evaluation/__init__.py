"""Scoring and evaluation layer.

Combines phonological validity (hard constraints) with soft-scored qualities
(semantic continuity, novelty, cliché avoidance) into a single ranking score
usable by the generation loop to select among candidate lines.

    S = w_m * S_metre + w_r * S_rhyme + w_t * S_theme + w_n * S_novelty
        - w_c * P_cliche
"""
