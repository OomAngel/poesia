"""French phonology / scansion backend (pure Python, no dependencies).

French metre counts every pronounced vowel up to the last stressed one; a final mute *e*
after it (rime féminine) is not counted. Rules implemented (classical prosody):

- Vowel units: digraphs and trigraphs are one sound (*eau*, *ou*, *ai*, *ei*, *oi*, *au*,
  *eu*, *œu*); *u* after *q* (and after *g* before e/i) is silent; *y* between vowels is a
  vowel plus a glide (*voyage* = voi-ya-ge); *il(l)* after a vowel is a glide (*soleil*).
- Mute *e*: a final *-e* counts before a consonant, is elided before a vowel or mute *h*,
  and does not count at the end of the line. Final *-es* and the verb ending *-ent* count
  before any word (the consonant blocks elision) except at the line end. An *e* after a
  vowel (*vie*, *joies*, *aient*, *dévouement*) is silent.
- Diérèse and synérèse: *i*, *u*, *ou* before another vowel. After a consonant + l/r they
  stay apart (*pri-er*, *ou-bli-er*); *ou* + vowel and *u* + vowel apart (*jou-er*,
  *tu-er*) except *ui* and *oui*; *-ion*, *-ia*, *-io*, *-ieux* apart (*na-ti-on*,
  *di-a-ble*, *glo-ri-eux*) with common exceptions (*dieu*, *cieux*, *mieux*); *ie* + other
  (*bien*, *pitié*, *lumière*, *ciel*) together.
- Aspirated *h* (*le héros*) blocks elision.

Checked against the 72,412 metre-annotated verses of Métrique en Ligne (Averell corpus 9):
see ``scripts/check_french_scansion.py``.
"""

from __future__ import annotations

import functools
import re
import unicodedata
from importlib import resources

from poesia.phonology.base import RhymeKey, ScanResult, Stress

VOWEL_LETTERS = set("aeiouyàâäéèêëîïôöùûüœæ")
_LIQUID_CLUSTER = re.compile(r"(?:[bcdfgkptv][lr])$")
_UNITS = (
    "eau",
    "œu",
    "oeu",
    "aî",
    "au",
    "ai",
    "ei",
    "oî",
    "oi",
    "où",
    "oû",
    "ou",
    "eû",
    "eu",
    "œ",
    "æ",
)
# Words whose ieu/ien keep one syllable although the general rule splits them.
_IEU_TOGETHER = {
    "dieu",
    "dieux",
    "adieu",
    "adieux",
    "cieux",
    "lieu",
    "lieux",
    "milieu",
    "milieux",
    "mieux",
    "vieux",
    "essieu",
    "épieu",
    "monsieur",
    "messieurs",
    "pieu",
    "plusieurs",
}
# -ien words with diérèse (li-en, an-ci-en, chré-ti-en); others keep one syllable (bien, rien).
_IEN_APART = {
    "lien",
    "liens",
    "chrétien",
    "chrétiens",
    "chrétienne",
    "chrétiennes",
    "gardien",
    "gardiens",
    "gardienne",
    "aérien",
    "aériens",
    "aérienne",
    "aériennes",
    "indien",
    "indiens",
    "indienne",
    "comédien",
    "comédiens",
    "historien",
    "historiens",
}
_ASPIRATED_H = {
    "hache",
    "haie",
    "haies",
    "haillon",
    "haillons",
    "haine",
    "haines",
    "haïr",
    "hais",
    "hait",
    "haïssent",
    "hâle",
    "haleter",
    "halte",
    "hamac",
    "hameau",
    "hameaux",
    "hanche",
    "hanches",
    "hangar",
    "hanter",
    "hante",
    "hantent",
    "happer",
    "harangue",
    "harceler",
    "hardi",
    "hardie",
    "hardis",
    "hardiesse",
    "hareng",
    "hargne",
    "haricot",
    "harnais",
    "harpe",
    "harpes",
    "hasard",
    "hasards",
    "hâte",
    "hâter",
    "hausser",
    "haut",
    "haute",
    "hautes",
    "hauts",
    "hauteur",
    "hauteurs",
    "hautain",
    "hennir",
    "hérisser",
    "hérisson",
    "héros",
    "héron",
    "hêtre",
    "hêtres",
    "heurt",
    "heurter",
    "heurte",
    "hibou",
    "hiboux",
    "hideux",
    "hideuse",
    "hiérarchie",
    "hisser",
    "hocher",
    "homard",
    "honte",
    "hontes",
    "honteux",
    "honteuse",
    "hoquet",
    "horde",
    "hordes",
    "hors",
    "houle",
    "houles",
    "housse",
    "huit",
    "huée",
    "huées",
    "huer",
    "hurler",
    "hurle",
    "hurlent",
    "hurlement",
    "hurlements",
    "hutte",
    "huttes",
    "hublot",
    "hune",
    "huppe",
    "hamecon",
    "hallebarde",
    "halle",
}
_ASPIRATED_H_STEMS = (
    "hach",
    "haill",
    "hain",
    "haï",
    "halet",
    "hant",
    "harc",
    "hard",
    "harn",
    "hasard",
    "hauss",
    "haut",
    "henn",
    "hériss",
    "heurt",
    "hibou",
    "hiss",
    "hoch",
    "hont",
    "hoquet",
    "hors",
    "houl",
    "hurl",
    "hutt",
    "hideu",
)
# -ien(s)/-ienne(s) with one syllable: possessives, bien/rien, venir/tenir forms, ancien.
_IEN_TOGETHER = re.compile(
    r"^(bien|biens|rien|riens|chien|chiens|chienne|chiennes|combien|mien|miens|mienne|miennes|"
    r"tien|tiens|tienne|tiennes|sien|siens|sienne|siennes|ancien|anciens|ancienne|anciennes)$"
    r"|[vt]ien(s|t|nent|ne|nes)?$"
)
_ELIDED = re.compile(r"^(?:[ldjmtnsc]|qu|jusqu|lorsqu|puisqu|quoiqu|presqu)'")


