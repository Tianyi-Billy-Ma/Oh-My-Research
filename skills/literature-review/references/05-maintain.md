# Phase 5 — Maintain

**Goal:** idempotently refresh an existing literature workspace. Merge NEW
findings into the existing `paper_bank.json` (append-only, dedup by
canonical `id`), screen only what's new, and regenerate `summary.md`'s
marker block — without disturbing the user's prior decisions.

This phase is the entry point when a workspace **already exists** and the
user chooses "maintain / refresh" over "fresh" (see SKILL.md and
`01-scope.md` 1.2). It composes Phases 2–4 with tighter guardrails rather
than re-running them blindly.

## Invariants

- **Append-only, dedup by `id`.** New search hits merge into the existing
  `papers[]`. An incoming entry whose canonical `id` already exists is a
  duplicate — merge metadata (fill empty fields, comma-join `source`),
  never create a second row, never reorder existing rows.
- **Don't re-flip settled verdicts.** Existing entries keep their
  `screening` verdict untouched UNLESS the `rubric_version` changed (see
  3.2). New entries get screened from scratch. The user's manual edits to
  verdicts survive a maintain run at the same rubric version.
- **Idempotent.** Running maintain twice with no new findings is a no-op
  beyond a log line: same corpus, same verdicts, same summary block.
- **All MVP safety rails still apply** (never fabricate, `url` mandatory,
  `authors[]` array, AskUserQuestion for every prompt).

## Steps

### 5.1 Confirm the maintain target

The workspace path arrives from `01-scope.md` (existing-workspace branch).
Read `<workspace>/scope.yaml` — it is the source of truth; do **not**
re-prompt scoping fields. Read the existing `<workspace>/paper_bank.json`
and build `seen_ids` from its entries.

Snapshot pre-run counts for the idempotency report: total papers, and the
included/excluded/review split.

### 5.2 Search for new findings (delegate to Phase 2)

Re-enter `${CLAUDE_PLUGIN_ROOT}/skills/literature-review/references/02-search.md`
in **append mode**:

- Use the same `scope.yaml.sources` (or `--sources` override if the user
  passed one on this invocation).
- Honor `--from-existing` if passed this run — its import (2.1a) merges
  the same way, deduped against `seen_ids`.
- Every new hit is deduped against `seen_ids`. Genuinely new entries get
  `screening: null` (Phase 2 always does this). Already-present `id`s
  merge metadata only.
- Respect `max_papers` as the cap on the **total** corpus, not per-run.

Track the set of `id`s that are new this run (`new_ids`) — Phase 3 needs it.

### 5.3 Screen only the new entries (delegate to Phase 3)

Re-enter `${CLAUDE_PLUGIN_ROOT}/skills/literature-review/references/03-screen.md`
in **maintain mode** (its 3.2):

- **Default:** screen only entries whose `screening` is `null` (i.e.
  `new_ids`). Existing verdicts are not touched.
- **Rubric-version drift:** compare the `rubric_version` stored on existing
  entries against the current value in `screening-rubric.md`. If they
  differ, re-screen **all** entries so the whole corpus is consistent under
  one rubric version, and note it in the log (`rescreened_all: true`).
  Before doing a full re-screen that could flip user-visible verdicts, ask
  via `AskUserQuestion`:

  > The screening rubric changed (`<old>` → `<new>`). Re-screen the entire
  > corpus (may change existing verdicts), or screen only new papers under
  > the old rubric for now?

  Options: `Re-screen all (recommended)` / `New papers only`.

### 5.4 Refresh the summary marker block (delegate to Phase 4)

Re-enter `${CLAUDE_PLUGIN_ROOT}/skills/literature-review/references/04-summarize.md`.
It already handles the idempotent marker block: it replaces the content
between `<!-- BEGIN omr:lit-review ... -->` and `<!-- END omr:lit-review -->`
in place and preserves everything outside it. Re-render from the current
`included` set across all `scope.yaml.output_languages`.

If nothing changed in the corpus (no new included papers, no verdict
flips), Phase 4 still re-renders the block at the current
`{{omr_version}}`; the result is byte-stable, which keeps maintain
idempotent.

### 5.5 Log and report the diff

Append to `log.jsonl`:

```json
{"ts":"<ISO>","phase":"maintain","action":"maintained","new_papers":<int>,"new_included":<int>,"new_review":<int>,"new_excluded":<int>,"rescreened_all":<bool>}
```

Print the maintain diff to the user:

```
omr:literature-review — maintain done.

  Before:  <n0> papers (<inc0> incl / <exc0> excl / <rev0> review)
  After:   <n1> papers (<inc1> incl / <exc1> excl / <rev1> review)
  Added:   <new_papers> new this run; <new_included> passed screening
  Summary: refreshed marker block in summary.md (+ per-language files)
```

If `new_papers == 0` and no verdicts changed, say so explicitly:

> No new findings since last run — corpus and summary unchanged.

## Handoff

> Phase 5 done — corpus merged (`<new_papers>` new), new entries screened,
> summary refreshed. Workspace at `<workspace>`.

This is the terminal phase for a maintain run. Stop here.
