---
name: setup
description: |
  Initialize Oh-My-Research (omr): check tokens for the bundled MCP servers
  (Exa, Tavily, Brave Search, GitHub, Hugging Face), scaffold a project-local
  `.env` from `.env.example` when missing, and verify each server is reachable.
  Use when the user says "omr-setup", "omr:setup", "setup omr", "set up
  Oh-My-Research", "configure omr keys", or otherwise asks to install /
  configure / health-check this plugin.
---

# omr:setup

Configure Oh-My-Research after install. The goal is to leave the user with a
session where every MCP server they want is reachable, and to tell them
unambiguously which ones aren't yet — without ever printing secrets to the
chat.

## What this skill is responsible for

1. Enumerate the MCP servers declared in `${CLAUDE_PLUGIN_ROOT}/.mcp.json`.
2. Detect whether each server's token is available from **either** the
   inherited shell env **or** a project-local `.env`.
3. Report a per-server status table. Stdio servers can use shell env or
   `.env`; HTTP servers (currently `github`, `huggingface`) can only use
   shell env, because Claude Code expands `${VAR}` in `headers` before any
   subprocess starts.
4. Offer remediation for missing tokens: copy `.env.example` → `.env`, open
   `.env` for editing, and point the user at the canonical "where do I get a
   key" URLs. Never write a key into a file the user hasn't dictated.
5. Tell the user how to actually pick up the new state (reload the plugin or
   restart `claude`).

## How to run it

Work top-down. Stop and ask before doing anything destructive.

### Step 1 — Discover what's declared

Read `${CLAUDE_PLUGIN_ROOT}/.mcp.json`. Build a list of `{name, transport,
env_vars}` for each entry under `mcpServers`. Transport is `http` when the
entry has a `type: "http"` field, otherwise `stdio`. Env vars are inferred:

- Stdio entries that route through `bin/load-env-and-exec.sh`: read the
  README "Bundled MCPs" table for the expected env var name. Don't hard-code
  it in this skill; the README is the source of truth.
- HTTP entries: parse the `Authorization` header for `${VAR_NAME}`.

If `.mcp.json` is missing, stop and tell the user the plugin install looks
broken — recommend reinstalling rather than trying to patch around it.

### Step 2 — Resolve each env var

For each token name, check in this order and remember which layer it came
from (used to drive accurate advice later):

1. **Shell env** — `printenv VAR_NAME` (or test `-n "${VAR_NAME:-}"` via a
   short bash one-liner). Never echo the value; only check presence/length.
2. **Project-local `.env`** — read `./.env` if present, parse `KEY=VALUE`
   pairs, check whether the key is non-empty. Again: never surface the value.

Treat any non-empty match as "set". An empty `KEY=` line counts as unset.

### Step 3 — Report

Print one table like this (filling in real values), nothing more:

```
Server         Transport  Token                              Source     Status
exa            stdio      EXA_API_KEY                        shell      ✓ set
tavily         stdio      TAVILY_API_KEY                     .env       ✓ set
brave-search   stdio      BRAVE_API_KEY                      —          ✗ missing
github         http       GITHUB_PERSONAL_ACCESS_TOKEN       shell      ✓ set
huggingface    http       HF_TOKEN                           —          ✗ missing  (HTTP — .env won't help)
```

For each `✗ missing` HTTP server, append the parenthetical reminder that
`.env` is not consulted. Don't repeat this for stdio rows.

### Step 4 — Remediate (only with explicit user consent)

If there are missing stdio tokens and no `.env` exists, ask:

> No `.env` in the current project. Want me to copy `.env.example` to `.env`
> so you can fill in the missing keys?

If they say yes: `cp .env.example .env` (do **not** `chmod`, do **not** seed
values). Tell them which keys to fill, and where to get each one (link to
the README "Bundled MCPs" table for the canonical URLs).

If there are missing HTTP tokens, do NOT touch `.env` for them. Tell the
user the exact `export` lines to add to their shell profile, e.g.:

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN=...
export HF_TOKEN=...
```

…and mention `direnv` as an alternative for project-scoped exports.

Never run commands that print the token. Never `cat .env`. Never echo
`$GITHUB_PERSONAL_ACCESS_TOKEN`. If the user pastes a key into chat, redact
it from any followup recap.

### Step 5 — Reload guidance

Tell the user how to pick up new env values:

- If keys were added to `.env` and the stdio shim will pick them up: just
  reload the plugin (`/mcp` in Claude Code, then reconnect each affected
  server) or restart `claude`.
- If keys were added to the shell profile: source the profile in any new
  shell where they launch `claude` (or open a new terminal). HTTP MCPs read
  from the launching process env, so a full `claude` restart is the safest
  path.

### Step 6 — Verify (optional, only on request)

If the user asks "is it actually working?", suggest running `/mcp` and
checking that each server shows as connected with its tools listed. Do not
attempt to send a real request through the MCP server from this skill —
that's outside scope and burns the user's quota for no diagnostic value.

## Out of scope

- Installing the plugin itself (the user is already inside it if this skill
  runs).
- Writing tokens to disk on behalf of the user.
- Verifying that a token has the right scopes — that's a vendor-side
  problem.
- Adding new MCP servers — separate workflow.

## Naming convention reminder

This plugin uses `omr` as its slash-command namespace (short for
Oh-My-Research). Every skill folder under `skills/` is invoked as
`/omr:<skill-name>`. Keyword triggers in skill descriptions should also use
the `omr-` prefix (e.g. `omr-setup`, `omr-survey`) so users can type the
hyphenated form in plain chat.