def _plain(ch: str) -> str:
    return unicodedata.normalize("NFD", ch)[0]


@functools.cache
def _lexicon() -> dict[str, str]:
    """Word classes from Wiktionary (data/fr_words.tsv): word -> flags.

    ``v`` verb form ending in silent -ent (*chantent*), ``n`` an -ent word that is
    pronounced (*souvent*), ``d`` an infinitive in -ier with diérèse (*oublier*),
    ``h`` aspirated h. Built by scripts/build_french_lexicon.py; empty if absent.
    """
    try:
        text = resources.files("poesia.phonology").joinpath("data/fr_words.tsv").read_text("utf-8")
    except (FileNotFoundError, OSError):
        return {}
    out = {}
    for line in text.splitlines():
        if line and not line.startswith("#"):
            word, flags = line.split("\t")
            out[word] = flags
    return out


def _word(token: str) -> str:
    token = token.lower().replace("’", "'")
    return "".join(c for c in token if c.isalpha() or c == "'").strip("'")


def _tokens(line: str) -> list[str]:
    """Words of a line; hyphens separate (*ici-bas*), an elided article stays with its
    word with the apostrophe (*l'âme*, *qu'il*); see _key for lexicon lookups."""
    raw = re.split(r"[\s\-–—]+", line)
    return [w for w in (_word(t) for t in raw) if w]


def _key(word: str) -> str:
    """Lexicon form: the word after an elided article (s'empoisonnent -> empoisonnent)."""
    return word.split("'")[-1]


def _flags(word: str) -> str:
    return _lexicon().get(_key(word), "")


def _starts_vowel(word: str) -> bool:
    if not word:
        return False
    word = word.replace("'", "")
    if word[0] == "h":
        if word in _ASPIRATED_H or word.startswith(_ASPIRATED_H_STEMS) or "h" in _flags(word):
            return False
        return len(word) > 1 and word[1] in VOWEL_LETTERS
    if word[0] == "y" and len(word) > 1 and word[1] in VOWEL_LETTERS:
        return False  # yeux, yeuse: y is a consonant here
    return word[0] in VOWEL_LETTERS


