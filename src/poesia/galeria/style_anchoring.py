"""Style anchoring for image generation based on poetic influences.

Phase 4C: Uses influence profiles to generate appropriate visual style keywords
for image backends. Maps literary movements, tones, and eras to visual styles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from poesia.memoria.records import InfluenceRecord

# Movement -> visual style mapping
MOVEMENT_STYLES: dict[str, list[str]] = {
    # Spanish/Latin American
    "Generación del 98": ["austere landscape", "Castilian plateau", "muted earth tones"],
    "Generación del 27": ["surrealist", "Andalusian", "dramatic shadows"],
    "Modernismo": ["art nouveau", "ornate", "jewel tones", "exotic"],
    "Post-Modernismo": ["intimate", "domestic scenes", "soft lighting"],
    "Romanticismo": ["dramatic", "moonlit", "passionate", "nature sublime"],
    "Post-Romanticismo": ["dreamy", "soft focus", "intimate scenes"],
    "Baroque": ["rich textures", "chiaroscuro", "ornate details", "religious iconography"],
    "Siglo de Oro": ["rich textures", "chiaroscuro", "ornate details"],
    # Surrealism
    "Surrealism": ["dreamlike", "impossible geometry", "Dalí-esque", "metamorphosis"],
    "Contemporáneos": ["modernist", "geometric", "Mexican muralism influences"],
    # English
    "Romanticism": ["Turner-esque", "sublime nature", "dramatic skies", "ruins"],
    "Victorian": ["Pre-Raphaelite", "detailed nature", "moral allegory"],
    "Georgian": ["pastoral", "English countryside", "nostalgic"],
    "American Transcendentalism": ["vast landscapes", "luminism", "Hudson River School"],
    "American Modernism": ["rural New England", "stark", "Wyeth-esque"],
    # Dutch
    "Tachtigers": ["Dutch Golden Age revival", "sensory", "individualist"],
    "Forum-generatie": ["autumnal", "Dutch landscape", "melancholic"],
    "Expressionisme": ["bold colors", "dynamic", "cosmic scale"],
    "Vitalism": ["energy", "movement", "life force"],
}

# Tone -> visual mood mapping
TONE_MOODS: dict[str, list[str]] = {
    "melancholic": ["muted colors", "twilight", "solitary figure"],
    "meditative": ["still water", "contemplative", "sparse composition"],
    "austere": ["minimal", "stark", "clean lines"],
    "spare": ["minimalist", "negative space", "restraint"],
    "sensual": ["warm colors", "soft textures", "intimate"],
    "earthy": ["natural materials", "brown and green palette", "organic"],
    "passionate": ["red accents", "dynamic composition", "intensity"],
    "tragic": ["dark shadows", "dramatic lighting", "pathos"],
    "surreal": ["dreamlike", "impossible perspectives", "symbolic"],
    "intimate": ["close-up", "warm lighting", "personal space"],
    "nostalgic": ["sepia undertones", "soft focus", "memory-like"],
    "cosmic": ["vast scale", "starfields", "infinite depth"],
    "elemental": ["raw nature", "water fire earth air", "primal"],
    "pastoral": ["countryside", "gentle light", "bucolic"],
    "duende": ["flamenco shadows", "Spanish soul", "dark passion"],
    "musical": ["flowing lines", "rhythm in composition", "harmony"],
}


def style_from_influences(
    influences: list[InfluenceRecord],
    max_keywords: int = 8,
) -> str:
    """Generate visual style string from matched influences.

    Args:
        influences: List of matched influence records
        max_keywords: Maximum number of style keywords to include

    Returns:
        Comma-separated style string for image generation prompt
    """
    keywords: list[str] = []

    for inf in influences:
        # Add movement-based styles
        if inf.movement:
            # Handle multi-part movements like "Surrealism → Political → Late simplicity"
            for mov_part in inf.movement.split("→"):
                mov = mov_part.strip()
                if mov in MOVEMENT_STYLES:
                    keywords.extend(MOVEMENT_STYLES[mov][:2])

        # Add tone-based moods
        for tone in inf.tone:
            if tone.lower() in TONE_MOODS:
                keywords.extend(TONE_MOODS[tone.lower()][:1])

    # Deduplicate while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)
            if len(unique_keywords) >= max_keywords:
                break

    return ", ".join(unique_keywords) if unique_keywords else ""


def illustrate_prompt(
    poem_line: str,
    influences: list[InfluenceRecord] | None = None,
    base_style: str = "traditional woodcut line-art",
) -> str:
    """Build an illustration prompt from poem line + influence-derived style.

    Args:
        poem_line: The verse line to illustrate
        influences: Optional list of influences for style derivation
        base_style: Fallback style if no influences match

    Returns:
        Complete prompt for image generation
    """
    style = style_from_influences(influences) if influences else ""
    combined_style = f"{style}, {base_style}" if style else base_style
    return f"{poem_line}, {combined_style}"
