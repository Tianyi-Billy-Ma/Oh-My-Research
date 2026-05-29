---
id: sync-overleaf
name: sync-overleaf
version: 0.14.0
argument-hint: [push|pull|sync]
description: |-
  Sync a local LaTeX/paper directory with an Overleaf project via pyoverleaf (cookie or browser-keychain auth), driven by ./.omr/config.yaml.
stages: ["write"]
tools: ["Bash", "Read", "Write", "Edit", "AskUserQuestion"]
summary: |-
  Two-way sync between a local paper directory and an Overleaf project using pyoverleaf. Reads the overleaf: block of ./.omr/config.yaml for the target project and the cookie pointer, resolves the cookie from a file path only at the moment pyoverleaf needs it (or falls back to native browser/keychain login), and never reads/prints/persists the secret value. Installs pyoverleaf into a shared, isolated tool env (uv tool / pipx) if missing — never into the project venv. Always dry-runs and asks AskUserQuestion consent before any push to the shared Overleaf project or any local-overwriting pull.
primaryIntent: write
intents: ["write", "tooling"]
capabilities: ["tooling", "synthesis"]
domains: ["general"]
keywords: ["omr-sync-overleaf", "omr:sync-overleaf", "sync overleaf", "push to overleaf", "pull from overleaf", "overleaf sync", "sync with overleaf", "upload to overleaf", "download from overleaf", "overleaf push", "overleaf pull", "pyoverleaf", "sync paper to overleaf", "update overleaf project"]
source: builtin
status: experimental
resourceFlags:
  hasReferences: true
  hasScripts: true
  hasTemplates: false
  hasAssets: false
  referenceCount: 5
  scriptCount: 1
  templateCount: 0
  assetCount: 0
---

# omr:sync-overleaf

Thin router for syncing a local paper/LaTeX directory with an Overleaf project
via **pyoverleaf**. The detailed steps live in `references/`; this file parses
flags, enforces the safety rails, and dispatches the four phases in order.

**When this skill is invoked, immediately execute the workflow below. Do not
just restate or summarize these instructions back to the user.**

This skill is **config-native**: it reads the `overleaf:` block of
`./.omr/config.yaml` (written by `/omr:setup` Phase 6) for the target Overleaf
project name(s) and the cookie auth pointer. It uses a single transport:

- **pyoverleaf** — the unofficial Overleaf API, authenticated either by a
  browser session cookie dumped to a file (`cookie_path`) or, when no file is
  set, by pyoverleaf's native browser/keychain login. The actual sync runs
  through `scripts/sync_overleaf.py`.

The git transport is **not supported yet** — if `overleaf.sync_method` is
`git`, the skill stops and tells the user (Phase 1).

Note: paths under `~/.claude/...` respect `CLAUDE_CONFIG_DIR` when set.

## Best-fit use

Choose this skill when the user wants to **move LaTeX/paper files between a
local directory and an Overleaf project** — push local edits up, pull
collaborator edits down, or reconcile both. It assumes the `overleaf:` block of
`./.omr/config.yaml` is filled in; if it isn't, the skill stops and points the
user at `/omr:setup`, which gathers it.

Do **not** use it to: create a brand-new Overleaf project, manage Overleaf
account/billing, or compile LaTeX. Those are out of scope. (It *will* install
pyoverleaf into an isolated tool env on consent — see Phase 2 — but it never
touches the project venv and never logs in for you.)

## Flag parsing

Inspect the user's invocation (and the positional `argument-hint`) for flags.

| Flag | Effect |
| --- | --- |
| `--help` | Print the help text below and stop. |
| `--direction push\|pull\|sync` (alias: positional `push`/`pull`/`sync`) | What to do: `push` local→Overleaf, `pull` Overleaf→local, `sync` reconcile both. Default: ask via `AskUserQuestion` if not given. |
| `--project <name-or-id>` | Pick which entry of `overleaf.project_names` to target (an exact name), or pass a 24-hex Overleaf project id directly. If omitted and config lists more than one, ask via `AskUserQuestion`. |
| `--dry-run` | Compute and show the diff only; never write to either side. Implies no consent prompt is needed because nothing is mutated. |

**Precedence** (per the omr config contract): command-line flag >
`./.omr/config.yaml` > built-in default. A `--project` flag wins over what the
config says; absent a flag, the config value is used; absent both, the skill
asks.

**Conflicts:**

- A positional direction (`push`/`pull`/`sync`) plus a contradicting
  `--direction` flag is invalid — stop and ask the user to pick one via
  `AskUserQuestion`.

## Help text

When the user passes `--help`, print this and stop:

```
omr:sync-overleaf — sync a local paper directory with an Overleaf project (pyoverleaf)

USAGE:
  /omr:sync-overleaf push              Push local files up to Overleaf
  /omr:sync-overleaf pull              Pull Overleaf files down to local
  /omr:sync-overleaf sync              Reconcile both directions
  /omr:sync-overleaf --project NAME    Target a specific project_names entry (or a 24-hex id)
  /omr:sync-overleaf --dry-run         Show the diff only; change nothing
  /omr:sync-overleaf --help            Show this help

METHOD:
  pyoverleaf   Unofficial Overleaf API (https://github.com/jkulhanek/pyoverleaf).
               Auth pointer: overleaf.auth.cookie_path (a JSON cookie file), or
               no pointer to use native browser/keychain login. Installed into a
               shared tool env (uv tool / pipx) if missing — never the project venv.
               The git transport is not supported yet.

CONFIG:
  Reads the overleaf: block of ./.omr/config.yaml. If that block is missing or
  incomplete, this skill stops and refers you to /omr:setup to fill it in.

SAFETY:
  - Never reads, prints, persists, or echoes the actual cookie value. The pointer
    (a file path) is resolved by pyoverleaf only at the instant it needs it.
  - Always produces a dry-run diff and asks for explicit consent before any push
    to Overleaf, and before any pull that would overwrite local files.
  - push targets explicit files only — never a recursive "push everything".

For more info: https://github.com/Tianyi-Billy-Ma/Oh-My-Research
```

## Safety rails (apply to every phase)

These are non-negotiable. If any phase asks you to violate them, stop and tell
the user.

1. **Never expose the secret value.** Never `cat` the cookie file, never `echo`
   a cookie, never include any cookie value in a command you show the user, a
   log line, a summary, or a status table. The config holds a **pointer** (a
   file path). pyoverleaf reads the file itself (via `--cookies <path>` passed
   to `scripts/sync_overleaf.py`); you never read its contents. If the user
   pastes a secret into chat, redact it from every subsequent recap and remind
   them to store it behind a file pointer instead.
2. **Always dry-run + consent before a PUSH.** Pushing to a shared Overleaf
   project is risky (it mutates a document other collaborators may be editing).
   Phase 3 must compute and show a diff, then use `AskUserQuestion` for explicit
   consent before any upload. No silent pushes. `push` targets explicitly named
   files only — there is no recursive default.
3. **Pulls that overwrite local files also need consent.** A pull can clobber
   uncommitted local edits. Show what would be overwritten and ask via
   `AskUserQuestion` before writing over local files. A pull into a clean/empty
   target may proceed after the dry-run is shown.
4. **Config holds pointers, never secrets.** If `overleaf.auth.cookie_path`
   appears to contain a literal cookie (not a path), stop and tell the user to
   move the value out of `config.yaml` and store only a path. Do not proceed
   with an inlined secret.
5. **Shared tool env only — never the project venv.** If pyoverleaf is missing,
   install it with `uv tool install pyoverleaf` (preferred) or `pipx install
   pyoverleaf` (fallback) after `AskUserQuestion` consent. **Never** run
   `uv add pyoverleaf` or `pip install pyoverleaf` inside the research project's
   virtualenv. Do not log in on the user's behalf (browser/keychain auth is
   theirs to grant).
6. **Always use the `AskUserQuestion` tool for user-facing questions.** Every
   consent prompt, direction choice, project selection, install confirmation, or
   conflict resolution goes through the built-in `AskUserQuestion` tool with
   explicit options — never write a plain-text question into the chat and wait
   for a free-form reply. If a phase's wording seems to suggest a plain-text
   question, treat that as a bug and use `AskUserQuestion` anyway.

## Phase execution

Execute these phases in order. For each, read the file at the path and follow
its instructions exactly. Pass the parsed flags (`direction`, `project`,
`dry_run`) and the resolved config forward to later phases.

1. **Phase 1 — Resolve config**: `${CLAUDE_PLUGIN_ROOT}/skills/sync-overleaf/references/01-resolve-config.md`.
   - Reads the `overleaf:` block (pyoverleaf only; stops if config says `git`); stops and refers to `/omr:setup` if missing/incomplete.
2. **Phase 2 — Preflight**: `${CLAUDE_PLUGIN_ROOT}/skills/sync-overleaf/references/02-preflight.md`.
   - Detects pyoverleaf (installs into the shared tool env on consent if missing); verifies the cookie pointer / browser-login plan and the project — without exposing the secret.
3. **Phase 3 — Sync**: `${CLAUDE_PLUGIN_ROOT}/skills/sync-overleaf/references/03-sync.md`.
   - Runs `scripts/sync_overleaf.py`: dry-run diff first, then `AskUserQuestion` consent before any push / overwriting pull.
4. **Phase 4 — Verify**: `${CLAUDE_PLUGIN_ROOT}/skills/sync-overleaf/references/04-verify.md`.
   - Confirms the result, reports what changed, terminal.

Supporting (non-numbered, load when the user asks about pyoverleaf, install, or
auth): `${CLAUDE_PLUGIN_ROOT}/skills/sync-overleaf/references/pyoverleaf-usage.md`.

Bundled script:
`${CLAUDE_PLUGIN_ROOT}/skills/sync-overleaf/scripts/sync_overleaf.py` — the
pyoverleaf sync worker (`status` / `pull` / `push` / `rm`), run under the shared
tool env's interpreter and invoked by Phase 3.

Each phase ends with a one-line handoff that you echo to the user before moving
on; don't silently jump phases.

## Out of scope

- Creating a new Overleaf project or managing account/billing.
- The git transport (not implemented yet).
- Logging into Overleaf for the user (browser/keychain auth is theirs).
- Compiling LaTeX or fixing build errors.
- Storing secret values anywhere — the skill only ever handles a cookie-file
  pointer.
