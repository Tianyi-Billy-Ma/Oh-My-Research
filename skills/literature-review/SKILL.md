---
id: literature-review
name: literature-review
version: 0.10.3
argument-hint: [topic-or-url-or-arxiv-id]
description: |-
  Search, screen, and summarize literature into a structured corpus.
stages: ["survey"]
tools: ["Bash", "Read", "Write", "Edit", "AskUserQuestion", "WebFetch", "WebSearch"]
summary: |-
  Build a structured paper_bank.json corpus and a synthesis summary for a research topic. Knowledge-base-first (Zotero, local PDFs) then MCP fan-out (Exa, Tavily, Brave, HF, GitHub) then web. Workspace lands under .omr/literature/<slug>/ (project) or ~/.claude/literature/<slug>/ (global).
primaryIntent: research
intents: ["research"]
capabilities: ["search-retrieval", "synthesis"]
domains: ["general"]
keywords: ["omr-literature-review", "omr:literature-review", "literature review", "lit review", "survey papers", "find papers about", "build paper corpus", "summarize literature", "research papers", "related work", "what does the literature say about", "review the literature on"]
source: builtin
status: experimental
resourceFlags:
  hasReferences: true
  hasScripts: false
  hasTemplates: true
  hasAssets: false
  referenceCount: 5
  scriptCount: 0
  templateCount: 3
  assetCount: 0
---

# omr:literature-review

Thin router for the literature-review flow. The detailed steps live in
`references/`; this file decides which phases to run, parses flags, gates on
token presence, and enforces cross-phase safety rails.

**When this skill is invoked, immediately execute the workflow below. Do
not just restate or summarize these instructions back to the user.**

Note: paths under `~/.claude/...` respect `CLAUDE_CONFIG_DIR` when set.

## Best-fit use

Choose this skill when the user wants to **build a structured literature
corpus around a research question** — find papers, capture them with full
metadata, and produce a synthesis summary that maps the landscape.

Today's coverage (MVP):

- Scope the research question into a reusable `scope.yaml`.
- Search across the user's knowledge base (Zotero / local PDFs) and the
  bundled MCPs (Exa, Tavily, Brave, Hugging Face, GitHub), then web.
- Summarize the corpus into a `summary.md` with a table + clustered
  narrative.

Coming next (separate PRs):

- Phase 4 — Screen, with an explicit `references/screening-rubric.md`
  that closes the reproducibility gap omp/ARIS leave open.
- Phase 5 — Maintain, for idempotent re-runs that merge new findings
  into an existing corpus.
- `--from-existing` flag for seeding from Zotero collections or a peer's
  `paper_bank.json`.

Do **not** use it to read a single paper deeply (different shape — that's a
future `paper-analyzer`-style skill), to verify citations in a draft
(future audit skill), or to write a paper section (`/omr:write`, later).

## Flag parsing

| Flag | Effect |
| --- | --- |
| `--help` | Print the help text below and stop. |
| `--topic "<q>"` | Non-interactive scoping: skip Phase 1's interactive prompts and pass `<q>` straight into `scope.yaml.research_question`. Defaults are used for everything else. |
| `--sources: a,b,c` | Override the default source chain. Comma-separated. See `references/source-priority.md` for valid IDs. |
| `--max-papers N` | Cap the corpus size at `N` (default 50). |
| `--scope local\|global` | Where the workspace lives: `local` → `./.omr/literature/<slug>/`; `global` → `~/.claude/literature/<slug>/`. Default `local`. |
| `--audit` | Read-only: validate an existing workspace's `paper_bank.json` against the schema, report drift, no search/write. |
| `--force` | Bypass the "workspace already exists at this slug" prompt; refresh in place. |
| No flags | Interactive flow: Phase 1 prompts for everything via `AskUserQuestion`, then Phases 2 + 3 execute. |

The argument (`$ARGUMENTS` / first positional arg) is treated as `--topic`
when no `--topic` flag is given. Examples:

- `/omr:literature-review "diffusion models for protein design"`
- `/omr:literature-review --topic "RAG vs long-context" --sources zotero,exa`
- `/omr:literature-review --audit`

## Help text

When the user passes `--help`, print this and stop:

