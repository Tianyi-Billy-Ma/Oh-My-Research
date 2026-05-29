# Phase 2 — Search

**Goal:** populate `paper_bank.json` with candidate papers from the sources
listed in `scope.yaml`. Knowledge-base-first, then MCPs, then web. Every
entry is schema-valid; every URL is real.

## Invariants

- **Append-only.** If `paper_bank.json` exists (refresh run), merge by
  canonical `id` — never reorder or drop existing entries.
- **Skip silently on missing sources.** If Zotero MCP isn't loaded, or
  an MCP token is missing, log the gap to `log.jsonl` and move to the
  next source. Don't fail the run unless **all** sources fail.
- **Validate every entry before write.** Use `templates/paper_bank.schema.json`.
  Entries missing required fields (`id`, `title`, `authors[]`, `url`,
  `source`, `retrieved_at`) get logged to `log.jsonl` and dropped.
- **`max_papers` is a hard cap.** Stop search as soon as the corpus
  reaches `scope.yaml.max_papers`. Document the stopping point in the
  log.

## Steps

### 2.1 Load scope and pre-existing corpus

Read:
- `<workspace>/scope.yaml`
- `<workspace>/paper_bank.json` if it exists; else initialize an empty
  one from `templates/paper_bank.schema.json` with metadata fields
  filled (`schema_version` via `{{omr_version}}`, `slug`, `created_at`).

Build a `seen_ids` set from existing entries' `id` field for dedup.

### 2.1a Seed from an existing corpus (`--from-existing`)

If the `--from-existing <value>` flag was parsed at the skill level, import
its entries **before** any source search. `<value>` is one of:

- **A Zotero collection name** — resolve via `mcp__zotero__zotero_get_collections`,
  match the name case-insensitively, then pull items with
  `mcp__zotero__zotero_get_collection_items`. Tag each imported entry with
  `source: "zotero"` and set `retrieval_query: "from-existing: collection <name>"`.
  Requires the Zotero MCP to be loaded — if it isn't, halt and tell the
  user the collection can't be reached.
- **A path to a `paper_bank.json`** — read the file, validate it against
  `templates/paper_bank.schema.json`, and import its `papers[]`. This lets
  a teammate's corpus seed yours. Preserve each entry's original `source`
  value; append `,from-existing` is **not** done — instead record the
  provenance in `notes` (e.g. `"imported from <path>"`).
- **A path to a BibTeX export (`.bib`)** — parse entries. Map BibTeX
  fields to the schema: `title`→`title`, `author`→`authors[]` (split on
  ` and `), `year`→`year`, `journal`/`booktitle`→`venue`, `doi`→`id`+`url`
  (`https://doi.org/<doi>`), `url`→`url` when no DOI, `abstract`→`abstract`.
  Set `source: "bibtex"` and `retrieval_query: "from-existing: <path>"`.
  If neither a DOI nor a usable URL is present, the entry fails the `url`
  rail — drop it and log.

Detection: if `<value>` is an existing file path ending in `.json` treat it
as a paper_bank import; ending in `.bib` treat it as BibTeX; otherwise treat
it as a Zotero collection name.

Every imported entry is **normalized and validated exactly like a search
hit** (see 2.4) — same required fields, same `url` and `authors[]` rails,
same dedup against `seen_ids`. Set `screening: null` on every import so
Phase 3 (Screen) evaluates it from scratch; never trust a verdict carried
in from an external file. Drop and log any import that fails validation:

```json
{"ts":"<ISO>","phase":"search","action":"import_dropped","origin":"<from-existing value>","title":"<truncated>","reason":"<field>"}
```

Log the import summary:

```json
{"ts":"<ISO>","phase":"search","action":"from_existing_import","origin":"<value>","imported":<int>,"dropped":<int>}
```

After import, continue to 2.2 and run the normal source search unless
`--sources` was set to an empty/none chain. Imported and freshly-searched
entries share one corpus and all flow into screening together.

### 2.2 Validate token presence per requested source

For each source in `scope.yaml.sources`:

| Source | Token required | Probe |
| --- | --- | --- |
| `zotero` | none (MCP loaded?) | check for `mcp__zotero__*` tool availability |
| `local` | none | check that at least one of `papers/`, `literature/`, or `<workspace>/../*/paper_bank.json` exists |
| `exa` | `EXA_API_KEY` | `printenv EXA_API_KEY` |
| `tavily` | `TAVILY_API_KEY` | `printenv TAVILY_API_KEY` |
| `brave-search` | `BRAVE_API_KEY` | `printenv BRAVE_API_KEY` |
| `huggingface` | `HF_TOKEN` | `printenv HF_TOKEN` |
| `github` | `GITHUB_PERSONAL_ACCESS_TOKEN` | `printenv GITHUB_PERSONAL_ACCESS_TOKEN` |
| `web` | none | always available |

