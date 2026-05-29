# Phase 6 — Project config (./.omr/config.yaml)

**Goal:** interview the user (via `AskUserQuestion`) and write a project-local
`./.omr/config.yaml` capturing cross-skill defaults — general keys, Overleaf
integration, literature-review defaults, and an HPC pointer. The file is
tool-written from the answers; the user can hand-edit afterward.

## Invariants

- **Project-local.** Always `./.omr/config.yaml`. The `--global` / `--local`
  flags do not change this — config is per-project.
- **Pointers, never secrets.** Overleaf auth fields hold a file path or an
  env-var name, never a cookie/token/key value. If the user pastes a secret,
  store its location and tell them to keep the value out of the file.
- **Every question via `AskUserQuestion`.** No free-text prompts.
- **Idempotent.** If `./.omr/config.yaml` exists, offer to refresh in place
  (preserving values the user already set) rather than clobbering it.
- **`schema_version` tracks the plugin version** via `{{omr_version}}`
  substitution at write time.

## Steps

### 6.1 Render the template and check existing state

Read `${CLAUDE_PLUGIN_ROOT}/skills/setup/templates/config.yaml`. Substitute
`{{omr_version}}` with the current plugin version (from
`${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` `.version`).

If `./.omr/config.yaml` already exists, parse it and pre-fill the interview
with its current values. Ask via `AskUserQuestion`:

> `./.omr/config.yaml` already exists. What now?

1. **Refresh** — re-run the interview, defaulting each answer to the current
   value. Only changed fields are updated.
2. **Leave as-is** — skip this phase entirely.

If `--force` was passed, behave as `Refresh` without asking.

### 6.2 General keys

Ask in one `AskUserQuestion` round (2 questions):

- `author`: "Name to use for citations / paper metadata?" (free-form; blank
  allowed)
- `default_model`: "Preferred model routing hint for omr skills?" Options:
  `opus` / `sonnet` / `haiku` / `leave blank`.

### 6.3 Overleaf integration

This config feeds the `/omr:sync-overleaf` skill. Only the **pyoverleaf**
sync method is supported today (git is not yet wired up), so `sync_method`
stays `pyoverleaf`.

**Round 1 — configure Overleaf now?** `AskUserQuestion`:

> Configure Overleaf sync for this project?

1. **Yes** — collect the fields below.
2. **Skip for now** — leave the `overleaf:` block at its template defaults
   (the user can rerun `/omr:setup` or edit `config.yaml` later). Move to 6.4.

**Round 2 — auth pointer.** pyoverleaf authenticates from the logged-in
browser by default (no config needed). Only ask if the user wants the
headless cookie-file mode. `AskUserQuestion`:

> How should pyoverleaf authenticate?

1. **Native browser/keychain (default)** — leave `auth.cookie_path` blank;
   pyoverleaf reads the cookie from your logged-in browser at run time.
2. **Cookie file (headless)** — collect a file path into `auth.cookie_path`.

If the user picks the file mode, store the **path** only — never the cookie
value. If they paste a cookie value, respond:

> Keep the value out of `config.yaml` — give me the path to the JSON cookie
> file that holds it instead.

Leave `tool_installer` blank; `/omr:sync-overleaf` resolves it (uv preferred,
pipx fallback) on first run.

**Round 3 — local path + project names.** `AskUserQuestion` (free-form):

> Where should synced Overleaf projects live (relative to the repo root)?
> [default: `overleaf`]

Write it to `local_path` (default `overleaf` if the user accepts).

> Overleaf project name(s) for this repo? (comma-separated if more than one)

Write them as a YAML list under `project_names`. Each project syncs into
`<local_path>/<project_name>/`, so a repo with several papers keeps them in
separate subfolders (e.g. `overleaf/ARR-26-MemoVQ/`, `overleaf/AMLC-26-MemoVQ/`).

### 6.4 Literature-review defaults

Ask in `AskUserQuestion` rounds (2–3 questions each):

- `default_scope`: `local` / `global`.
- `output_languages`: `English only` / `English + Chinese` / `English + others
  (specify)`. Store as a list.
- `max_papers`: integer, default 50.
- `default_sources`: offer the full chain as the default; ask only if the user
  wants to trim it. Most users keep the default.

### 6.5 HPC pointer

`config_dir` is fixed at `./.omr/hpc/` — don't ask.

For `default_cluster`: list the `*.yaml` files currently in `./.omr/hpc/`
(written by Phase 5). Ask via `AskUserQuestion`:

> Which HPC config is the project default?

Options: one per file found, plus `None / not using HPC`. Store the chosen
**filename** (e.g. `acme-slurm.yaml`) in `default_cluster` — not the full
path. Skills join `config_dir` + `default_cluster` to resolve it.

If `./.omr/hpc/` is empty (Phase 5 skipped or opted out), leave
`default_cluster` blank and note the user can rerun `/omr:setup` after adding
a cluster.

### 6.6 Write the file

Render the collected values into the template (replacing every
`<placeholder>` and the `{{omr_version}}` token). Write `./.omr/config.yaml`
(`mkdir -p ./.omr` first). On a refresh, preserve any field the user didn't
revisit this run.

Echo to the user:

> Wrote `./.omr/config.yaml`. omr skills read this for defaults; edit it any
> time or rerun `/omr:setup` to reconfigure. Auth fields hold pointers only —
> no secret values are stored here.

### 6.7 Record for Phase 7

Pass forward: `config_phase: configured | skipped`, and the resolved
`./.omr/config.yaml` path so Phase 7's wrap-up can mention it.

## Handoff

> Phase 6 done — project config captured at `./.omr/config.yaml`. Moving to verify.
