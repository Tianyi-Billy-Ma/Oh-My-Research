# Source priority for `/omr:literature-review`

Default search chain (knowledge-base-first). Phase 2 walks this list in
order; each source either contributes hits or is skipped silently.

## Default chain

1. **Zotero** (via `mcp__zotero__*`) — the user's curated library.
   Strongest signal; what they've already decided is worth keeping.
   Skipped silently if the Zotero MCP isn't loaded in this session.
2. **Local PDFs** — globs `papers/**/*.pdf`, `literature/**/*.pdf`, plus
   any sibling `.omr/literature/*/paper_bank.json` files. The latter
   lets reviews on related topics build on each other.
3. **MCPs** (in this order):
   - **Exa** (`mcp__exa__*`) — best general academic / web search.
   - **Tavily** (`mcp__tavily__*`) — broad coverage; useful as a
     cross-check on Exa.
   - **Brave Search** (`mcp__brave-search__*`) — independent index;
     fills gaps the other two miss.
   - **Hugging Face** (`mcp__huggingface__paper_search`) — ML papers
     keyed by arXiv ID. Strong for AI/ML topics, sparse elsewhere.
   - **GitHub** (`mcp__github__*`) — search repos that reference the
     topic. Surfaces implementations, not papers per se; useful when
     `scope.yaml.criteria` cares about code availability.
4. **Web** — `WebSearch` + `WebFetch`. Targeted at arXiv, DOI
   resolution, openreview.net, and publisher pages. Use this last
   because it's slowest and least structured.

## Override

`--sources: a,b,c` on the command line overrides the default chain.
Valid names: `zotero`, `local`, `exa`, `tavily`, `brave-search`,
`huggingface`, `github`, `web`. Unknown names halt with a clarifying
message; don't silently drop them.

Examples:
- `--sources zotero, exa` — knowledge base + Exa only.
- `--sources web` — pure web search; skip everything else.
- `--sources exa, github` — Exa for papers + GitHub for adjacent code.

## Graceful degradation

A source can be unreachable for several reasons:

- MCP not loaded (Zotero).
- Required token missing (`EXA_API_KEY`, `TAVILY_API_KEY`, etc — see
  `omr:setup`).
- Network or service outage (web).
- Local paths don't exist (`papers/`, `literature/`).

In every case: log the gap to `log.jsonl` and move on. Don't ask the
user to fix it mid-run; surface it in the final summary if needed.

If **every** configured source is unreachable, Phase 2 halts and refers
the user to `/omr:setup --audit`.

## Per-source query strategy

### Zotero

- Use `mcp__zotero__zotero_search_items` with the research question's
  keyword variants.
- Also enumerate `zotero_get_collections` and pull items from any
  collection whose name matches the topic (substring, case-insensitive).
- Pull annotations (`zotero_get_annotations`) for hits the user marked
  highly — these become first-class candidates because the user's
  highlights signal importance.

### Local PDFs

- Glob the configured paths. Hard cap: 20 PDFs per run (read first 3
  pages each).
- Extract title, abstract, authors via `pdfminer` or `pdftotext`. If
  neither is available, fall back to metadata-only and log.
- For prior `.omr/literature/*/paper_bank.json` files: read the
  `papers[]` array and add entries whose abstracts mention the topic
  keywords.

### Exa / Tavily / Brave

- Dispatch the research question + 2–3 keyword reformulations in
  parallel. Take top 10 per source.
- Prefer hits with structured metadata (DOI in URL, arXiv ID,
  author/year in snippet) over generic web results.

### Hugging Face papers

- `mcp__huggingface__paper_search` with the topic. arXiv IDs come
  through cleanly; abstracts are reliable.

### GitHub

- Search for repos with the topic in description or README. Pull the
  README of the top 5 hits; if a README cites a paper (`arxiv.org`,
  `doi.org`), add the paper as a candidate with `source: "github"`
  and the repo URL in `notes`.

### Web

- Targeted queries: `site:arxiv.org <topic>`, `site:openreview.net
  <topic>`, plus a generic `<topic> survey paper`.
- For each hit, try to resolve to a canonical paper page via DOI or
  arXiv link in the HTML. Skip blog posts unless the user's scope
  explicitly allows them.

## Multi-source dedup

When the same paper appears from multiple sources:

- Keep the entry whose first appearance came earliest in the source
  chain.
- Update its `source` field to a comma-joined list in order of
  appearance (e.g. `"zotero,exa,web"`).
- Merge metadata: prefer non-null values from later sources where the
  first source left a field empty.
- Log the merge:

  ```json
  {"ts":"<ISO>","phase":"search","action":"merged","id":"<canonical>","sources":["zotero","exa"]}
  ```
