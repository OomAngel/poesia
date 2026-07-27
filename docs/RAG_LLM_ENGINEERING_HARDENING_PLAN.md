# PoesIA RAG, GraphRAG, and LLM Engineering Hardening Plan

Doc class: canonical implementation plan for PoesIA RAG/LLM work  
Status: active  
Created: 2026-07-27  
Scope: `memoria/`, embedding-backed evaluation, retrieval-informed generation, hosted
LLM integration, and their CLI/user journeys

This plan is subordinate to `AGENTS.md` and `docs/ARCHITECTURE.md`, but it is the
authoritative sequencing and completion guide for RAG, GraphRAG, embeddings, and LLM
lifecycle work. A phase or capability must not be described as complete merely because
files exist or the aggregate test count passes.

## 1. Current assessment

PoesIA contains real RAG/LLM engineering, but its current “GraphRAG complete” claim is
ahead of the implementation. It presently consists of several valuable components that
are not yet joined into one dependable end-to-end system.

### What is genuinely implemented

- provider-neutral LLM integration through an `LLMClient` protocol;
- deterministic generation, validation, scoring, ranking, and repair orchestration;
- dense semantic retrieval of personal fragments for generation briefs;
- an explicit embedding-client abstraction with multilingual E5 support;
- semantic-graph construction and retrieval when correct explicit embeddings are supplied;
- local graph JSON persistence and neighbourhood queries;
- retrieval-informed prompt construction;
- hosted Gemini/OpenAI HTTP adapters and mock-based request/response tests;
- a Markdown/SQLite poem library.

### Current honest positioning

Until the acceptance criteria in this plan are met, describe PoesIA as:

> A hybrid deterministic/LLM poetry system with dense personal-context retrieval and a
> separate semantic-graph prototype.

Do not yet describe the complete application journey as production GraphRAG or operated
LLMOps.

## 2. Critical embedding-contract defect

The embedding protocol correctly distinguishes:

```text
embed(list[str]) -> list[list[float]]
embed_one(str)   -> list[float]
```

However, `GraphRAGRetriever.ingest()` and `LineScorer` pass scalar strings to the batch
method. Because Python strings are iterable, a text such as `"moon"` is interpreted as
four separate documents and produces four vectors instead of one.

Observed directly on 2026-07-27:

```text
embed("abc")     -> shape 3 x 384
embed_one("abc") -> shape 384
```

Consequences:

- one auto-embedded poem stores a nested, malformed embedding;
- retrieval commonly returns `0.0` because query and stored dimensions differ;
- two auto-embedded records with equal-length text can crash cosine evaluation with:

  ```text
  TypeError: can't multiply sequence by non-int of type 'list'
  ```

- semantic line scoring silently falls back to `theme=0.0` and `novelty=1.0`;
- broad exception handling hides the failure and makes the pipeline appear healthy.

### Why existing tests miss it

- the auto-embedding test checks only that the stored value is truthy;
- the theme test says “non-zero” but accepts `theme >= 0.0`;
- the novelty test checks only that the result contains a `novelty` key;
- hand-authored flat vectors bypass the broken automatic integration path.

### Required correction

- use `embed_one()` for scalar text and `embed()` only for batches;
- replace `Any` with the typed `EmbeddingClient` port;
- validate vector rank, dimensions, numeric values, and finiteness at the boundary;
- remove silent semantic fallback or expose it explicitly in the result;
- add failure tests for malformed vectors;
- test at least two auto-embedded records plus a real retrieval query;
- assert meaningful semantic outcomes, not merely key presence or non-negativity.

## 3. The current flow is not integrated GraphRAG

PoesIA currently has three partially separate mechanisms:

1. dense fragment retrieval in `BriefBuilder`;
2. a semantic-similarity graph in `GraphRAGRetriever`;
3. LLM generation in `ConstrainedLoop`.

`BriefBuilder` accepts and stores a `GraphRAGRetriever`, but does not call it. It performs
its own dense fragment retrieval. `GraphRAGRetriever.retrieve()` also ignores graph edges
and scans all node embeddings directly. Graph traversal is available only through the
separate `neighbourhood()` method, and that context is not assembled into a generation
brief.

The current implementation is therefore:

> Dense RAG for personal fragments plus a separate semantic-neighbourhood graph.

It becomes a defensible GraphRAG journey only when graph structure materially selects,
expands, constrains, or explains the context supplied to generation.

## 4. The graph model is narrower than the documented design

The design describes poems, fragments, seeds, themes, influences, and the relationships
`similar_to`, `inspired_by`, `explores`, and `contains`. The implementation currently
ingests only `PoemRecord` nodes and creates only cosine-similarity edges.