def _prepare(word: str) -> str:
    """Spelling to vowel-relevant form: silent u after q/g, y between vowels."""
    w = re.sub(r"(^|')y(?=[aeiouéèê])", r"\1j", word)  # yeux, d'yeux: consonant y
    w = w.replace("'", "")
    w = re.sub(r"q(u)", "q", w)
    w = re.sub(r"(?<!ai)gu(?=[aoâ])", "g", w)  # narguant, fatiguons (not aiguille)
    w = re.sub(r"^([pft])aon", r"\1an", w)  # paon, faon, taon: one vowel
    w = re.sub(r"oe(?=ll)|oê", "oi", w)  # moelle, poêle
    w = re.sub(r"(?<=[cg])ue(?=il)", "œ", w)  # cueillir, écueil, orgueil
    w = re.sub(r"g(u)(?=[eéèêiîy])", "g", w)
    w = re.sub(r"(?<=[aou])y(?=[aeiouéèê])", "ij", w)  # voyage -> voijage, payer -> paijer
    w = re.sub(r"(?<=[aeiouéèêœ])y(?=[aeiouéèê])", "j", w)
    w = re.sub(r"(?<=[gcj])e(?=[aoâôuû])", "", w)  # nageaient, mangeons, Jean: e only softens
    w = w.replace("seoi", "soi")  # asseoir, surseoir
    w = re.sub(r"(?<=[aeouéèêœ])ill", "lj", w)  # feuille, paille: glide
    w = re.sub(r"(?<=[aeouéèêœ])il(?=s?$)", "lj", w)  # soleil, travail, œil, écueils
    return w


def _units(word: str) -> list[tuple[str, int]]:
    """Vowel units with their start index in ``word`` (after _prepare)."""
    units = []
    i = 0
    while i < len(word):
        if word[i] not in VOWEL_LETTERS:
            i += 1
            continue
        for u in _UNITS:
            if word.startswith(u, i) and not any(c in "ëïü" for c in word[i + 1 : i + len(u)]):
                units.append((u, i))
                i += len(u)
                break
        else:
            units.append((word[i], i))
            i += 1
    return units


def _mute_final(word: str, units: list[tuple[str, int]], flags: str = "") -> bool:
    """True when the last unit is a final mute e (-e, -es, verb -ent); never the only vowel
    (le, les, de, que: their e is pronounced, and elision is written)."""
    if len(units) < 2:
        return False
    u, pos = units[-1]
    if u != "e":
        return False
    tail = word[pos:]
    if tail in ("e", "es"):
        return True
    if tail == "ent":
        if "n" in flags:
            return False
        if "v" in flags:
            return True
        # Unknown word: silent after a vowel (aient, voient, crient), else pronounced (vent).
        if re.search(r"[vt]ient$", word):
            return False  # vient, tient, revient: venir/tenir, not a plural
        return len(units) > 1 and units[-2][1] + len(units[-2][0]) == pos
    return False


def _apart_i(word: str, rest: str, key: str, flags: str) -> bool:
    """Diérèse for i before a vowel."""
    if rest.startswith("eu"):
        if key in _IEU_TOGETHER:
            return False
        return rest.startswith(("eux", "euse")) or bool(re.search(r"érieur", word))  # glo-ri-eux
    if rest.startswith(("on", "a", "o")):
        return True  # na-ti-on, di-a-ble, vi-o-lon
    if rest.startswith("é") and len(rest) > 1 and not re.fullmatch(r"ée?s?", rest):
        return True  # pi-é-té, va-ri-é-té, qui-é-tude (but pi-tié, a-mi-tiés)
    if rest.startswith("enc") or re.search(r"tiel(le)?s?$", word):
        return True  # sci-ence, cons-ci-ence, pro-vi-den-ti-el
    if rest.startswith("en") and (key in _IEN_APART or "n" in flags):
        return True  # li-en, chré-ti-en; pa-ti-ent, o-ri-ent (pronounced -ent)
    if re.search(r"ien(s|ne|nes)?$", word) and not _IEN_TOGETHER.search(key):
        return True  # quo-ti-di-en, bo-hé-mi-en, mu-si-ci-en
    return False  # bien, pitié, lumière, ciel, premier


