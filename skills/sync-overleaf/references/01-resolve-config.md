# Phase 1 — Resolve config

**Goal:** read the `overleaf:` block of `./.omr/config.yaml`, validate it is
complete enough to sync, and resolve the three things later phases need: the
**method**, the **auth pointer** (a file path or env-var name — never the
value), and the **target project**. If the block is missing or incomplete,
stop and refer the user to `/omr:setup`.

## Invariants

- **Pointer only.** This phase records *where* the secret lives (a path or an
  env-var name). It never reads the cookie/token/key value. Resolution to the
  actual value happens in Phase 2, at the moment a tool needs it.
- **Config is the source of defaults; flags win.** Precedence is
  command-line flag > `./.omr/config.yaml` > built-in default.
- **Never inline a secret.** If an `auth.*` field looks like a literal secret
  (long opaque string, not a path or env-var name), stop per safety rail 5.

## Steps

### 1.1 Locate and read the config

Look for `./.omr/config.yaml` (project-local). If it does not exist, stop and
tell the user:

> No `./.omr/config.yaml` found. The Overleaf settings (sync method, auth
> pointer, project names) live there. Run `/omr:setup` to create it, then
> rerun `/omr:sync-overleaf`.

Read the file and parse the top-level `overleaf:` block. If the `overleaf:` key
is absent, or every field under it is still a `<placeholder>`, stop and tell the
user:

> `./.omr/config.yaml` exists but its `overleaf:` block isn't filled in.
> Run `/omr:setup` (it interviews you for the sync method, the auth pointer,
> and your Overleaf project name(s)), then rerun this skill.

Do not attempt to write or repair `config.yaml` from this skill — `/omr:setup`
owns that file.

### 1.2 Resolve the method

Determine `method` with this precedence:

1. `--method` flag, if passed.
2. `overleaf.sync_method` from config (`pyoverleaf` or `git`).
3. If neither resolves to a valid value, ask via `AskUserQuestion`
   (single-select): "Which sync method should I use?" → options `pyoverleaf` /
   `git`.

Validate the resolved value is exactly `pyoverleaf` or `git`. Anything else →
ask via `AskUserQuestion` to pick one.

### 1.3 Resolve the auth pointer (record location, not value)

Based on the resolved `method`, pull the relevant pointer fields from
`overleaf.auth` and record which one is set. **Do not read the file contents or
the env var value here** — just note the pointer.

- **pyoverleaf** needs one of:
  - `cookie_path` — a file holding the session cookie, or
  - `cookie_env` — the name of an env var holding it.
- **git** needs one of:
  - `ssh_key_path` — an SSH private-key file (for SSH remotes), or
  - `token_env` — the name of an env var holding an HTTPS token.

Build an `auth_pointer` record: `{kind: cookie_path|cookie_env|ssh_key_path|
token_env, value: <the path or env-var name as written in config>}`.

If **both** valid pointers for the method are set, prefer the file-path form
for git (`ssh_key_path`) / leave it to the user for pyoverleaf by asking via
`AskUserQuestion` which to use. If **neither** is set for the chosen method,
do not stop yet — pass `auth_pointer: null` forward; Phase 2 produces the
actionable "pointer resolves to nothing" guidance with the exact field to fill.

**Sanity check (safety rail 5):** if the pointer field's written value looks
like a literal secret rather than a path or an env-var name (e.g. it contains
`=`, spaces, or a long base64/hex blob, and is not an existing path or a plausible
`UPPER_SNAKE_CASE` env-var name), stop and tell the user:

> The `overleaf.auth.<field>` value in `config.yaml` looks like a secret value,
> not a pointer. Move the actual cookie/token/key out of the file and store
> only a path or env-var name there (rerun `/omr:setup` to fix it). I won't
> proceed with an inlined secret.

### 1.4 Resolve the target project

`overleaf.project_names` is a YAML list. Resolve `project` with this precedence:

1. `--project <name>` flag, if passed — validate it appears in
   `project_names`; if not, ask via `AskUserQuestion` to pick from the list.
2. If `project_names` has exactly one entry, use it.
3. If `project_names` has more than one entry and no `--project` flag, ask via
   `AskUserQuestion` (single-select): "Which Overleaf project should I sync?"
   with one option per name.
4. If `project_names` is empty or all placeholder, stop and refer to
   `/omr:setup`:

   > `overleaf.project_names` is empty in `config.yaml`. Add your Overleaf
   > project name(s) via `/omr:setup`, then rerun.

### 1.5 Resolve the direction

Resolve `direction` with this precedence:

1. `--direction` flag or positional `push`/`pull`/`sync`, if given. (A
   positional that contradicts an explicit `--direction` is invalid — stop and
   ask via `AskUserQuestion` to pick one.)
2. Otherwise ask via `AskUserQuestion` (single-select): "Which direction?" →
   `push (local → Overleaf)` / `pull (Overleaf → local)` /
   `sync (reconcile both)`.

### 1.6 Emit a no-secret summary

Print what was resolved, **with the pointer shown as a location, never a
value**:

```
Resolved Overleaf sync config:
  method:       git
  project:      ARR-26-MemoVQ
  direction:    push
  auth pointer: ssh_key_path → ~/.ssh/id_ed25519   (value not read)
  dry-run:      false
```

## Handoff

Hand `method`, `project`, `direction`, `auth_pointer`, and `dry_run` to Phase 2.
Echo one line:

> Phase 1 done — config resolved (method=`<method>`, project=`<project>`, direction=`<direction>`). Moving to preflight.