Missing tokens → log `{"action":"source_skipped","source":"<id>","reason":"<id>_TOKEN missing"}` and drop the source from this run. Don't ask the user — they already configured `sources` in scope.yaml.

If **every** source ends up dropped, halt and tell the user:

> No sources reachable. Run `/omr:setup --audit` to see token gaps, then
> re-run this skill. Workspace state preserved.

### 2.3 Search in priority order

Process `scope.yaml.sources` in the order given. For each source:

1. Build query variants from `scope.yaml.research_question`. Keep them
   short and specific (3–8 word phrases).
2. Dispatch the query. Per-source query strategies live in
   `${CLAUDE_PLUGIN_ROOT}/skills/literature-review/references/source-priority.md`
   — read it once, follow it for all sources.
3. For each hit, attempt to normalize to a `paper_bank.json` entry
   (schema below). Skip hits that can't reach a real URL — log them.
4. Dedup against `seen_ids` and the in-flight batch. Multi-source hits
   keep `source` as a comma-joined string in order of first
   appearance (e.g. `"exa,web"`).
5. Stop the source's loop when:
   - The source returns no more results, OR
   - The combined corpus + new hits reach `scope.yaml.max_papers`, OR
   - You've pulled 25 hits from this single source (per-source soft cap
     to keep diversity).

### 2.4 Entry normalization

Required fields per `templates/paper_bank.schema.json`:

| Field | How to fill |
| --- | --- |
| `id` | DOI (`10.xxxx/yyyy`) if available; else arXiv ID (`2401.12345`); else stable hash of title (`sha1` first 12 chars). |
| `title` | Verbatim from source. |
| `authors` | Array of strings. If source returns "Last, First" or "First Last", normalize to one consistent form per entry. Never empty, never `["TBD"]`. |
| `url` | DOI URL preferred (`https://doi.org/<id>`); else arXiv abs URL; else publisher / Semantic Scholar URL. Never blank. |
| `source` | The source ID that returned this hit. Multi-source dedup uses comma-join. |
| `retrieved_at` | ISO-8601 timestamp of this run. |

Optional but-fill-when-available:
- `year`, `venue`, `abstract`, `retrieval_query`, `notes`.

Always set `screening: null` on a freshly added entry. Phase 3 (Screen)
populates the `screening` object; Phase 2 never writes a verdict.

Drop the entry if `id`, `title`, `authors`, or `url` can't be set.
Log the drop:

```json
{"ts":"<ISO>","phase":"search","action":"entry_dropped","source":"<id>","title":"<truncated>","reason":"<which field is missing>"}
```

### 2.5 Write `paper_bank.json`

After each source completes its batch (not per-entry), write the merged
corpus atomically:

```bash
jq --argjson new "$BATCH" \
   '.papers += $new | .last_updated_at = (now | todate)' \
   "<workspace>/paper_bank.json" > "<workspace>/paper_bank.json.tmp"
mv "<workspace>/paper_bank.json.tmp" "<workspace>/paper_bank.json"
```

If `jq` is unavailable, use a Python one-liner with `json` stdlib. Either
way: atomic via tmpfile + rename, never partial writes.

Log per-source completion:

```json
{"ts":"<ISO>","phase":"search","action":"source_done","source":"<id>","hits_added":<int>,"hits_dropped":<int>}
```

### 2.6 Final validation

After all sources run, re-load `paper_bank.json` and validate every
entry against `templates/paper_bank.schema.json`. Drop and re-write if
any entry fails (this shouldn't happen — but it catches schema drift
from edited files).

Print a one-line summary to the user:

> Search done — `<n_total>` papers in `paper_bank.json` (`<n_new>` added
> this run from sources: `<list>`). Skipped `<n_dropped>` entries with
> missing required fields (see `log.jsonl`).

## Audit-only flow (--audit flag)

If `--audit` was passed at the skill level, **stop after search** — do not
run Phase 3 (Screen) or Phase 4 (Summarize). Skip 2.1–2.5 entirely.
Instead:

1. Load `<workspace>/paper_bank.json`.
2. Validate every entry against the schema. Report violations to stdout
   with line/index, missing field, and entry title.
3. Check `schema_version` against the current plugin version. If
   different, print:

   > Schema version drift: corpus is `<v>`, plugin is `<v>`. Refresh by
   > re-running `/omr:literature-review` without `--audit`.
4. Don't write anything.

## Handoff

> Phase 2 done — `<workspace>/paper_bank.json` now has `<n>` entries. Moving to screen.

Pass forward to Phase 3 (Screen): the workspace path and the path to
`paper_bank.json`. Phase 3 needs `scope.yaml.criteria` (year window,
preprint/workshop flags, min_citations) to apply the rubric — not the
source list.
