# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`Oh-My-Research` is a **Claude Code plugin** (not an application). It packages research-oriented skills, agents, and hooks that get loaded into Claude Code via the plugin system. The goal is an "autoresearch / viberesearch" suite — automating literature survey, idea generation, experiment loops, paper writing, and review — similar in spirit to:

- `wanshuiyin/Auto-claude-code-research-in-sleep`
- `LigphiDonk/Oh-my--paper`
- `uditgoenka/autoresearch`

Current surface area is small: a plugin manifest, an `.mcp.json` declaring three search-MCP servers (Exa, Tavily, Brave), and a `bin/load-env-and-exec.sh` shim that resolves API keys from shell env first and a project-local `.env` second. No skills/agents/hooks/commands yet, and there is **no build, test, or lint pipeline** because there is no application code — do not invent one. New work means authoring plugin components and bumping `plugin.json` version, not editing source.

## Plugin layout contract

Follow the official Claude Code plugin template exactly — the README pins this and the loader depends on it:

```
Oh-My-Research/
├── .claude-plugin/
│   └── plugin.json          # ONLY file under .claude-plugin/
├── .mcp.json                # MCP server declarations loaded by the plugin
├── bin/                     # plugin-internal scripts (e.g. env loader shim)
├── skills/                  # one folder per skill, each containing SKILL.md
│   └── <skill-name>/SKILL.md
├── agents/                  # optional: <name>.md agent definitions
├── hooks/                   # optional: hooks.json
└── commands/                # optional: slash-command markdown files
```

Hard rules:
- Only `plugin.json` belongs inside `.claude-plugin/`. Everything else (skills, agents, hooks, commands) lives at the **plugin root**, not nested under `.claude-plugin/`.
- Each skill is a directory under `skills/` with a `SKILL.md` entry point; supporting scripts/templates go alongside it in the same directory.
- When adding a skill or agent, also bump `version` in `.claude-plugin/plugin.json` so installations refresh.

## Installing locally for testing

```bash
claude --plugin-dir /Users/billyma/Workspace/Oh-My-Research
```

This loads the plugin into a Claude Code session without publishing to a marketplace. Use it to verify skills surface under `/<plugin>:<skill>` before committing.

## Authoring notes

- This plugin is intended to compose with the user's existing `oh-my-claudecode` and `claude-mem` plugins (already installed globally). Don't duplicate skills that those provide (e.g., `autopilot`, `ralph`, `ultrawork`, `make-plan`); instead, add research-domain capabilities that *call* them when appropriate.
- The workspace also hosts `omp:*` and `billyverse:*` skills geared at academic research (literature search, paper writing, experiment dispatch). Before adding a skill here, check whether one of those already covers the workflow — this plugin should add what's missing, not re-implement.
- Inspiration repos above are good references for shape (skill names, prompt structure, loop semantics) but their code is not vendored here; consult them externally when designing a new workflow.

## MCP servers (`.mcp.json`)

The plugin ships three search MCPs at the root:

- `exa` → `npx -y exa-mcp-server` (env: `EXA_API_KEY`)
- `tavily` → `npx -y tavily-mcp` (env: `TAVILY_API_KEY`)
- `brave-search` → `npx -y @brave/brave-search-mcp-server` (env: `BRAVE_API_KEY`, stdio is default in 2.x)

All three are launched through `${CLAUDE_PLUGIN_ROOT}/bin/load-env-and-exec.sh`, which:

1. Reads `$PWD/.env` if it exists.
2. Exports any `KEY=VALUE` pairs that are **not already set** in the inherited environment (so shell exports win over `.env`).
3. `exec`s the actual MCP server command.

When adding a new MCP that needs API keys, reuse this shim — don't bypass it. Just append another entry to `.mcp.json` with the same `command` and the new server's `npx` invocation in `args`. The shim is intentionally provider-agnostic and handles quoted values, `export`-prefixed lines, comments, and malformed lines.

Anything that touches MCP wiring (new server, env var rename, shim change) is user-visible and should bump the `version` in `.claude-plugin/plugin.json`.

## Repository-specific conventions

- `.omc/` is git-ignored and holds local OMC runtime state (sessions, project memory, HUD cache) — never commit it.
- `.env` is git-ignored; only `.env.example` is checked in. Never put real keys in the example.
- The repo lives at `github.com/Tianyi-Billy-Ma/Oh-My-Research` per `plugin.json`; the `name` field there (`oh-my-research`) is what shows up as the plugin namespace inside Claude Code.
