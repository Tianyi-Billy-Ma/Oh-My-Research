# Screening rubric for `/omr:literature-review`

This is the **reproducibility contract** for Phase 3 (Screen). The same
rubric version applied to the same corpus MUST produce the same verdicts.
No model "vibes": every verdict is the deterministic output of the rules
below. When you change any rule, bump `rubric_version` (see the bottom).

`rubric_version: lr-screen-1`

## Inputs

Per paper, read these fields from its `paper_bank.json` entry:

- `title`, `abstract` (or `notes` when no abstract), `year`, `venue`,
  `source`, `url`.
- Citation/usage signals **only if the source returned them** — never
  fetch them just to screen. Common carriers: a `citations` count if a
  source populated `notes`/`abstract` with one, or Zotero usage signals.

And these from `scope.yaml`:

- `research_question`
- `criteria.year_min`, `criteria.year_max`
- `criteria.include_preprints`, `criteria.include_workshop_papers`
- `criteria.min_citations`

## The four gates

Evaluate gates **in order**. Gates A–C are hard filters that can force
`excluded`. Gate D is a soft signal that can only push a borderline paper
into `review`. A paper that clears A–C with a clear relevance read is
`included`.

### Gate A — Recency window (hard)

- If `criteria.year_min` is set and `year` is present and `year <
  year_min` → **excluded**, reason `"older than year_min=<n>"`.
- If `criteria.year_max` is set and `year` is present and `year >
  year_max` → **excluded**, reason `"newer than year_max=<n>"`.
- If `year` is **missing/null**, the recency gate cannot decide: do not
  exclude on this gate alone. Carry a `year_unknown` mark into Gate D.

### Gate B — Source-quality tier (hard, criteria-driven)

Assign a tier from `venue` + `source`:

| Tier | Definition |
| --- | --- |
| `peer-reviewed` | Has a non-empty `venue` naming a journal or refereed conference (NeurIPS, ACL, JMLR, Nature, etc.) **and** is not flagged as a workshop. |
| `preprint` | arXiv / bioRxiv / SSRN / OpenReview-submission with no accepted venue; `venue` empty and `source` includes arXiv/HF, or URL is an arXiv abs page. |
| `workshop` | `venue` names a workshop (contains "workshop", "WS", or a co-located workshop tag). |
| `other` | Blog posts, GitHub READMEs, vendor pages, or anything that resolves to neither a paper venue nor a recognized preprint server. |

Tier ordering for downstream sorting: `peer-reviewed > preprint > workshop > other`.

Apply the criteria flags:

- Tier `preprint` **and** `criteria.include_preprints == false` →
  **excluded**, reason `"preprints disabled by scope"`.
- Tier `workshop` **and** `criteria.include_workshop_papers == false` →
  **excluded**, reason `"workshop papers disabled by scope"`.
- Tier `other` → **excluded**, reason `"non-paper source (tier: other)"`,
  UNLESS `source` includes `github` and the entry is explicitly an
  implementation the scope wanted (scope mentions "code"/"implementation")
  — then route to **review** with reason `"code artifact, not a paper"`.

Record the resolved tier in the verdict reason for auditability.

### Gate C — Relevance to scope (hard)

Score the paper's `title` + `abstract`/`notes` against
`scope.yaml.research_question` on a deterministic 3-level scale:

- **on-topic** — the abstract addresses the core subject of the research
  question (its primary method, problem, or domain). → relevance pass.
- **adjacent** — the paper touches a neighboring problem, shares a method,
  or is a likely "related work" cite but does not directly answer the
  question. → route to **review** unless a stronger include signal exists.
- **off-topic** — no substantive overlap with the research question. →
  **excluded**, reason `"off-topic vs research_question"`.

To keep this reproducible, decide the level by keyword/concept overlap
between the research question's salient terms and the title+abstract, not
by open-ended judgment. If the abstract is **missing entirely** and only a
title is available, cap relevance at **adjacent** (you cannot confirm
on-topic from a title alone) and route to `review`.

### Gate D — Citation / usage signal (soft, tie-breaker only)

This gate **never excludes on its own** and only applies to papers that
reached `review` from Gate C or carried `year_unknown` from Gate A.

- If `criteria.min_citations` is set **and** the source returned a citation
  count **and** count `< min_citations` → keep at **review**, reason
  appends `"; below min_citations"`. (Not excluded — low citations may
  just mean recent.)
- If `criteria.min_citations` is set, a count is present, and count `>=
  min_citations`, and Gate C was `adjacent` → promote `review` →
  **included** (strong usage signal compensates for adjacency).
- If no citation count was returned, leave the verdict unchanged. Never
  fabricate a count and never go fetch one.

## Verdict resolution

Combine the gates into exactly one verdict:

- Any hard exclusion (A, B, or C `off-topic`) → **excluded**.
- Gate C `on-topic`, clears A and B → **included**.
- Gate C `adjacent`, or `year_unknown`, or a Gate-D tie that stays
  unresolved → **review**.

Write the verdict object onto the entry's `screening` field:

```json
{"verdict":"included|excluded|review","reason":"<gate-cited reason>","rubric_version":"lr-screen-1"}
```

The `reason` MUST name the deciding gate(s) and the resolved tier, e.g.
`"Gate A: older than year_min=2015"` or `"Gate C: on-topic; tier:
peer-reviewed"`. This is what makes a verdict reproducible and auditable.

## Determinism rules

1. Same `rubric_version` + same entry fields ⇒ same verdict. If two runs
   disagree, that is a bug — the gates must be tightened, not the model
   re-rolled.
2. Never use information outside the entry's own fields and `scope.yaml`.
   No fresh web lookups, no citation fetches, no memory of prior runs.
3. Evaluate gates in the fixed order A → B → C → D and stop at the first
   hard exclusion.
4. Record the deciding gate in every `reason`.

## Versioning

`rubric_version` is a string, not the plugin version — it tracks the rubric
logic independently. Current: `lr-screen-1`. Bump to `lr-screen-2` (etc.)
whenever any gate's rule, threshold, or ordering changes. A re-run over an
existing workspace compares the corpus's stored `rubric_version` against
this file's value to decide whether existing verdicts must be recomputed
(see `03-screen.md` step 3.2).