def _apart(word: str, units: list[tuple[str, int]], k: int, key: str = "") -> bool:
    """Diérèse: does unit k (i, u, ou) keep its own syllable before unit k + 1?"""
    u, pos = units[k]
    rest = word[units[k + 1][1] :]
    if u not in ("i", "u", "ou"):
        return u != "ï"  # two full vowels: hiatus (thé-â-tre); ï + vowel a glide (aï-eul)
    key = key or word
    flags = _lexicon().get(key, "")
    if "d" in flags or "s" in flags:
        return "d" in flags  # ou-bli-er, en-vi-ez (-ier verbs) / é-tions, sa-vions
    if _LIQUID_CLUSTER.search(word[:pos]) and not (u == "u" and rest.startswith("i")):
        return True  # pri-er, ou-bli-er, cri-ant (but bruit, truite)
    if u == "u":
        return bool(re.search(r"ruin", word)) or not rest.startswith("i")  # ru-i-ne; nuit; tu-er
    if u == "ou":
        return key not in ("oui", "ouis")  # jou-er, jou-ir, é-pa-nou-i; only oui together
    return _apart_i(word, rest, key, flags)


def _syllables(word: str, *, line_end: bool, before_vowel: bool) -> tuple[int, int]:
    """(counted syllables, index of the stressed one counted from the start) for one word."""
    w = _prepare(word)
    units = _units(w)
    if not units:
        return 0, -1
    key = _key(word)
    flags = _lexicon().get(key, "")
    mute = _mute_final(w, units, flags)
    nuclei = []
    k = 0
    while k < len(units):
        u, pos = units[k]
        if mute and k == len(units) - 1:
            break
        if (
            u == "e"
            and k > 0
            and pos == units[k - 1][1] + len(units[k - 1][0])
            and re.match(r"[^aeiouyàâäéèêëîïôöùûüœæ][aeiouyàâäéèêëîïôöùûüœæ]", w[pos + 1 : pos + 3])
        ):
            # mute e after a vowel inside the word: dévouement, gaieté, enviera (not crier, ciel)
            k += 1
            continue
        if k + 1 < len(units) and units[k + 1][1] == pos + len(u):
            nxt_is_mute = mute and k + 1 == len(units) - 1
            if not nxt_is_mute and not _apart(w, units, k, key):
                nuclei.append(u)
                k += 2  # glide + vowel = one syllable
                continue
        nuclei.append(u)
        k += 1
    count = len(nuclei)
    stressed = count - 1
    if mute:
        last_u, last_pos = units[-1]
        after_vowel = len(units) > 1 and units[-2][1] + len(units[-2][0]) == last_pos
        if not (line_end or after_vowel or (before_vowel and w[last_pos:] == "e")):
            count += 1  # mute e pronounced
    return count, stressed


_V = "aeiouyàâäéèêëîïôöùûüœæ"
_PRONOUNCED_FINAL = set("crfl")  # "CaReFuL": final consonants heard in masculine words
_ER_HEARD = {
    "mer",
    "fer",
    "cher",
    "chair",
    "hier",
    "fier",
    "hiver",
    "enfer",
    "amer",
    "éther",
    "ver",
    "vers",
    "cancer",
    "jupiter",
    "lucifer",
    "outremer",
    "univers",
    "travers",
    "envers",
    "revers",
    "pervers",
    "divers",
    "tiers",
}
_VOWEL_SOUNDS = (  # longest spelling first; nasals only when no vowel follows the n/m
    ("eau", "o"),
    ("oin", "wɛ̃"),
    ("ain", "ɛ̃"),
    ("aim", "ɛ̃"),
    ("ein", "ɛ̃"),
    ("œu", "ø"),
    ("aî", "ɛ"),
    ("ai", "ɛ"),
    ("ei", "ɛ"),
    ("au", "o"),
    ("oî", "wa"),
    ("oi", "wa"),
    ("oû", "u"),
    ("où", "u"),
    ("ou", "u"),
    ("eû", "ø"),
    ("eu", "ø"),
    ("an", "ɑ̃"),
    ("am", "ɑ̃"),
    ("en", "ɑ̃"),
    ("em", "ɑ̃"),
    ("in", "ɛ̃"),
    ("im", "ɛ̃"),
    ("yn", "ɛ̃"),
    ("ym", "ɛ̃"),
    ("on", "ɔ̃"),
    ("om", "ɔ̃"),
    ("un", "ɛ̃"),
    ("um", "ɛ̃"),
    ("œ", "ø"),
    ("é", "e"),
    ("è", "ɛ"),
    ("ê", "ɛ"),
    ("ë", "ɛ"),
    ("e", "ɛ"),
    ("a", "a"),
    ("â", "a"),
    ("à", "a"),
    ("o", "o"),
    ("ô", "o"),
    ("u", "y"),
    ("û", "y"),
    ("ù", "y"),
    ("i", "i"),
    ("î", "i"),
    ("ï", "i"),
    ("y", "i"),
)
_CONSONANT_SOUNDS = (
    ("gn", "ɲ"),
    ("ch", "ʃ"),
    ("ph", "f"),
    ("th", "t"),
    ("qu", "k"),
    ("q", "k"),
    ("ç", "s"),
    ("j", "ʒ"),
    ("x", "ks"),
    ("h", ""),
    ("w", "w"),
)


