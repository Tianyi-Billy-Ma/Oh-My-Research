# Phase 3 — Summarize

**Goal:** turn `paper_bank.json` into a human-readable `summary.md` — a
landscape table + clustered narrative + open questions. Idempotent across
re-runs via a versioned marker block.

## Invariants

- **`summary.md` only cites entries that exist in `paper_bank.json`.**
  Every paper mentioned in the narrative has a row in the table; every
  row in the table has an entry in the corpus.
- **No fabrication.** If a paper's abstract/year is missing in the
  corpus, treat that field as `?` in the table — never invent.
- **Marker block is idempotent.** Re-runs replace the block in place; the
  user's content outside the marker (if any) is preserved.
- **Output template is the source of truth.** Follow
  `references/output-template.md` for table columns, narrative
  structure, and length budget.

## Steps

### 3.1 Load corpus and references

Read:
- `<workspace>/paper_bank.json` → `papers[]`.
- `<workspace>/scope.yaml` → `research_question`, `output_languages`.
- `${CLAUDE_PLUGIN_ROOT}/skills/literature-review/references/output-template.md`
  for column conventions and narrative structure.

If `papers[]` is empty (Phase 2 found nothing usable), halt with:

> No papers in the corpus. Re-run with different `--sources` or check
> `log.jsonl` for source failures.

### 3.2 Filter entries with insufficient metadata

For summarization, an entry needs at minimum: `title`, `authors`, `url`,
plus enough text for the narrative (`abstract` OR `notes`). Entries
without abstract/notes can still appear in the table but contribute
nothing to the narrative — flag them so the user knows to fetch more
detail later.

### 3.3 Cluster the corpus

Group papers into **2–4 thematic clusters** based on the
`research_question` and the abstracts. Be explicit about the clustering
criterion (method family, problem variant, dataset/domain, etc.) so
re-runs can reproduce the grouping rationale.

Within each cluster:
- Sort by year descending.
- Mark the foundational paper (oldest cited, or canonically named) in
  its cluster.

### 3.4 Render the table

Use the columns from `references/output-template.md`:

`| Paper | Venue | Year | Approach | Key finding | Limitation | Relevance |`

Rules:
- `Paper` is `[Title](url)` — `url` is the corpus entry's URL field.
- `Venue` is empty for preprints (mark in the Year column as `(preprint)`
  if helpful).
- `Approach`, `Key finding`, `Limitation`, `Relevance` are 3–12 word
  cells extracted from the abstract. Be honest: if you can't tell, write
  `unclear`.
- `Relevance` always ties back to `scope.yaml.research_question`.

Group rows by cluster with a sub-heading. Within each cluster, keep
rows in the order from 3.3.

### 3.5 Render the narrative

Follow `references/output-template.md`'s narrative structure:

1. **Landscape** — name the 2–4 clusters explicitly. 2–3 sentences each.
2. **Methods** — what techniques dominate; what assumptions they share.
3. **Findings** — where evidence converges; where it diverges.
4. **Open questions** — 3–6 bullets. These will feed `/omr:ideate`
   (future skill).

Length budget: 500–1500 words excluding the table. Tighter is better.
Every claim cites a paper from the corpus (by title or `[link](url)`).

### 3.6 Apply the marker block

Read `${CLAUDE_PLUGIN_ROOT}/skills/literature-review/templates/summary.md`
as the scaffold. Render the table + narrative into the slots inside
the marker:

```
<!-- BEGIN omr:lit-review version="<OMR_VERSION>" -->
... rendered content ...
<!-- END omr:lit-review -->
```

Resolve `{{omr_version}}` to the current plugin version (same pattern as
`templates/hpc.yaml`).

### 3.7 Write `summary.md` per output language

For each language in `scope.yaml.output_languages`:

- `en` → `<workspace>/summary.md`.
- `<other>` (e.g. `zh`, `ja`) → `<workspace>/summary.<lang>.md`. Translate
  the rendered content; keep URLs, titles, and paper IDs as-is. Don't
  invent new analysis in translation.

If the file already exists (refresh run):
- Marker block present → replace its contents in place. Preserve
  anything outside the block.
- Marker block absent but file exists → ask via `AskUserQuestion`:

  > `<path>` exists but has no omr:lit-review marker. Append the
  > generated block, or overwrite the whole file (backup taken)?

  Options: `Append block` / `Overwrite (back up to <path>.backup.<date>)`.

### 3.8 Log and wrap up

Append to `log.jsonl`:

```json
{"ts":"<ISO>","phase":"summarize","action":"summary_written","languages":<list>,"paper_count":<int>,"clusters":<int>}
```

Print the final block:

```
omr:literature-review — done.

  Corpus:   <workspace>/paper_bank.json (<n> papers, <m> sources)
  Summary:  <workspace>/summary.md  (+ summary.<lang>.md for each extra language)
  Audit:    <workspace>/log.jsonl

Open questions surfaced — these feed a future /omr:ideate run.
```

## Handoff

This is the terminal phase. Echo:

> /omr:literature-review complete.

…and stop.
