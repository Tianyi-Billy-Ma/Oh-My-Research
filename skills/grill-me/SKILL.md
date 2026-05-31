---
id: grill-me
name: grill-me
version: 0.15.0
argument-hint: [idea-or-plan-or-paper-path]
description: |-
  Relentlessly stress-test a research idea, hypothesis, or plan against your literature corpus and a reviewer rubric before you commit to it.
stages: ["ideation"]
tools: ["Bash", "Read", "Grep", "Glob", "AskUserQuestion"]
summary: |-
  A reviewer/committee-style grilling: interrogates a research idea, hypothesis, experimental design, or paper argument one question at a time, grounding every challenge in your literature-review corpus (paper_bank.json + summary.md) and project files rather than vibes. Walks the decision tree branch by branch, offers a recommended answer per question, and ends with a sharpened statement + ranked open risks. A pre-commitment gate that pairs with /omr:ideate and /omr:plan.
primaryIntent: research
intents: ["research", "evaluation"]
capabilities: ["evaluation-benchmarking", "research-planning"]
domains: ["general"]
keywords: ["omr-grill-me", "omr:grill-me", "grill me", "grill my idea", "stress-test my plan", "poke holes in my idea", "play devil's advocate", "mock defense", "defend my research", "challenge my hypothesis", "reviewer grilling", "red-team my plan"]
source: builtin
status: experimental
resourceFlags:
  hasReferences: false
  hasScripts: false
  hasTemplates: false
  hasAssets: false
  referenceCount: 0
  scriptCount: 0
  templateCount: 0
  assetCount: 0
---

# omr:grill-me

Stress-test a research idea, hypothesis, experimental design, or paper
argument by interrogating it the way a sharp PhD committee or a tough
reviewer would — one question at a time, every challenge grounded in
evidence, until the idea is either sharpened into something defensible or
revealed as not yet ready.

**When this skill is invoked, immediately execute the workflow below. Do
not just restate or summarize these instructions back to the user.**

This is the adversarial counterpart to ideation: `/omr:ideate` *generates*
directions; `grill-me` *attacks* one until only the strong parts survive.

## Best-fit use

Choose this skill when the user wants to **pressure-test something before
committing effort to it** — a research direction, a hypothesis, an
experimental design, a paper's central claim, or a grant angle. Run it
after `/omr:ideate` (grill the chosen direction) or before `/omr:plan`
(make sure the idea survives scrutiny before you plan experiments around
it).