def _coda_sound(letters: str, feminine: bool = False, nasal: bool = False) -> str:
    """Pronounced consonants after the vowel (letters already exclude silent endings).
    ``J`` marks a glide (soleil, feuille)."""
    if feminine and letters == "s" and not nasal:
        return "z"  # rose, chose: s between vowels (not pense, not tresse)
    if feminine:
        letters += "e"  # the mute e still softens c and g: commence, héritage
    out = ""
    i = 0
    letters = re.sub(r"(.)\1", r"\1", letters)  # belle -> bele, terre -> tere, tresse -> trese
    while i < len(letters):
        for spell, snd in _CONSONANT_SOUNDS:
            if letters.startswith(spell, i):
                out += snd
                i += len(spell)
                break
        else:
            c = letters[i]
            nxt = letters[i + 1] if i + 1 < len(letters) else ""
            if c == "c":
                out += "s" if nxt in ("e", "i", "y") else "k"
            elif c == "g":
                out += "ʒ" if nxt in ("e", "i", "y") else "g"
            elif c == "J":
                out += "j"
            elif c == "G":
                out += "g"
            elif c not in _V:
                out += c
            i += 1
    return out


_E_FINAL_MONOSYLLABLES = ("les", "des", "mes", "tes", "ses", "ces", "nez", "chez", "pied", "clef")


def _rhyme_spelling(key: str) -> str:
    """Spelling with silent or hard letters marked: qu -> q, hard gu -> G, cueille -> cœille."""
    w = re.sub(r"q(u)", "q", key)
    w = re.sub(r"(?<=[cg])ue(?=il)", "œ", w)  # cueille, orgueil
    w = re.sub(r"(?<!ai)gu(?=[eéèêiîaoâ])", "G", w)  # hard g: bague, prodigue, narguant
    return re.sub(r"^femme", "famme", w)


def _is_feminine(w: str, flags: str, units: list[tuple[str, int]]) -> bool:
    """A final mute e (-e, -es, silent verb -ent) after another vowel sound."""
    if len(units) < 2:
        return False
    if re.search(r"es?$", w):
        return True
    if not w.endswith("ent"):
        return False
    if "v" in flags:
        return True
    return not flags and bool(re.search(r"[aeiouy]ent$", w)) and not re.search(r"[vt]ient$", w)


def _masculine_stem(stem: str, units: list[tuple[str, int]]) -> tuple[str, tuple[str, str] | None]:
    """Drop silent final consonants; some endings are answered directly (premier -> e)."""
    if stem in _ER_HEARD:
        return stem, ("ɛ", "r")
    if re.search(r"[^aeiouy]ier?s?$", stem) or re.search(r"(er|ez|ers|ed|eds)$", stem):
        if len(units) > 1 or stem in _E_FINAL_MONOSYLLABLES:
            return stem, ("e", "")  # premier, aimer, chez, pied
    if re.search(r"ets?$", stem):
        return stem, ("ɛ", "")  # secret, jouet
    while stem and stem[-1] in "sxzt dpg" and len(stem) > 1:
        stem = stem[:-1]  # silent final consonants
    if re.search(r"[nr]c$", stem):
        stem = stem[:-1]  # blanc, porc
    if stem and stem[-1] not in _V and stem[-1] not in _PRONOUNCED_FINAL and stem[-1] not in "mn":
        stem = stem[:-1]
    return stem, None


def _glide_stem(stem: str, key: str) -> str:
    """-il/-ill after a vowel and -ill after a consonant are the glide j (J)."""
    if re.search(r"vill$", stem) or key in ("mille", "milles", "tranquille", "tranquilles"):
        return stem
    stem = re.sub(r"(?<=[aeuéèêœ])ill?$", "J", stem)  # paille, feuille, soleil (not voile)
    return re.sub(r"(?<=[^aeiouyéèêœ])ill$", "iJ", stem)  # fille, famille (not ville, mille)


