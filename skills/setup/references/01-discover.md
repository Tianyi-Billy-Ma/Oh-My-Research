# Phase 1 — Discover

**Goal:** build an authoritative list of MCP servers declared by this plugin,
each annotated with its transport and the env var that holds its token.
Subsequent phases consume this list — don't hard-code server names here.

## Steps

### 1.1 Read `.mcp.json`

Read `${CLAUDE_PLUGIN_ROOT}/.mcp.json`. If it's missing or malformed, stop and
tell the user:

> `.mcp.json` is missing or invalid. The omr install looks broken — try
> reinstalling the plugin (`/plugin reinstall omr` or equivalent) before
> rerunning `/omr:setup`.

Do not attempt to repair `.mcp.json` from this skill.

### 1.2 Classify each server

For every key under `mcpServers`, build a record with these fields:

| Field | How to derive |
| --- | --- |
| `name` | the key (e.g. `exa`, `github`) |
| `transport` | `http` if the entry has `"type": "http"`, else `stdio` |
| `env_var` | see 1.3 |

### 1.3 Resolve the env var name

- **HTTP servers**: parse the `headers.Authorization` field (or any other
  header) for a `${VAR_NAME}` placeholder. That `VAR_NAME` is the env var.
  Example: `"Authorization": "Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}"` →
  `GITHUB_PERSONAL_ACCESS_TOKEN`.
- **Stdio servers** routed through `bin/load-env-and-exec.sh`: the shim
  doesn't encode the var name. Use this lookup table — kept here, not in
  Phase 2, so Phase 2 stays purely about presence checking:

  | Server (`args`) | Env var |
  | --- | --- |
  | `exa-mcp-server` | `EXA_API_KEY` |
  | `tavily-mcp` | `TAVILY_API_KEY` |
  | `@brave/brave-search-mcp-server` | `BRAVE_API_KEY` |

  If you encounter a stdio server whose `args` aren't in this table, fall
  back to reading the README's "Bundled MCPs" section
  (`${CLAUDE_PLUGIN_ROOT}/README.md`). The README is the canonical source;
  this table is a fast path. If still no match, label the env var as
  `UNKNOWN` and surface it in the Phase 2 status table — don't guess.

### 1.4 Emit the discovery summary

Print a short summary so the user knows what you're going to audit. No
secrets, no probes yet — just the declared shape:

```
Discovered 5 MCP server(s):
  exa            stdio   env: EXA_API_KEY
  tavily         stdio   env: TAVILY_API_KEY
  brave-search   stdio   env: BRAVE_API_KEY
  github         http    env: GITHUB_PERSONAL_ACCESS_TOKEN
  huggingface    http    env: HF_TOKEN
```

## Handoff

Hand the records to Phase 2. Echo one line:

> Phase 1 done — discovered N servers. Moving to audit.
