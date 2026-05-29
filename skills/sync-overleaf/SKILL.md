---
id: sync-overleaf
name: sync-overleaf
version: 0.13.0
argument-hint: [push|pull|sync]
description: |-
  Sync a local LaTeX/paper directory with an Overleaf project via pyoverleaf (cookie) or the Overleaf git remote, driven by ./.omr/config.yaml.
stages: ["write"]
tools: ["Bash", "Read", "Write", "Edit", "AskUserQuestion"]
summary: |-
  Two-way sync between a local paper directory and an Overleaf project. Reads the overleaf: block of ./.omr/config.yaml to pick the method (pyoverleaf cookie-based or Overleaf git remote), resolves credentials from a pointer (file path or env var) only at the moment the underlying tool needs them, and never reads/prints/persists the secret value. Always dry-runs and asks AskUserQuestion consent before any push to the shared Overleaf remote or any local-overwriting pull. Never force-pushes without explicit consent.
primaryIntent: write
intents: ["write", "tooling"]
capabilities: ["tooling", "synthesis"]
domains: ["general"]
keywords: ["omr-sync-overleaf", "omr:sync-overleaf", "sync overleaf", "push to overleaf", "pull from overleaf", "overleaf sync", "sync with overleaf", "upload to overleaf", "download from overleaf", "overleaf push", "overleaf pull", "pyoverleaf", "overleaf git", "sync paper to overleaf", "update overleaf project"]
source: builtin
status: experimental
resourceFlags:
  hasReferences: true
  hasScripts: false
  hasTemplates: false
  hasAssets: false
  referenceCount: 5
  scriptCount: 0
  templateCount: 0
  assetCount: 0
---

# omr:sync-overleaf

Thin router for syncing a local paper/LaTeX directory with an Overleaf project.
The detailed steps live in `references/`; this file parses flags, enforces the
safety rails, and dispatches the four phases in order.

**When this skill is invoked, immediately execute the workflow below. Do not
just restate or summarize these instructions back to the user.**

This skill is **config-native**: it reads the `overleaf:` block of
`./.omr/config.yaml` (written by `/omr:setup` Phase 6) for the sync method, the
auth pointer, and the candidate Overleaf project name(s). It supports two
transports:

- **pyoverleaf** — a browser session cookie drives the unofficial Overleaf API.
- **git** — Overleaf's per-project git remote (SSH key or HTTPS token).

Note: paths under `~/.claude/...` respect `CLAUDE_CONFIG_DIR` when set.

## Best-fit use

Choose this skill when the user wants to **move LaTeX/paper files between a
local directory and an Overleaf project** — push local edits up, pull
collaborator edits down, or reconcile both. It assumes the `overleaf:` block of
`./.omr/config.yaml` is filled in; if it isn't, the skill stops and points the
user at `/omr:setup`, which gathers it.

