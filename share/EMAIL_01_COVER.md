# Email 1 — Cover / introduction

> Copy into your mail client. Everything in `[brackets]` is for you to fill in.
> An English body + a short Spanish variant at the end.

**To:** [contact's email]
**Subject:** PoesIA — the poetry engine I've been building (for your eyes only)

Hi [name],

I've been building something quietly for a while, and I wanted to share it with
one person who I think will actually get it: PoesIA.

It's a poetry-writing engine — but not another "ask an AI for a poem" tool.
The idea is a hybrid: a language model supplies the imagination (metaphor,
mood, surprise), and a set of deterministic algorithms verify the craft —
syllable counts, stress, rhyme, how the words sound — then repair whatever
doesn't pass. The name is a pun: "poesía" is Spanish for poetry, and the last
three letters are already *IA* (Inteligencia Artificial — AI). Every module
follows the same trick: EufonÍA (sound analysis), GalerÍA (illustration),
MemorÍA (a personal library with retrieval), ArmonÍA (turning poems into music).

It started as a personal project, so it's tuned for Spanish first — it handles
sinalefa correctly, scans hendecasyllable verse, and draws on a corpus of
~7,500 public-domain poems (Machado, Lorca, Darío, Sor Juana…).

**What you'll receive**
The full repository as a single tarball — README, usage guide, docs, tests.
You can unpack it and have it running locally in about five minutes
(Python 3.11; an offline "stub" mode works with zero API keys).

**The license, in plain language**
- The *software* is MIT-licensed: read it, run it, adapt it, build on it —
  just keep the copyright notice.
- The *original poems and personal fragments* inside (`seeds/`) are mine and
  stay mine. I'm sharing them so you can read them, not to hand over rights.
- The *corpus poems* are public domain (Project Gutenberg / Wikisource), with
  full provenance documented in the repo.

More than anything, I'd genuinely love your reaction — especially on the
poems it writes and whether you think the whole "engine" idea holds up.
The follow-up email in this thread is a 15-minute tour if you want to try it.

Warmly,
[your name]

---

## Versión en español (si tu contacto prefiere)

**Para:** [email del contacto]
**Asunto:** PoesIA — el motor de poesía que llevo construyendo (solo para tus ojos)

Hola [nombre],

Llevo un tiempo construyendo algo en silencio y quería compartirlo con una
persona que creo que lo va a entender: PoesIA.

No es otra herramienta de "pídele un poema a la IA". Es un híbrido: un modelo
de lenguaje aporta la imaginación (metáfora, tono, sorpresa) y un conjunto de
algoritmos deterministas verifica el oficio — sílabas, acentos, rima, sonoridad —
y repara lo que no pasa. El nombre es un juego: "poesía" ya lleva IA escondida
en las últimas tres letras. Y cada módulo juega igual: EufonÍA, GalerÍA,
MemorÍA, ArmonÍA.

Es un proyecto personal, pensado primero para español: maneja sinalefa,
escande endecasílabos y se apoya en un corpus de ~7.500 poemas de dominio
público (Machado, Lorca, Darío, Sor Juana…).

**Qué recibes:** el repositorio completo en un solo archivo — README, guía de
uso, documentación y tests. En cinco minutos lo tienes corriendo localmente
(Python 3.11; el modo "stub" funciona sin claves de API).

**La licencia, en cristiano:** el *software* está bajo MIT (léelo, úsalo,
adáptalo, conservando el aviso de copyright); los *poemas y fragmentos
originales* en `seeds/` son míos y siguen siendo míos (te los comparto para
leerlos, no para ceder derechos); el *corpus* es de dominio público con
procedencia documentada.

Me encantaría tu reacción, sobre todo a los poemas que escribe. El siguiente
correo es un recorrido de 15 minutos si quieres probarlo.

Un abrazo,
[tu nombre]