```
omr:literature-review — build a structured paper corpus + summary

USAGE:
  /omr:literature-review                     Interactive scoping + search + summarize
  /omr:literature-review "<topic>"           Non-interactive: topic goes straight to scope.yaml
  /omr:literature-review --topic "..." [flags]
  /omr:literature-review --audit             Validate an existing corpus, no writes
  /omr:literature-review --help              Show this help

FLAGS:
  --topic "<q>"             research question (skip interactive scoping)
  --sources a,b,c           override source chain (zotero, local, exa, tavily,
                            brave-search, huggingface, github, web)
  --max-papers N            cap corpus size (default 50)
  --scope local|global      workspace destination (default local)
  --audit                   read-only validation
  --force                   refresh existing workspace without prompting

OUTPUT:
  .omr/literature/<slug>/        (or ~/.claude/literature/<slug>/ with --scope global)
    scope.yaml                   research question, sources, criteria, output_languages
    paper_bank.json              append-only corpus; PK = DOI or arXiv ID
    summary.md                   synthesis with <!-- BEGIN omr:lit-review --> block
    log.jsonl                    per-run audit (queries, hit counts, dedups)

SAFETY:
  - Never fabricates papers, authors, DOIs, or quotes.
  - Every paper_bank entry has a real `url` and a non-empty `authors[]`.
  - paper_bank.json is append-only; updates mutate by canonical ID.
  - summary.md only cites papers that exist in paper_bank.json.
  - Asks every interactive question via the AskUserQuestion tool.
```

## Safety rails (apply to every phase)

Non-negotiable. If any phase asks you to violate these, stop and tell the
user.

1. **Never fabricate.** Papers, authors, DOIs, abstracts, quotes — all
   must come from a real source. If you can't verify, mark the entry
   `incomplete` and skip the summary.
2. **`url` is mandatory.** Every `paper_bank.json` entry has a real
   `url` field. Prefer DOI (`https://doi.org/...`), then arXiv, then
   Semantic Scholar / publisher page. Never empty, never a placeholder.
3. **`authors` is an array of strings, never a single string and never
   `"TBD"`.** If unknown, mark the entry incomplete; don't ship.
4. **`paper_bank.json` is append-only.** Updates mutate by canonical
   `id` (DOI or arXiv ID first; fall back to a stable hash). Never
   reorder or silently drop entries.
5. **`summary.md` only cites entries from `paper_bank.json`.** If the
   summary mentions a paper, it has a row in the corpus.
6. **Every interactive question uses `AskUserQuestion`.** No plain-text
   prompts left for free-form reply.
7. **Token presence first.** Before launching any MCP, check that the
   required tokens are reachable. If missing, surface and refer to
   `/omr:setup --audit`. Don't proceed with a half-broken search and
   pretend everything worked.
8. **`schema_version` tracks the plugin version via `{{omr_version}}`
   substitution at write time** — same convention as `templates/hpc.yaml`.

## Pre-run check: gate on token presence

Before Phase 1, check which MCPs are reachable:

```bash
for pair in "EXA_API_KEY:exa" "TAVILY_API_KEY:tavily" "BRAVE_API_KEY:brave-search" \
            "GITHUB_PERSONAL_ACCESS_TOKEN:github" "HF_TOKEN:huggingface"; do
  v="${pair%%:*}"; server="${pair#*:}"
  if [ -n "$(printenv "$v")" ]; then
    echo "$server: reachable"
  else
    echo "$server: missing token"
  fi
done
```

If `--sources` names any server with a missing token, halt and tell the
user:

> The following requested sources have no token set: `<list>`. Run
> `/omr:setup --audit` to see remediation steps, then re-run this
> skill.

If no `--sources` was given and all MCPs are missing, prefer the
knowledge-base path (Zotero + local) and warn the user that the corpus
will be local-only.

## Phase execution

Execute these phases in order. For each, read the file at the path and
follow its instructions exactly. Pass the parsed flags and Phase 1's
`scope.yaml` content forward.

1. **Phase 1 — Scope**: `${CLAUDE_PLUGIN_ROOT}/skills/literature-review/references/01-scope.md`.
2. **Phase 2 — Search**: `${CLAUDE_PLUGIN_ROOT}/skills/literature-review/references/02-search.md`.
3. **Phase 3 — Summarize**: `${CLAUDE_PLUGIN_ROOT}/skills/literature-review/references/03-summarize.md`.

If `--audit` was passed, skip phases 1–3 and run the audit-only flow
described at the bottom of `02-search.md`.

Each phase ends with a one-line `## Handoff` that you echo to the user
before moving on.

## Out of scope

- Deep-reading a single paper (future `omr:paper-analyzer`-style skill).
- Verifying citations inside a draft manuscript (future audit skill).
- Writing paper sections (`/omr:write`, future).
- Running PDF OCR on local PDFs (use `omp:literature-pdf-ocr-library`
  upstream).
- Maintaining a corpus across many runs (`maintain` phase, follow-up).