Similarity alone adds little beyond a vector index. The graph becomes valuable when it
can answer and explain:

- Which personal fragments connect to this theme?
- Which influences and exemplar lines shaped those fragments?
- Which seeds appeared in related poems?
- Which relationships should be included or excluded for this generation?
- Why was each context item retrieved?

### Required correction

- define one canonical graph schema for every implemented node and edge type;
- retain source/provenance identifiers on nodes and relations;
- ingest the record types promised by the schema;
- make traversal bounded and deterministic;
- return retrieval explanations and relationship paths;
- keep dense similarity, graph expansion, and final context selection distinguishable.

## 5. The user journey bypasses implemented components

A functional Markdown/SQLite `Library` exists, but `poesia memoria list` and
`poesia memoria search` still report Phase-0 stubs. The CLI does not expose:

```text
save accepted poem
  -> index poem and related context
  -> build or update embeddings and graph
  -> retrieve and inspect context
  -> assemble a grounded generation brief
  -> generate and validate candidates
  -> let the human choose
  -> save the accepted result with provenance
```

### Required correction

Implement one complete vertical slice before adding more algorithms:

1. persist and list real library records through the CLI;
2. ingest exact library/context records into retrieval;
3. retrieve context for one theme and expose why it was selected;
4. include selected context in the generation brief;
5. produce validated candidate lines;
6. present alternatives for human selection;
7. save the accepted poem with retrieval/model/configuration provenance.

## 6. Embedding and index compatibility is unprotected

Persisted graph JSON currently lacks:

- model ID and immutable revision;
- vector dimensions;
- query/document prefix contract;
- normalization and pooling;
- tokenizer/configuration fingerprint;
- similarity function;
- source-content fingerprint;
- index-build version.

Embeddings produced by one model can therefore be loaded and queried by another without
detection. The E5 client also prepends `query:` to every input, including stored
documents, although E5 retrieval should distinguish query and passage roles.

### Required correction

Introduce one immutable embedding compatibility descriptor containing:

- model ID and revision;
- dimensions;
- query and document prefixes;
- normalization and pooling;
- tokenizer/configuration fingerprint;
- implementation profile;
- vector type and similarity function.

Derive index identity and persisted metadata from that descriptor plus the source-corpus
fingerprint. Build and query must require the exact same descriptor.

## 7. Persistence and scale boundaries

Current risks:

- graph saving is not atomic;
- corrupt or incompatible JSON is swallowed and silently replaced with an empty graph;
- re-ingestion can leave obsolete similarity edges;
- similarity threshold `0.70` is hard-coded and unevaluated;
- graph construction is all-pairs `O(n²)`;
- retrieval scans every node;
- no lock or concurrent-reader/writer policy exists.

Linear retrieval and NetworkX remain reasonable for a small personal corpus. That boundary
should be explicit and measured rather than implied to be unlimited.

### Required correction

- atomically replace persisted graphs;
- distinguish missing, corrupt, incompatible, and empty states;
- never discard a persisted graph silently;
- rebuild similarity edges from a clean edge set;
- fingerprint and evaluate the threshold;
- record expected corpus size and latency budget;
- define a migration trigger for another vector/graph store.

## 8. RAG evaluation is missing

Current tests demonstrate that functions can run with synthetic vectors. They do not
establish retrieval or generation quality.

The evaluation system must answer:

- Are the right fragments, poems, seeds, and influences retrieved?
- Does graph expansion improve over dense retrieval?
- Does retrieved context preserve Angel's voice?
- Does it improve formal validity, relevance, novelty, or cliché avoidance?
- Does irrelevant context harm generation?
- Can every generated influence or personal reference be traced?
- Does the embedding profile work across Spanish, English, and Dutch?

### Required evaluation corpus

Create a small owner-reviewed multilingual corpus containing:

- representative theme/tone/form queries;
- expected relevant context records;
- prohibited or misleading context;
- relationship paths expected from graph expansion;
- generation comparisons for no retrieval, dense retrieval, and graph-enhanced retrieval.

### Required metrics

- Recall@k and at least one early-ranking metric;
- irrelevant-context exposure;
- context precision or owner acceptance;
- provenance/attribution coverage;
- formal-validity rate;
- groundedness and unsupported-reference rate;
- latency and, for hosted generation, token/cost metadata.

No retrieval or generation profile is selected from one convenient example.

## 9. Hosted-model lifecycle and privacy

Current hosted integration lacks:

- retry/backoff and rate-limit handling;
- model and prompt revision manifests;
- token, latency, and cost tracking;
- structured response validation;
- provider/model provenance on saved output;
- explicit privacy/export approval before personal fragments are transmitted;
- robust redaction of provider error bodies.

Personal fragments are particularly sensitive. Enabling a hosted LLM with a rich brief may
transmit them outside the local machine.

The CLI fallback is also unreliable: `get_embedding_client()` returns a lazy client inside
the `try`, while import/model/download failure may occur only later during `embed()`.

### Required correction

- make local versus hosted execution explicit;
- require an owner-visible disclosure/export decision for personal context;
- record provider, model, prompt/configuration fingerprint, and disclosed source IDs;
- add bounded retries, timeouts, and rate-limit handling;
- record latency, token usage, and estimated cost without logging prompt bodies;
- validate provider output before it enters the generation loop;
- probe lazy dependencies before reporting that a backend is active.

## 10. Generation-validation gaps

The core hybrid idea is strong, but documented guarantees remain incomplete:

- rhyme scoring is inactive unless a target rhyme key is supplied;
- the loop does not manage a complete form's rhyme scheme line by line;
- repair targets metrical mismatch only;
- provider output is not strictly constrained to one clean line;
- the CLI automatically selects the top candidate rather than presenting alternatives;
- broad exception swallowing can present semantic failure as valid fallback.

### Required correction

- derive the target rhyme role from line position and `FormSpec`;
- validate metre, rhyme, theme, novelty, repetition, and output shape separately;
- request repair for one explicit failed constraint at a time;
- rescan every repaired candidate;
- expose a bounded candidate set and score breakdown to the human;
- persist only the human-selected result;
- distinguish deliberate degraded mode from accidental failure.

## 11. Documentation and completion drift

The repository currently contains contradictory states:

- memory-bank notes say load-bearing semantic gaps were fixed;
- the same active context lists auto-embedding as future work;
- the task board says GraphRAG and auto-embedding are complete;
- the CLI describes the library as a Phase-0 stub;
- architecture documents contain phase states that no longer agree.

### Required correction

- use this document as the active RAG/LLM completion authority;
- treat old phase-complete statements as historical, not current proof;
- update status only from acceptance evidence;
- record known defects explicitly;
- distinguish implemented, locally verified, integrated, evaluated, and operated states.

## 12. Implementation sequence

### P0 — Restore semantic correctness

1. Correct every scalar/batch embedding call.
2. Add vector shape and compatibility validation.
3. Remove silent semantic failure.
4. Replace weak test oracles with discriminating expected outcomes.
5. Prove auto-ingestion and semantic scoring with at least two records.

### P1 — Complete one end-to-end RAG journey

1. Wire the real library into the CLI.
2. Ingest library and context records.
3. Retrieve and expose selected context.
4. Feed that exact context into `GenerationBrief`.
5. Generate, validate, present alternatives, and save the human selection.
6. Preserve source and configuration provenance.

### P2 — Make graph structure materially useful

1. Implement typed nodes and relations.
2. Add bounded graph expansion.
3. Return paths and explanations.
4. Compare dense-only with graph-enhanced context.

### P3 — Make artifacts reproducible

1. Add the immutable embedding/index compatibility descriptor.
2. Add source and graph fingerprints.
3. Make persistence atomic and versioned.
4. Add explicit rebuild/migration behaviour.

### P4 — Establish evaluation

1. Build the reviewed multilingual corpus.
2. Evaluate retrieval and context exposure.
3. Evaluate grounded generation and formal validity.
4. Freeze a profile only after comparative evidence.

### P5 — Add provider and operational controls

1. Add privacy/export decisions.
2. Add provider/run lineage.
3. Add retries, structured failures, latency, token, and cost metadata.
4. Add monitoring/deployment only when an operated deployment exists.

## 13. Definition of done

PoesIA may claim an integrated GraphRAG generation system when:

- an exact corpus version is ingested with a compatible embedding profile;
- retrieval returns relevant records plus explainable graph paths;
- the graph materially affects selected generation context;
- that context is visible in the generation brief;
- generated candidates are validated and presented for human choice;
- accepted output preserves source/model/configuration provenance;
- dense-only and graph-enhanced retrieval have been compared on reviewed examples;
- private context cannot reach a hosted provider without an explicit decision;
- failures are visible rather than silently converted into success;
- the CLI executes the complete user journey.

Production MLOps/LLMOps remains a separate later claim requiring hosted deployment,
monitoring, rollback, incident/failure handling, and operated evidence.
