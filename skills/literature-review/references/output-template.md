# Output template for `summary.md`

The scaffold lives at `templates/summary.md`. This document defines the
column conventions, narrative structure, and length budget that Phase 3
must follow.

## Table

Use exactly these columns:

| Paper | Venue | Year | Approach | Key finding | Limitation | Relevance |

Per-column rules:

- **Paper** — `[Title](url)`. The URL comes from the corpus entry's
  `url` field; never a different link.
- **Venue** — conference / journal short name (e.g. `NeurIPS`, `ACL`,
  `JMLR`). Blank for preprints; mark `(preprint)` in the Year column
  if helpful.
- **Year** — integer. `?` only if the corpus entry has `year: null`.
- **Approach** — 3–12 words describing the method or angle. Be
  specific (`"sparse-attention finetune"` beats `"new method"`).
- **Key finding** — one-line claim or quantitative result. Cite the
  paper's own claim; don't add your own interpretation.
- **Limitation** — one honest line on what the paper does *not* show or
  where it stops. Pull from the paper's own limitations section when
  available; otherwise mark `unclear`.
- **Relevance** — short note tying the paper to
  `scope.yaml.research_question`. This is the only column where Phase
  3's judgment shows; keep it factual.

## Grouping

Rows are grouped by cluster (sub-heading `### <cluster name>`). Within a
cluster, sort by year descending. Mark the foundational paper for each
cluster — either the oldest cited or the canonically named one — with
`★` in the Paper column.

## Narrative structure (after the table)

Four sections, in this order:

1. **Landscape** — name the 2–4 clusters explicitly. 2–3 sentences each.
   Explain the clustering criterion (method family, problem variant,
   etc.) so re-runs can reproduce the grouping rationale.
2. **Methods** — what techniques dominate; what assumptions they share.
   Cite specific papers inline via `[Title](url)`.
3. **Findings** — where evidence converges; where it diverges. Mark
   uncertain claims explicitly.
4. **Open questions** — 3–6 bullets. These will feed `/omr:ideate`
   (future skill); write them as questions, not statements.

## Length budget

- **Total**: 500–1500 words *excluding the table*. Tighter is better.
- **Each cluster intro**: 2–3 sentences.
- **Methods / Findings**: 2–4 paragraphs each.
- **Open questions**: 3–6 bullets.

If the corpus is small (<10 papers), aim for the lower end; the
narrative shouldn't exceed the evidence base.

## Tone

- **Tied to evidence.** Every claim cites a paper from
  `paper_bank.json` by `[Title](url)`.
- **No filler.** No "This paper is interesting because…". State the
  contribution.
- **Mark uncertainty.** If a paper's claim hasn't been independently
  reproduced, say so. Honesty about confidence levels is more valuable
  than confident-sounding summary.
- **No editorial opinion.** Don't recommend papers as "must-reads";
  describe what they show and let the user decide.

## Bilingual output

If `scope.yaml.output_languages` includes a language beyond `en`,
generate `summary.<lang>.md` alongside `summary.md`. Translate the
narrative; **never translate paper titles, author names, venue names,
or URLs.** The table stays in the original language for those fields.
Don't add or remove analysis in translation.
