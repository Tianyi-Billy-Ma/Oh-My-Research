# Phase 1 — Resolve config

**Goal:** read the `overleaf:` block of `./.omr/config.yaml`, validate it is
complete enough to sync via pyoverleaf, and resolve the things later phases
need: the **auth pointer** (a cookie file path — never the value, and optional
since browser login is the fallback), the **target project**, and the
**direction**. If the block is missing or incomplete, stop and refer the user
to `/omr:setup`.

## Invariants

- **pyoverleaf only.** This skill currently supports only the pyoverleaf
  transport. If config requests `git`, stop with the message in step 1.2 — the
  git method is not implemented yet.
- **Pointer only.** This phase records *where* the cookie lives (a path). It
  never reads the cookie value. Resolution happens in Phase 2/3, at the moment
  pyoverleaf needs it.
- **Config is the source of defaults; flags win.** Precedence is
  command-line flag > `./.omr/config.yaml` > built-in default.
- **Never inline a secret.** If `auth.cookie_path` looks like a literal cookie
  value (long opaque string, not a path), stop per safety rail 4.

## Steps

### 1.1 Locate and read the config

Look for `./.omr/config.yaml` (project-local). If it does not exist, stop and
tell the user:

> No `./.omr/config.yaml` found. The Overleaf settings (cookie pointer,
> project names) live there. Run `/omr:setup` to create it, then rerun
> `/omr:sync-overleaf`.

Read the file and parse the top-level `overleaf:` block. If the `overleaf:` key
is absent, or every field under it is still a `<placeholder>`, stop and tell the
user:

> `./.omr/config.yaml` exists but its `overleaf:` block isn't filled in.
> Run `/omr:setup` (it interviews you for the cookie pointer and your Overleaf
> project name(s)), then rerun this skill.

Do not write or repair `config.yaml` from this phase — `/omr:setup` owns that
file. (Phase 2 may write the single non-secret `overleaf.tool_installer` key;
nothing else.)

### 1.2 Check the sync method (pyoverleaf only)

Read `overleaf.sync_method`. Only `pyoverleaf` is supported right now:

- If it is `pyoverleaf` (or unset/blank — treat the default as `pyoverleaf`),
  continue.
- If it is `git`, stop and tell the user:

  > Your config sets `overleaf.sync_method: git`, but this skill only supports
  > the `pyoverleaf` method right now — the git transport isn't implemented
  > yet. Set `overleaf.sync_method: pyoverleaf` via `/omr:setup` (and fill in
  > a cookie pointer or rely on browser login), then rerun.

- Any other value → treat as invalid and stop with the same guidance,
  pointing the user to set it to `pyoverleaf`.

### 1.3 Resolve the auth pointer (record location, not value)

Pull `overleaf.auth.cookie_path` and record it. **Do not read the file
contents here** — just note the pointer.

Build an `auth_pointer` record:
`{kind: cookie_path, value: <the path as written in config>}` when set, or
`null` when `cookie_path` is blank/placeholder.

A `null` pointer is **not** an error: with no cookie file, `sync_overleaf.py`
falls back to pyoverleaf's native browser/keychain login in Phase 3. Pass
`auth_pointer: null` forward and let Phase 2 note the browser-login plan.

**Sanity check (safety rail 4):** if `cookie_path`'s written value looks like a
literal cookie value rather than a path (e.g. it contains `=`, spaces, or a long
base64/hex blob, and is not a plausible filesystem path), stop and tell the user:

> The `overleaf.auth.cookie_path` value in `config.yaml` looks like a cookie
> value, not a path. Move the actual cookie out of the file and store only a
> file path there (rerun `/omr:setup` to fix it). I won't proceed with an
> inlined secret.

### 1.4 Resolve the target project

`overleaf.project_names` is a YAML list. Resolve `project` with this precedence:

1. `--project <name>` flag, if passed — validate it appears in
   `project_names`; if not, ask via `AskUserQuestion` to pick from the list.
   (A 24-hex id passed via `--project` is also valid and goes straight through
   to the script.)
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
  method:       pyoverleaf
  project:      ARR-26-MemoVQ
  direction:    push
  auth pointer: cookie_path → ~/.config/pyoverleaf/cookies.json   (value not read)
                # or: (none) → native browser/keychain login
  dry-run:      false
```

## Handoff

Hand `project`, `direction`, `auth_pointer`, and `dry_run` to Phase 2. Echo one
line:

> Phase 1 done — config resolved (method=`pyoverleaf`, project=`<project>`, direction=`<direction>`). Moving to preflight.
