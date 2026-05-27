---
id: setup
name: setup
version: 0.8.2
description: |-
  Install, configure, and health-check Oh-My-Research (omr).
stages: ["setup"]
tools: ["Bash", "Read", "Write", "Edit", "AskUserQuestion"]
summary: |-
  Umbrella entry point for omr install / config / health-check. Covers MCP token audit, CLAUDE.md install via versioned marker block, .env scaffolding, optional HPC YAML config, and a configured-state marker so repeat runs short-circuit to a quick re-audit.
primaryIntent: setup
intents: ["setup", "configuration"]
capabilities: ["tooling"]
domains: ["general"]
keywords: ["omr-setup", "omr:setup", "setup omr", "set up oh-my-research", "configure omr", "check omr status", "omr health check", "refresh omr claude.md", "configure omr hpc", "add omr cluster", "install omr"]
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

# omr:setup

Thin router for the omr install/health-check flow. The detailed steps live in
`phases/`; this file decides which phases to run, parses flags, handles the
"already configured" short-circuit, and enforces cross-phase safety rails.

**When this skill is invoked, immediately execute the workflow below. Do not
just restate or summarize these instructions back to the user.**

Note: paths under `~/.claude/...` respect `CLAUDE_CONFIG_DIR` when that
environment variable is set.

## Best-fit use

Choose this skill when the user wants to **install, configure, or health-check
Oh-My-Research itself**. Setup is the umbrella entry point for everything that
lives "around" the plugin — CLAUDE.md installation and MCP wiring today,
additional sub-systems (model defaults, agent installs, project-local config,
hooks) as they get added.

When new setup concerns land, they're added as new phases under this skill —
not as separate skills — so users have one consistent place to fix any "I
just installed omr, now what?" issue.

Today's coverage:

- Install (or refresh) omr's instructions block into the user's CLAUDE.md
  via a versioned marker (`<!-- BEGIN omr version="X.Y.Z" -->`) so future
  Claude Code sessions know about the plugin without re-discovery.
- Audit tokens for the five bundled MCP servers (Exa, Tavily, Brave Search,
  GitHub, Hugging Face) and surface which ones are missing.
- Scaffold a project-local `.env` from `.env.example` on consent.
- Optionally drop a per-cluster HPC / remote-server YAML config file (from
  `templates/hpc.yaml`) into `~/.claude/hpc/<id>.yaml` or
  `./.omr/hpc/<id>.yaml` so future compute-routing skills know where to
  send jobs. The phase never modifies `~/.ssh/config` and never runs SSH
  commands — it's pure config installation.
- Persist a configured-state marker so repeat runs short-circuit to a quick
  re-audit instead of replaying the full wizard.