Do **not** use it to *generate* ideas (that's `/omr:ideate`), to build the
literature corpus (that's `/omr:literature-review`), or to write prose
(that's `/omr:write`, later). Grill-me assumes you already have a thing to
defend.

## Flag parsing

| Flag | Effect |
| --- | --- |
| `--help` | Print the help text below and stop. |
| `--target "<text>"` | The idea/plan/claim to grill, inline. If omitted, the positional argument is used; if both absent, ask for it via `AskUserQuestion` (with a free-form "Other"). |
| `--corpus <slug>` | Grill against a specific literature-review corpus at `./.omr/literature/<slug>/`. If omitted, auto-discover corpora (see Evidence gathering) and, if more than one exists, ask which to grill against. |
| `--paper <path>` | Grill the central claim of a paper/draft at `<path>` (a `.md`/`.tex` file) instead of a free-text idea. |
| `--rounds N` | Soft cap on the number of grilling questions (default: keep going until the decision tree is resolved or the user calls it). |
| `--lens reviewer\|committee\|red-team` | Grilling persona (default `reviewer`). See Grilling lenses. |

## Help text

When the user passes `--help`, print this and stop:

```
omr:grill-me — stress-test a research idea/plan against your corpus + a rubric

USAGE:
  /omr:grill-me "<idea or claim>"          Grill an inline idea
  /omr:grill-me --paper paper/main.tex     Grill a draft's central claim
  /omr:grill-me --corpus rag-vs-long-ctx   Grill against a specific corpus
  /omr:grill-me --lens committee           Pick the grilling persona
  /omr:grill-me --help                     Show this help

WHAT IT DOES:
  Reads your literature corpus (.omr/literature/<slug>/) and project files,
  then interrogates your idea ONE question at a time — novelty vs the
  corpus, feasibility, methodology, baselines, evaluation, threats to
  validity. Each question comes with a recommended answer. Ends with a
  sharpened statement of the idea + a ranked list of unresolved risks.

LENSES:
  reviewer   (default) a tough but fair conference reviewer
  committee  a PhD thesis committee probing depth and rigor
  red-team   an adversary actively trying to break the idea

It asks via the AskUserQuestion tool, never free-text prompts, and never
fabricates papers or results to make a point.
```

## Safety rails

1. **Ground every challenge in evidence, never vibes.** A novelty or
   prior-work challenge must cite a real entry from the corpus
   (`paper_bank.json`) or a real project file. If you can't ground it,
   frame it as an open question, not a fact. Never invent a paper, author,
   result, or quote to strengthen a challenge.
2. **Every question goes through `AskUserQuestion`.** One question at a
   time. Provide a **recommended answer** as the first option, plus 1–3
   genuine alternative stances, and rely on the tool's "Other" for
   free-form. Never paste a question into the chat and wait for a reply.
3. **One question at a time; wait for the answer before the next.** Do not
   batch. Let each answer steer which branch of the decision tree you walk
   next.
4. **Explore before asking.** If a question can be answered by reading the
   corpus, the config, or the project files, read them instead of asking.
   Redundant questions erode trust.
5. **Grill to sharpen, not to win.** The goal is a stronger idea or an
   honest "not ready," not a debate victory. When the user gives a good
   answer, register it and move on; don't re-litigate settled points.
6. **No code, no writes to research artifacts.** This skill is
   read-and-interrogate only. It may write its final summary to a file
   *if the user asks*, but it never edits the corpus, the paper, or config.

## Workflow

### 1. Resolve the target

Establish *what* is being grilled (the `--target` text, the `--paper`
file's central claim, or — if neither — ask via `AskUserQuestion`: "What
should I grill — a research idea, a hypothesis, an experimental design, or
a paper's central claim?"). Restate it back in one sentence and confirm
you've got it right before grilling (one `AskUserQuestion`: "Is this the
claim I should attack? <restatement>" → Yes / Refine it / Other).

### 2. Gather evidence (explore, don't ask)

Read what's available so the grilling is grounded:

- **Corpus**: `./.omr/literature/<slug>/paper_bank.json` + `summary.md`.
  If `--corpus` is set, use it. Otherwise glob `./.omr/literature/*/` for
  corpora; if exactly one, use it; if several, ask which; if none, say so
  and grill on reasoning alone (note that novelty challenges will be
  weaker without a corpus, and suggest `/omr:literature-review` first).
- **Config**: `./.omr/config.yaml` for `author`, default model, etc.
- **Project**: relevant code/docs (`Grep`/`Glob`) when the idea touches an
  existing implementation.

Summarize in one line what evidence you have ("Grilling against the
`rag-vs-long-context` corpus, 38 papers") before the first question.

### 3. Pick the lens

`--lens` (default `reviewer`). Each lens changes the *posture*, not the
rubric:
- **reviewer** — fair but tough; "would I accept this at a top venue?"
- **committee** — depth and rigor; "do you understand *why*, not just
  *what*?"
- **red-team** — adversarial; actively constructs the strongest case the
  idea is wrong/unoriginal/infeasible.

### 4. Grill — walk the decision tree

Interrogate one question at a time via `AskUserQuestion`, walking down
each branch and resolving dependencies between decisions before moving on.
Cover these dimensions (skip ones the evidence already settles):

- **Novelty vs the corpus** — which specific `paper_bank.json` entries are
  closest? How does this differ, concretely? What must it beat?
- **Feasibility** — data, compute (`.omr/hpc/` if relevant), time, skills.
  What's the riskiest assumption?
- **Methodology** — is the approach sound? What confound or leakage could
  invalidate it?
- **Baselines** — what are the honest baselines (from the corpus)? Is the
  comparison fair?
- **Evaluation** — what metric actually measures success? What would
  falsify the hypothesis?
- **Scope** — is this one paper or five? What's the minimal defensible
  contribution?
- **Threats to validity** — internal, external, construct. What's the
  reviewer's likely rejection reason?

For each question: state your **recommended answer** (option 1), give real
alternatives, and let the user pick or "Other". When an answer exposes a
new dependency, follow that branch next.

### 5. Close — sharpened statement + ranked risks

When the tree is resolved (or the user calls it / `--rounds` hit), stop
grilling and produce:

```
Sharpened claim:
  <one-paragraph restatement incorporating what survived the grilling>

Resolved:
  - <decision> → <what the user committed to>

Open risks (ranked):
  1. [HIGH] <risk> — <why it matters> — <what would resolve it>
  2. [MED]  ...

Verdict: <ready to plan / needs more evidence / reconsider>  (with one-line reason)
```

If the verdict is "ready to plan," point at `/omr:plan`. If "needs more
evidence," point at `/omr:literature-review` (to fill the specific gap) or
a small probe experiment. Offer (via `AskUserQuestion`) to save this block
to `./.omr/grill/<slug>.md` — only write it if the user says yes.

## Out of scope

- Generating new ideas (`/omr:ideate`).
- Building the literature corpus (`/omr:literature-review`).
- Writing or editing the paper (`/omr:write`, later).
- Running experiments (`/omr:experiment`, later).
