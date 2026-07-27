# Generation Brief Format

_Companion to `ENRICHMENT_ARCHITECTURE.md` — defines the structured prompt assembled before LLM generation._

## Purpose

The generation brief is a **dense, grounded prompt** assembled programmatically by PoesIA from:
- Form specification
- User-provided theme/tone/seeds
- Retrieved personal context (fragments, exemplars)
- Pre-computed rhyme and word expansions
- Influence anchors

The brief replaces vague prompts like "write a sad Spanish sonnet" with rich context that keeps the LLM focused and reduces iteration.

## Brief Template

```markdown
# Generation Brief — [timestamp]

## FORM
- Name: soneto
- Language: es
- Structure: 14 lines, 2 quartets + 2 tercets
- Metre: hendecasyllables (11 syllables/line)
- Rhyme scheme: ABBA ABBA CDC DCD

## TONE
- melancholic
- tender
- restrained (Machado-like economy)

## THEME
- departure
- unspoken words
- the weight of silence

## PERSONAL CONTEXT (retrieved fragments)

### Fragment: 2019-station-departure (similarity: 0.87)
> That evening at the station, I watched the train pull away.
> The weight of things I didn't say pressed against my chest.

### Fragment: 2021-letter-unsent (similarity: 0.72)
> I wrote the letter three times. Burned all three.
> Some words only exist in the not-saying.

## WORD SEEDS + EXPANSIONS

### "silencio" (provided)
- Synonyms: callar, mudez, sigilo, quietud
- Rhymes (consonant): indicio, propicio, vicio
- Rhymes (assonant): tiempo, viento, cielo

### "partir" (provided)
- Synonyms: marchar, alejarse, huir, despedirse
- Rhymes (consonant): sentir, decir, vivir

## RHYME OPTIONS FOR TARGET SCHEME

### -ía words (high utility)
melancolía, lejanía, todavía, poesía, alegría, agonía

### -ento words
viento, momento, pensamiento, sentimiento

## EXEMPLAR LINES (your past work, similar tone)

From "Andenes" (2023):
> "El tren se lleva lo que no dijimos"
> "Quedó en el andén la palabra exacta"

## INFLUENCE ANCHOR

Machado: spare, meditative, landscape-as-interior.
Avoid: ornate flourishes, Baroque density, sentimentality.

---

Generate a soneto exploring this departure, using the provided seeds,
staying within the tonal register, grounded in the personal fragments above.
```

## Brief Verbosity Levels

| Level | Includes | Use Case |
|-------|----------|----------|
| **Minimal** | Form + theme + 2-3 fragments + seeds | Quick drafts, familiar territory |
| **Standard** | Above + rhyme options + exemplar lines | Default for most generation |
| **Maximal** | Above + influence anchors + anti-patterns | Complex pieces, unfamiliar forms |

CLI flag: `--brief-level minimal|standard|maximal`

## BriefBuilder Interface (implemented)

See `src/poesia/generation/brief_builder.py` for full implementation.

```python
class BriefBuilder:
    def __init__(
        self,
        embedding_client: EmbeddingClient | None = None,
        fragments: list[FragmentRecord] | None = None,
        influences: list[InfluenceRecord] | None = None,
    ) -> None: ...

    def add_fragments(self, fragments: list[FragmentRecord]) -> None: ...
    def add_influences(self, influences: list[InfluenceRecord]) -> None: ...

    def build(
        self,
        form: str | FormSpec,
        theme: str,
        tone: list[str] | None = None,
        seeds: list[str] | None = None,
        level: Literal["minimal", "standard", "maximal"] = "standard",
        language: str | None = None,
    ) -> GenerationBrief: ...


@dataclass
class GenerationBrief:
    form_spec: FormSpec
    theme: str
    tone: list[str]
    fragments: list[tuple[FragmentRecord, float]]  # (fragment, similarity)
    seeds_expanded: dict[str, SeedExpansion]
    rhyme_options: dict[str, list[str]]
    exemplar_lines: list[str]
    influences: list[InfluenceRecord]
    level: str  # "minimal", "standard", "maximal"
    created_at: datetime

    def to_prompt(self) -> str:
        """Render brief as LLM prompt string."""
        ...
```

## Integration Point

The `CandidateGenerator` currently receives raw instructions. After integration:

```python
# Before
candidates = generator.generate(
    prompt="Write a melancholic Spanish sonnet about departure",
    form=SONETO_ES,
)

# After
brief = brief_builder.build(
    form="soneto",
    theme="departure",
    tone=["melancholic", "tender"],
    seeds=["silencio", "partir"],
)
candidates = generator.generate(brief=brief)
```

## Cost Savings Estimate

| Approach | LLM Calls | Tokens/Call | Est. Cost |
|----------|-----------|-------------|-----------|
| Iterative (old) | 5-10 | 500-1000 | $0.05-0.15 |
| Brief-grounded | 1-2 | 2000-3000 | $0.02-0.04 |

Front-loading context trades input tokens for fewer calls. Net savings: ~50-70%.