def _nasal_blocked(stem: str, end: int, feminine: bool) -> bool:
    """A vowel + n/m is not nasal before a vowel, a second n/m or the mute e (bonne, aime)."""
    if end < len(stem):
        return stem[end] in _V or stem[end] in "nm"
    return feminine


def _last_vowel(stem: str, feminine: bool) -> tuple[int, str, str] | None:
    """(index, spelling, sound) of the last vowel spelling in the stem, longest spelling wins."""
    best = None
    for i in range(len(stem) - 1, -1, -1):
        for spell, snd in _VOWEL_SOUNDS:
            if not stem.startswith(spell, i):
                continue
            end = i + len(spell)
            if snd.endswith("\u0303") and _nasal_blocked(stem, end, feminine):
                continue
            if spell[-1] in "nm" and end < len(stem) and stem[end] in _V:
                continue
            best = (i, spell, snd)
            break
        if best:
            break
    if best is None or best[0] == 0:
        return best
    i, spell, snd = best
    for spell2, snd2 in _VOWEL_SOUNDS:  # the "u" of "ou": take the longest spelling ending there
        j = i + len(spell) - len(spell2)
        if j >= 0 and len(spell2) > len(spell) and stem.startswith(spell2, j):
            if snd2.endswith("\u0303") and _nasal_blocked(stem, j + len(spell2), feminine):
                continue
            return j, spell2, snd2
    return best


def _ending_sound(word: str) -> tuple[str, str]:
    """(vowel, coda) of a word's last pronounced syllable, a feminine ending marked by "ə"."""
    key = _key(word)
    w = _rhyme_spelling(key)
    flags = _lexicon().get(key, "")
    feminine = _is_feminine(w, flags, _units(_prepare(key)))
    if feminine:
        stem, fem_mark = re.sub(r"(es?|ent)$", "", w), "ə"
    else:
        stem, direct = _masculine_stem(w, _units(_prepare(key)))
        if direct:
            return direct
        fem_mark = ""
    stem = _glide_stem(stem, key)
    found = _last_vowel(stem, feminine)
    if found is None:
        return "", _coda_sound(stem) + fem_mark
    i, spell, snd = found
    after = stem[i + len(spell) :]
    if snd == "ɑ̃" and spell.startswith("en") and i > 0 and stem[i - 1] in "iyé":
        if not after and not feminine and "n" not in flags:
            snd = "ɛ̃"  # bien, vient, européen (not science, orient)
    coda = _coda_sound(after, feminine, nasal=snd.endswith("\u0303"))
    if snd == "ɛ" and spell == "e" and not coda:
        snd = "ə"
    return snd, coda + fem_mark


class FrenchPhonology:
    """Scans French verse lines (pure Python)."""

    def scan_line(self, line: str) -> ScanResult:
        words = _tokens(line)
        if not words:
            return ScanResult(line=line, metrical_syllable_count=0, is_valid=False)
        positions: list[Stress] = []
        for wi, word in enumerate(words):
            last = wi == len(words) - 1
            nxt = words[wi + 1] if not last else ""
            count, stressed = _syllables(word, line_end=last, before_vowel=_starts_vowel(nxt))
            marks = [Stress.UNSTRESSED] * count
            if count and stressed >= 0 and (count > 1 or last):
                marks[min(stressed, count - 1)] = Stress.PRIMARY
            positions.extend(marks)
        return ScanResult(
            line=line,
            metrical_syllable_count=len(positions),
            stress_pattern=tuple(positions),
            is_valid=bool(positions),
        )

    def rhyme_key(self, line: str) -> RhymeKey:
        """The sound of the line ending: last pronounced vowel plus the consonants heard after
        it (*mystère* / *solitaire* -> ``ɛr``, *temps* / *sang* -> ``ɑ̃``). ``assonant`` is the
        vowel alone."""
        words = _tokens(line)
        if not words:
            return RhymeKey(consonant="", assonant="")
        vowel, coda = _ending_sound(words[-1])
        return RhymeKey(consonant=vowel + coda, assonant=vowel)

    def classify_stanza(self, lines: list[str]) -> str | None:
        return {14: "sonnet", 4: "quatrain", 3: "tercet"}.get(len(lines))