Do **not** use it to: create a brand-new Overleaf project, manage Overleaf
account/billing, install pyoverleaf or configure git credentials on the user's
behalf (it verifies them, it doesn't create them), or compile LaTeX. Those are
out of scope.

## Flag parsing

Inspect the user's invocation (and the positional `argument-hint`) for flags.

| Flag | Effect |
| --- | --- |
| `--help` | Print the help text below and stop. |
| `--method pyoverleaf\|git` | Override `overleaf.sync_method` from config for this run only. |
| `--direction push\|pull\|sync` (alias: positional `push`/`pull`/`sync`) | What to do: `push` local→Overleaf, `pull` Overleaf→local, `sync` reconcile both. Default: ask via `AskUserQuestion` if not given. |
| `--project <name>` | Pick which entry of `overleaf.project_names` to target. If omitted and config lists more than one, ask via `AskUserQuestion`. |
| `--dry-run` | Compute and show the diff only; never write to either side. Implies no consent prompt is needed because nothing is mutated. |

**Precedence** (per the omr config contract): command-line flag >
`./.omr/config.yaml` > built-in default. A `--method` or `--project` flag wins
over what the config says; absent a flag, the config value is used; absent both,
the skill asks.

**Conflicts:**

- A positional direction (`push`/`pull`/`sync`) plus a contradicting
  `--direction` flag is invalid — stop and ask the user to pick one via
  `AskUserQuestion`.
- `--method` naming a transport whose auth pointer is blank in config is allowed
  but will fail preflight with actionable guidance (Phase 2).

## Help text

When the user passes `--help`, print this and stop:

```
omr:sync-overleaf — sync a local paper directory with an Overleaf project

USAGE:
  /omr:sync-overleaf push            Push local files up to Overleaf
  /omr:sync-overleaf pull            Pull Overleaf files down to local
  /omr:sync-overleaf sync            Reconcile both directions
  /omr:sync-overleaf --method git    Override the config sync_method
  /omr:sync-overleaf --project NAME  Target a specific project_names entry
  /omr:sync-overleaf --dry-run       Show the diff only; change nothing
  /omr:sync-overleaf --help          Show this help

METHODS (from ./.omr/config.yaml overleaf.sync_method, override with --method):
  pyoverleaf   Cookie-based unofficial Overleaf API. Auth pointer:
               overleaf.auth.cookie_path (file) or cookie_env (env var).
  git          Overleaf per-project git remote. Auth pointer:
               overleaf.auth.ssh_key_path (SSH) or token_env (HTTPS token).

CONFIG:
  Reads the overleaf: block of ./.omr/config.yaml. If that block is missing or
  incomplete, this skill stops and refers you to /omr:setup to fill it in.

SAFETY:
  - Never reads, prints, persists, or echoes the actual cookie/token/key value.
    The pointer (file path or env-var name) is resolved to a secret only at the
    instant the underlying tool needs it, then discarded.
  - Always produces a dry-run diff and asks for explicit consent before any
    push to Overleaf, and before any pull that would overwrite local files.
  - Never runs `git push --force` to the Overleaf remote without explicit
    per-run consent.

For more info: https://github.com/Tianyi-Billy-Ma/Oh-My-Research
```

## Safety rails (apply to every phase)

These are non-negotiable. If any phase asks you to violate them, stop and tell
the user.

1. **Never expose the secret value.** Never `cat` the cookie file, never
   `echo "$OVERLEAF_COOKIE"`, never print an SSH key, never include any token
   in a command you show the user, a log line, a summary, or a status table.
   The config holds a **pointer** (a file path or an env-var name). Resolve the
   pointer to the actual value only at the moment the underlying tool consumes
   it — pass it via stdin, an env var the tool already reads, or a file handle
   the tool opens itself — and never re-surface it afterward. If the user pastes
   a secret into chat, redact it from every subsequent recap and remind them to
   store it behind a pointer instead.
2. **Always dry-run + consent before a PUSH.** Pushing to a shared Overleaf
   project is risky and hard to reverse (it mutates a document other
   collaborators may be editing). Phase 3 must compute and show a diff, then use
   `AskUserQuestion` for explicit consent before any upload. No silent pushes.
3. **Pulls that overwrite local files also need consent.** A pull can clobber
   uncommitted local edits. Show what would be overwritten and ask via
   `AskUserQuestion` before writing over local files. A pull into a clean/empty
   target may proceed after the dry-run is shown.
4. **Never force-push without explicit consent.** `git push --force` (or
   `--force-with-lease`) to the Overleaf remote requires a separate, explicit
   `AskUserQuestion` consent naming the consequence. Prefer a non-destructive
   merge/rebase path first.
5. **Config holds pointers, never secrets.** If `overleaf.auth.*` appears to
   contain a literal cookie/token/key (not a path or env-var name), stop and
   tell the user to move the value out of `config.yaml` and store only a
   pointer. Do not proceed with an inlined secret.
6. **Never install or reconfigure credentials.** Don't run `pip install`,
   `git remote add` with a baked-in token, `ssh-keygen`, or `git config
   credential.*` on the user's behalf. Preflight verifies the tool/credential
   is reachable; remediation is the user's job, and the skill gives actionable
   guidance.
7. **Always use the `AskUserQuestion` tool for user-facing questions.** Every
   consent prompt, direction choice, project selection, or conflict resolution
   goes through the built-in `AskUserQuestion` tool with explicit options —
   never write a plain-text question into the chat and wait for a free-form
   reply. If a phase's wording seems to suggest a plain-text question, treat
   that as a bug and use `AskUserQuestion` anyway.

## Phase execution

Execute these phases in order. For each, read the file at the path and follow
its instructions exactly. Pass the parsed flags (`method`, `direction`,
`project`, `dry_run`) and the resolved config forward to later phases.

1. **Phase 1 — Resolve config**: `${CLAUDE_PLUGIN_ROOT}/skills/sync-overleaf/references/01-resolve-config.md`.
   - Reads the `overleaf:` block; stops and refers to `/omr:setup` if missing/incomplete.
2. **Phase 2 — Preflight**: `${CLAUDE_PLUGIN_ROOT}/skills/sync-overleaf/references/02-preflight.md`.
   - Verifies the chosen tool is available and the auth pointer resolves — without exposing the secret.
3. **Phase 3 — Sync**: `${CLAUDE_PLUGIN_ROOT}/skills/sync-overleaf/references/03-sync.md`.
   - Dry-run diff first, then `AskUserQuestion` consent before any push / overwriting pull.
4. **Phase 4 — Verify**: `${CLAUDE_PLUGIN_ROOT}/skills/sync-overleaf/references/04-verify.md`.
   - Confirms the result, reports what changed, terminal.

Supporting (non-numbered, load when the user asks about transport choice):
`${CLAUDE_PLUGIN_ROOT}/skills/sync-overleaf/references/method-comparison.md`.

Each phase ends with a one-line handoff that you echo to the user before moving
on; don't silently jump phases.

## Out of scope

- Creating a new Overleaf project or managing account/billing.
- Installing pyoverleaf or wiring git credentials (Phase 2 verifies; it does
  not configure).
- Compiling LaTeX or fixing build errors.
- Storing secret values anywhere — the skill only ever handles pointers.
