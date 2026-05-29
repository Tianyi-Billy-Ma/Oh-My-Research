# Phase 3 — Screen

**Goal:** apply a reproducible rubric to every paper in `paper_bank.json`,
writing a `screening` verdict (`included` / `excluded` / `review`) with a
gate-cited reason and a `rubric_version` onto each entry. This phase runs
**by default** in the full flow, between search and summarize. It is the
reproducibility layer the MVP left open.

The rubric itself — the gates, thresholds, and determinism rules — lives in
`${CLAUDE_PLUGIN_ROOT}/skills/literature-review/references/screening-rubric.md`.
Read it once, then apply it mechanically. This file is the procedure; that
file is the contract.

## Invariants

- **Every paper gets a verdict.** After this phase, no entry has
  `screening: null` — each carries `{verdict, reason, rubric_version}`
  conforming to `templates/paper_bank.schema.json`.
- **Verdicts are reproducible.** Same `rubric_version` + same corpus ⇒
  same verdicts. The `reason` field names the deciding gate so a human can
  re-derive the decision. No "I felt this one was relevant."
- **Screening reads only local evidence.** Entry fields + `scope.yaml`
  only. Never fetch citations or do fresh web lookups to screen — that
  would make verdicts non-reproducible and is a search-phase concern.
- **No fabrication.** Don't invent a year, venue, or citation count to push
  a verdict. Missing data routes a paper to `review`, never to a confident
  include/exclude.
- **Append-only corpus preserved.** Screening mutates the `screening`
  field in place; it never reorders, drops, or rewrites other fields.

## Steps

### 3.1 Load corpus, scope, and rubric

Read:
- `<workspace>/paper_bank.json` → `papers[]`.
- `<workspace>/scope.yaml` → `research_question` and the full `criteria`
  block (`year_min`, `year_max`, `include_preprints`,
  `include_workshop_papers`, `min_citations`).
- `${CLAUDE_PLUGIN_ROOT}/skills/literature-review/references/screening-rubric.md`
  → the gates and the current `rubric_version`.

If `papers[]` is empty, halt with:

> Nothing to screen — `paper_bank.json` has no entries. Re-run search or
> check `log.jsonl`.

### 3.2 Decide which entries to screen

- **Fresh run / full flow:** screen every entry.
- **Maintain re-run (Phase 5 calls back here):** screen only entries whose
  `screening` is `null` (newly added), UNLESS the corpus's stored
  `rubric_version` differs from the rubric file's current
  `rubric_version` — in that case re-screen **all** entries so the whole
  corpus is consistent under one rubric version. Phase 5 tells you which
  mode it wants; default to "newly added only."

### 3.3 Apply the rubric per entry

For each entry to screen, walk Gates A → B → C → D from
`screening-rubric.md` in that fixed order, stopping at the first hard
exclusion. Produce exactly one verdict object:

```json
{
  "verdict": "included",
  "reason": "Gate C: on-topic; tier: peer-reviewed",
  "rubric_version": "lr-screen-1"
}
```

Rules carried over from the rubric (do not re-derive — cite them):

- The `reason` MUST name the deciding gate and the resolved source tier.
- A paper missing its `year` cannot be excluded by Gate A alone.
- A paper with only a title (no abstract/notes) caps at `adjacent` → `review`.
- `min_citations` and other citation logic apply **only** when the source
  actually returned a count; never fetch one.

Set the entry's `screening` field to the verdict object. Leave all other
fields untouched.

### 3.4 Write the screened corpus

Write `paper_bank.json` atomically (tmpfile + rename), same pattern as
Phase 2's 2.5. With `jq`:

```bash
jq --argjson screened "$SCREENED" \
   '.papers = $screened | .last_updated_at = (now | todate)' \
   "<workspace>/paper_bank.json" > "<workspace>/paper_bank.json.tmp"
mv "<workspace>/paper_bank.json.tmp" "<workspace>/paper_bank.json"
```

If `jq` is unavailable, use a Python `json` one-liner. Either way: atomic,
never a partial write. Re-validate the file against
`templates/paper_bank.schema.json` after writing — the `screening` object
is now non-null and must satisfy its required keys (`verdict`, `reason`,
`rubric_version`).

### 3.5 Log the screening pass

Append one summary line to `log.jsonl`:

```json
{"ts":"<ISO>","phase":"screen","action":"screened","rubric_version":"<v>","included":<int>,"excluded":<int>,"review":<int>,"rescreened_all":<bool>}
```

If any paper was excluded purely for missing data the user might want to
fix (e.g. tier `other` that could be a mis-parsed paper), note the count —
but do not prompt mid-phase; the review queue surfaces in Phase 4.

### 3.6 Report

Print a one-line summary to the user:

> Screen done — `<included>` included, `<excluded>` excluded, `<review>`
> need review (rubric `<rubric_version>`). Reasons logged per entry in
> `paper_bank.json`. Moving to summarize.

## Handoff

> Phase 3 done — every paper carries a screening verdict
> (`<included>`/`<excluded>`/`<review>`) under rubric `<rubric_version>`.
> Moving to summarize.

Pass forward to Phase 4 (Summarize): the workspace path and the screened
`paper_bank.json`. Phase 4 consumes **only** `included` entries.
