# Phase 1 — Scope

**Goal:** turn the user's intent into a reusable `scope.yaml` that the later
phases (Search → Screen → Summarize) consume. Captures the research
question, time window, source priority, output configuration, and corpus
size cap. Also routes existing workspaces to maintain vs fresh.

## Steps

### 1.1 Resolve slug and workspace path

Derive a kebab-case slug from the `--topic` argument (or `$ARGUMENTS` if
no flag was given). Strip non-alphanumeric characters, lowercase, hyphens
only.

Examples:
- `"diffusion models for protein design"` → `diffusion-models-for-protein-design`
- `"RAG vs long-context"` → `rag-vs-long-context`
- `"https://arxiv.org/abs/2401.12345"` → ask the user for a slug; URLs
  don't make good slugs.

If `--topic` is missing AND no positional arg, ask via `AskUserQuestion`:

> What's the research question or topic for this literature review?

(Free-form expected; the user types the question, then we generate the
slug ourselves and confirm.)

Workspace path from the `--scope` flag:
- `scope=local` → `./.omr/literature/<slug>/`
- `scope=global` → `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/literature/<slug>/`
- No flag → ask via `AskUserQuestion`:

  > Where should the literature workspace live?
  >
  > 1. **Local** (`./.omr/literature/<slug>/`) — per-project (recommended for project-specific reviews).
  > 2. **Global** (`~/.claude/literature/<slug>/`) — per-user (recommended for evergreen topics).

### 1.2 Check existing workspace

If the workspace directory already exists, ask via `AskUserQuestion`
unless `--force` was passed:

> A workspace already exists at `<path>`. What now?

Options:
1. **Maintain (recommended)** — merge new findings into the existing
   `paper_bank.json`, screen only the new entries, and refresh
   `summary.md`. Runs Phase 5 (Maintain), which composes Search → Screen →
   Summarize with append-only/dedup guardrails. The existing `scope.yaml`
   is the source of truth; don't re-prompt scoping fields.
2. **Fresh re-run** — re-run the full flow (Search → Screen → Summarize)
   against the same `scope.yaml`. Still append-only on `paper_bank.json`,
   but new entries are screened and the summary fully re-rendered.
3. **Pick a new slug** — keep both corpora. Skip back to 1.1 to derive a
   new slug.
4. **Cancel** — exit without changes.

If `--force` was passed, behave as **Maintain** without asking.

- **Maintain** → jump straight to Phase 5 (`05-maintain.md`); skip the
  rest of Phase 1. Echo the maintain-mode handoff at the bottom of this
  file.
- **Fresh re-run** → jump to 1.5 (don't re-prompt scoping fields); the
  existing `scope.yaml` is the source of truth, then continue into Search.

### 1.3 Collect scoping fields

For a fresh workspace, ask in **small batches via `AskUserQuestion`** —
2–3 questions per round, never one giant form. Capture:

**Round 1 — research question (skip if `--topic` covered it):**
- Confirm the research question. Show the user what we have and let
  them refine.

**Round 2 — time window:**
- `year_min`: "Earliest year to include?" Options: `Last 5 years`,
  `Last 10 years`, `All time`, `Custom`.
- `year_max`: usually current year; ask only if the user picked
  `Custom`.

**Round 3 — quality filters:**
- `include_preprints`: true/false. Default true (preprints often have
  the freshest work).
- `include_workshop_papers`: true/false. Default true.
- `min_citations`: optional integer. Default blank (most sources
  don't reliably return citation counts).

**Round 4 — corpus size:**
- `max_papers`: integer. Default 50. Smaller for narrow reviews,
  larger for broad surveys.

**Round 5 — output languages:**
- `output_languages`: ask if user wants languages beyond English.
  Options: `English only` / `English + Chinese` / `English + others
  (specify)`. Default `[en]`.

Don't ask about `sources` here — Phase 2 uses the chain from
`./.omr/config.yaml` `literature_review.default_sources` (loaded in the
SKILL-level pre-run check), or the template default if no config exists,
unless `--sources` was passed on the command line.

When prompting for `default_scope`, `output_languages`, and `max_papers`
above, **default each answer to the value from `./.omr/config.yaml`'s
`literature_review:` block** when present, so a configured project doesn't
re-ask what the user already set. Flags still override.

### 1.4 Write `scope.yaml`

Read `${CLAUDE_PLUGIN_ROOT}/skills/literature-review/templates/scope.yaml`.
Substitute `{{omr_version}}` with the current plugin version (read from
`${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` `.version`). Replace
every `<placeholder>` with the value collected in 1.1–1.3.

If `--sources` was passed on the command line, overwrite the `sources:`
array with the parsed list. Validate each name against the allowed set:
`zotero`, `local`, `exa`, `tavily`, `brave-search`, `huggingface`,
`github`, `web`. Reject unknown names and ask the user to fix the flag.

Write to `<workspace>/scope.yaml`.

Echo to the user:

> Wrote `<workspace>/scope.yaml`. Open it any time to tune the search.

### 1.5 Initialize `log.jsonl`

Create an empty `<workspace>/log.jsonl` if it doesn't exist. Append one
line for this run:

```json
{"ts":"<ISO-8601>","phase":"scope","action":"workspace_initialized","slug":"<slug>","scope":"<local|global>"}
```

For refreshed workspaces, just append the line.

## Handoff

For a fresh workspace or a **Fresh re-run**:

> Phase 1 done — scope captured at `<workspace>/scope.yaml`. Moving to search.

Pass forward to Phase 2 (Search): the workspace path and the parsed
`scope.yaml`. The flow then continues Search → Screen → Summarize.

For an existing workspace where the user chose **Maintain** (or `--force`):

> Existing workspace at `<workspace>` — running maintain (merge new
> findings, screen new entries, refresh summary).

Pass forward to Phase 5 (Maintain): the workspace path and the existing
`scope.yaml`.