Do **not** use it to install the plugin itself (you're already inside it), to
add new MCP servers, or to validate that an API key has the right scopes —
those are separate workflows.

## Flag parsing

Inspect the user's invocation for flags. Accept any combination unless noted.

| Flag | Effect |
| --- | --- |
| `--help` | Print the help text below and stop. |
| `--audit` (alias `--check`) | Read-only: run Phase 1 + Phase 2 only. No file writes. Does not update the config marker. |
| `--local` | Scope to project-local files: CLAUDE.md install targets `./.claude/CLAUDE.md`; remediation only acts on `.env`; HPC configs land in `./.omr/hpc/`. HTTP gaps and global files are listed but not touched. |
| `--global` | Scope to user-level files: CLAUDE.md install targets `~/.claude/CLAUDE.md`; remediation only emits shell-export advice; HPC configs land in `~/.claude/hpc/`. The project `.env` is left alone. |
| `--force` | Skip the "already configured" pre-check; rerun the full flow regardless. |
| (no flags) | Pre-check first; if already configured, offer a quick re-audit; otherwise run the full flow, asking interactively where to install CLAUDE.md. |

**Conflicts:**

- `--local` + `--global` is invalid — stop and ask the user to pick one.
- `--audit` + `--local`/`--global` is allowed but has no effect on Phase 2's
  table (audit always shows all rows); the scope is recorded as informational
  metadata for the audit summary.

## Help text

When the user passes `--help`, print this and stop:

```
omr:setup — install, configure, and health-check Oh-My-Research

USAGE:
  /omr:setup            Pre-check, then full flow if not already configured
  /omr:setup --audit    Read-only: discover + audit, no file changes
  /omr:setup --local    Full flow scoped to project-local files
  /omr:setup --global   Full flow scoped to user-level files
  /omr:setup --force    Skip pre-check, rerun full flow from scratch
  /omr:setup --help     Show this help

MODES:
  Default (no flags)
    Reads ~/.claude/.omr-config.json. If you've completed setup before,
    offers a quick re-audit short-circuit. Otherwise: discover → audit →
    install CLAUDE.md → remediate → verify, asking interactively for the
    CLAUDE.md install scope.

  Audit (--audit / --check)
    Phase 1 + Phase 2 only. Probes tokens, prints the status table,
    stops. No filesystem writes, no consent prompts.

  Local (--local)
    Discover → audit → install (./.claude/CLAUDE.md) → remediate (.env
    only) → verify. Use when you only want to wire this one project.

  Global (--global)
    Discover → audit → install (~/.claude/CLAUDE.md) → remediate (shell
    exports only) → verify. Use when you want omr to apply to every
    Claude Code session for your user.

  Force (--force)
    Bypass the already-configured pre-check and rerun the full flow
    even if .omr-config.json says you're done.

SAFETY:
  - Never prints token values.
  - Never writes a token on your behalf.
  - Asks for explicit consent before any file write.
  - Backs up existing CLAUDE.md to CLAUDE.md.backup.YYYY-MM-DD before any
    refresh, and never full-overwrites (insert-block only).

For more info: https://github.com/Tianyi-Billy-Ma/Oh-My-Research
```

## Safety rails (apply to every phase)

These are non-negotiable. If any phase asks you to violate them, stop and tell
the user.

1. **Never echo a token value.** Probes check presence/length only —
   `[ -n "${VAR:-}" ]`, never `echo "$VAR"`, never `cat .env`, never include a
   token in a status table or summary. If the user pastes a key into chat,
   redact it from any subsequent recap.
2. **Never write a token to disk.** Scaffolding `.env` from `.env.example` is
   fine; writing values is the user's job.
3. **Always ask before mutating the filesystem.** Use AskUserQuestion before
   `cp .env.example .env`, before any CLAUDE.md write, or any other mutation.
   Read-only probes don't need consent.
4. **HTTP MCPs ignore `.env`.** Don't suggest a `.env` fix for `github` or
   `huggingface` (or any future HTTP-transport server). Only shell exports
   (or `direnv` etc.) work.
5. **Never full-overwrite CLAUDE.md.** Phase 3 uses a marker block; if the
   markers are unbalanced or nested, stop and ask the user to fix manually.
6. **Never touch `~/.ssh/config` or run SSH commands on the user's behalf.**
   Phase 5 only installs YAML config files; the user wires up authentication
   themselves. No `ssh-keygen`, no `ssh-copy-id`, no `ssh` smoke tests.
7. **Always use the `AskUserQuestion` tool for user-facing questions.** Every
   consent prompt, scope choice, conflict resolution, or branch decision goes
   through the built-in `AskUserQuestion` tool with explicit options — never
   write a plain-text question into the chat and wait for a free-form reply.
   This applies in SKILL.md (the already-configured prompt) and in every
   phase. If a phase's instructions seem to suggest a plain-text question,
   treat that as a bug and use `AskUserQuestion` anyway.

## Pre-setup check: already configured?

Before running any phase, check whether setup has previously completed. This
keeps the skill cheap to rerun after every plugin update.

```bash
CONFIG_FILE="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/.omr-config.json"

if [ -f "$CONFIG_FILE" ]; then
  SETUP_COMPLETED=$(jq -r '.setupCompleted // empty' "$CONFIG_FILE" 2>/dev/null)
  SETUP_VERSION=$(jq -r '.setupVersion // empty' "$CONFIG_FILE" 2>/dev/null)
  if [ -n "$SETUP_COMPLETED" ]; then
    ALREADY_CONFIGURED=true
  fi
fi
```

### Skip the check when:

- The user passed `--force`, `--audit`, `--local`, or `--global` (any explicit
  flag is itself a user signal — proceed without the prompt).
- `jq` is unavailable (degrade gracefully — proceed as if first run, mention
  it in the wrap-up so the user can install `jq` for the cache benefit later).

### When already configured (and no override flag):

Use AskUserQuestion (single-select) with this question and three options:

> omr was already configured on `<SETUP_COMPLETED>` (setup version
> `<SETUP_VERSION>`). What would you like to do?

1. **Re-audit only** — Phase 1 + Phase 2, no changes. (Recommended for routine
   health checks.)
2. **Re-run full setup** — discover → audit → install CLAUDE.md → remediate →
   verify.
3. **Cancel** — exit without changes.

Branch accordingly:

- `Re-audit only` → behave as if `--audit` was passed.
- `Re-run full setup` → proceed to phase execution with no scope filter.
- `Cancel` → echo "omr:setup cancelled." and stop.

## Phase execution

Execute these phases in order. For each, read the file at the path and follow
its instructions exactly. Pass the parsed flags (`scope`, `audit_only`,
`force`) and the per-server records from Phase 1 forward to later phases.

1. **Phase 1 — Discover**: `${CLAUDE_PLUGIN_ROOT}/skills/setup/phases/01-discover.md`.
2. **Phase 2 — Audit**: `${CLAUDE_PLUGIN_ROOT}/skills/setup/phases/02-audit.md`.
   - Stop after this phase if `audit_only` is true.
3. **Phase 3 — Install CLAUDE.md**: `${CLAUDE_PLUGIN_ROOT}/skills/setup/phases/03-install-claude-md.md`.
4. **Phase 4 — Remediate**: `${CLAUDE_PLUGIN_ROOT}/skills/setup/phases/04-remediate.md`.
5. **Phase 5 — HPC config (optional)**: `${CLAUDE_PLUGIN_ROOT}/skills/setup/phases/05-hpc-config.md`.
6. **Phase 6 — Verify**: `${CLAUDE_PLUGIN_ROOT}/skills/setup/phases/06-verify.md`.

Each phase ends with a one-line handoff that you echo to the user before
moving on; don't silently jump phases.

## Out of scope

- Installing the omr plugin itself (you're already inside it if this runs).
- Adding new MCP servers — that's a separate skill.
- Verifying a token has the right scopes — vendor-side concern.
- Live-testing each server with a real query — burns quota; `/mcp` connection
  status is enough.
