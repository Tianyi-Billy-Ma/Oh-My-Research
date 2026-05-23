---
name: setup
description: |
  Configure Oh-My-Research (omr) MCP servers: audit tokens for the five
  bundled servers (Exa, Tavily, Brave Search, GitHub, Hugging Face),
  scaffold a project-local `.env` from `.env.example` when missing, and
  point the user at the right remediation steps without ever printing
  secrets. Use when the user says "omr-setup", "omr:setup", "setup omr",
  "set up Oh-My-Research", "configure omr keys", "check omr status", or
  otherwise asks to install / configure / health-check this plugin.
level: 2
---

# omr:setup

Thin router for the omr install/health-check flow. The detailed steps live in
`phases/`; this file decides which phases to run and enforces the safety rails
that apply to every phase.

**When this skill is invoked, immediately execute the workflow below. Do not
just restate or summarize these instructions back to the user.**

## Best-fit use

Choose this skill when the user wants to **install, configure, or health-check
omr's MCP wiring**.

- After enabling the omr plugin for the first time → run it to confirm tokens
  are reachable.
- After adding a new API key → run it to confirm the right MCP server picks it
  up.
- When `/mcp` shows a server disconnected → run it to triage shell-env vs
  `.env` vs missing-token.

Do **not** use it to install the plugin itself (the user is already inside
it), to add new MCP servers, or to validate that an API key has the right
scopes — those are separate workflows.

## Flag parsing

Inspect the user's invocation for flags:

- `--help` → print the help text below and stop.
- `--audit` (alias `--check`) → run Phase 1 + Phase 2 only; skip remediation.
- `--fix` → run all four phases (default).
- No flags → same as `--fix`.

## Help text

When the user passes `--help`, print this and stop:

```
omr:setup — configure Oh-My-Research MCP servers

USAGE:
  /omr:setup           Full flow: discover → audit → remediate → verify
  /omr:setup --audit   Read-only: discover + audit, no file changes
  /omr:setup --fix     Same as default (full flow)
  /omr:setup --help    Show this help

WHAT IT DOES:
  1. Reads .mcp.json to enumerate which servers are declared and which
     env vars they need.
  2. Checks each token against shell env first, then a project-local
     .env (.env is only consulted for stdio servers).
  3. If tokens are missing: offers to copy .env.example → .env for
     stdio servers, and prints the exact `export` lines you need for
     HTTP servers.
  4. Tells you how to reload so the new state takes effect.

SAFETY:
  - Never prints token values.
  - Never writes a token on your behalf.
  - Asks for explicit consent before any file write.

For more info: https://github.com/Tianyi-Billy-Ma/Oh-My-Research
```

## Safety rails (apply to every phase)

These are non-negotiable. If any phase asks you to violate them, stop and tell
the user.

1. **Never echo a token value.** Probes must check presence/length only — e.g.
   `[ -n "${VAR:-}" ]`, never `echo "$VAR"`, never `cat .env`, never include a
   token in a status table or summary message. If the user pastes a key into
   chat, redact it from any subsequent recap.
2. **Never write a token to disk.** Scaffolding `.env` from `.env.example` is
   fine; writing values is the user's job. If they ask you to fill in a key,
   tell them to edit `.env` themselves and reload.
3. **Always ask before mutating the filesystem.** Use AskUserQuestion before
   `cp .env.example .env` or any other write. Read-only probes don't need
   consent.
4. **HTTP MCPs ignore `.env`.** Don't suggest a `.env` fix for `github` or
   `huggingface` (or any future HTTP-transport server) — Claude Code expands
   `${VAR}` against its own process env at startup. Only shell exports (or
   `direnv` etc.) work for them.

## Phase execution

Execute these phases in order. For each phase, read the file at the path and
follow its instructions exactly.

1. **Phase 1 — Discover**: read `${CLAUDE_PLUGIN_ROOT}/skills/setup/phases/01-discover.md`.
2. **Phase 2 — Audit**: read `${CLAUDE_PLUGIN_ROOT}/skills/setup/phases/02-audit.md`.
   - If the user passed `--audit` / `--check`, stop after this phase.
3. **Phase 3 — Remediate**: read `${CLAUDE_PLUGIN_ROOT}/skills/setup/phases/03-remediate.md`.
4. **Phase 4 — Verify**: read `${CLAUDE_PLUGIN_ROOT}/skills/setup/phases/04-verify.md`.

Each phase ends with a one-line handoff that you echo to the user before
moving on; don't silently jump phases.

## Out of scope

- Installing the omr plugin itself (you're already inside it if this runs).
- Adding new MCP servers — that's a separate skill.
- Verifying a token has the right scopes — vendor-side concern.
- Live-testing each server with a real query — burns quota; `/mcp` connection
  status is enough.
