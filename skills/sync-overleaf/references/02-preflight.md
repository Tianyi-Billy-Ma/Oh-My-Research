# Phase 2 — Preflight

**Goal:** confirm pyoverleaf can actually run before touching any files. Detect
the `pyoverleaf` tool; if it's missing, install it into the **shared tool env**
(uv tool / pipx) after `AskUserQuestion` consent — never into the research
project's venv. Verify the auth pointer resolves to *something* (without ever
reading the secret into the conversation), and confirm the target project is
reachable. On any gap, give precise, actionable guidance and stop.

## Invariants

- **Shared tool env only — NEVER the project venv.** pyoverleaf is a global
  cross-project utility. Install it with `uv tool install pyoverleaf`
  (preferred) or `pipx install pyoverleaf` (fallback). **Never** run
  `uv add pyoverleaf` or `pip install pyoverleaf` inside the research project's
  virtualenv — that pollutes the project's dependency set.
- **Resolve the secret only at the point of use, never into the chat.** Check
  *presence* of the credential, not its value. For a cookie file pointer, check
  the file exists and is readable (`[ -r "$path" ]`) and non-empty
  (`[ -s "$path" ]`) — never `cat` it. The actual value is read by pyoverleaf
  in Phase 3, not by you.
- **Confirm before installing.** Use `AskUserQuestion` before running any
  installer; don't install silently.
- **Reachability probe must not mutate.** Listing projects/files is fine;
  pushing/pulling is Phase 3.

## Steps

### 2.1 Resolve the working directory

Determine the local LaTeX/paper directory to sync. Default to the current
working directory. If the directory has no `.tex` files and no obvious paper
layout, confirm the directory with the user via `AskUserQuestion`
(single-select: `use current directory` / `let me specify a path`). Record it
as `local_dir`.

### 2.2 Detect pyoverleaf, install via the shared tool env if missing

Check whether the `pyoverleaf` CLI is already on `PATH`:

```bash
command -v pyoverleaf
```

**If present:** use it. Record the resolved tool. (To run `sync_overleaf.py`
you also want the tool's own Python interpreter — the env that
`uv tool` / `pipx` created, where `pyoverleaf` is importable. Resolve that
interpreter and remember it for Phase 3.)

**If missing:** auto-detect an installer and install into the shared tool env.

1. Detect installers:

   ```bash
   command -v uv    # preferred
   command -v pipx  # fallback
   ```

2. Pick the installer:
   - If `uv` is present → use `uv tool install pyoverleaf`.
   - Else if `pipx` is present → use `pipx install pyoverleaf`.
   - If **both** present → prefer `uv`.
   - If **neither** present → stop with guidance and do not proceed:

     > Neither `uv` nor `pipx` is available, so I can't install `pyoverleaf`
     > into an isolated tool environment. Install one of them first
     > (`uv`: https://docs.astral.sh/uv/ , or `pipx`: https://pipx.pypa.io/),
     > then rerun `/omr:sync-overleaf`. I won't install pyoverleaf into your
     > project's venv.

3. **Ask via `AskUserQuestion`** before installing (single-select):

   > `pyoverleaf` isn't installed. Install it into an isolated tool
   > environment with `<uv tool install pyoverleaf | pipx install pyoverleaf>`?
   > (This is a cross-project utility — it will NOT be added to your project's
   > venv.)

   Options:
   1. **Yes, install** — run the detected installer command.
   2. **No, I'll install it myself** — stop with the command shown so the user
      can run it, then rerun the skill.

4. On consent, run the installer. After it completes, re-check
   `command -v pyoverleaf` to confirm success. If it still isn't found, stop
   and surface the installer's error.

### 2.3 Persist the resolved installer

Record which installer is in effect (or was used) to `./.omr/config.yaml` under
`overleaf.tool_installer` (`uv` or `pipx`). This is the one config write this
skill performs — it's a non-secret preference, not credential data. Insert or
update only that key; preserve everything else in the file. If `pyoverleaf` was
already present and you can tell which installer owns it (e.g. it lives under a
`uv tool` or `pipx` path), record that; if you can't tell, leave the field as
the user's prior value or unset.

### 2.4 Resolve the auth pointer to a presence check (never a value)

Using the `auth_pointer` record from Phase 1:

| `auth_pointer.kind` | Presence check (no value ever printed) | If it resolves to nothing |
| --- | --- | --- |
| `cookie_path` | `[ -r "$path" ] && [ -s "$path" ]` | "Cookie file `<path>` is missing or empty. Dump your Overleaf session cookies into it as JSON (keep the value out of chat), or omit the cookie pointer to use pyoverleaf's native browser/keychain login." |
| `null` (no cookie_path set) | (nothing to check) | Not an error: with no `cookie_path`, `sync_overleaf.py` falls back to native browser/keychain login (`login_from_browser`). Note this and continue. |

**Two auth modes (record the plan, don't execute):**

- `cookie_path` set and the file exists → Phase 3 passes `--cookies <path>` to
  `sync_overleaf.py`, which calls `api.login_from_cookies(json.loads(...))`.
  The script opens the file itself; you never `cat` it into a printed command.
- no `cookie_path` (or the file is absent) → Phase 3 omits `--cookies`, and
  pyoverleaf uses `api.login_from_browser()` (browser session + keychain). On
  macOS this may prompt the user for keychain access; that's the user's action,
  not something the agent can do for them.

### 2.5 Reachability probe (read-only)

A light, non-mutating check that the project is reachable: list the user's
projects (`sync_overleaf.py ... status` reaches the API read-only, or
equivalently `pyoverleaf ls`) and confirm the resolved `project` name (or id)
exists. If a name isn't found, show the available names and ask via
`AskUserQuestion` to pick the right one (or stop if none match). If the probe
needs the cookie, this is the first point of use — wire it per the 2.4 plan and
never echo it.

### 2.6 Preflight verdict

Summarize, no secrets:

```
Preflight OK:
  tool:        pyoverleaf  (present; installer: uv tool)
  python:      <tool-env interpreter for sync_overleaf.py>
  local_dir:   /Users/.../paper
  project:     ARR-26-MemoVQ  (reachable)
  auth mode:   cookie_path → ~/.config/pyoverleaf/cookies.json  (readable; value not read)
               # or: native browser/keychain login (no cookie file)
```

If any check failed, stop here with the specific guidance from above — do not
proceed to Phase 3.

## Handoff

Hand `local_dir`, the resolved pyoverleaf tool + its interpreter, the persisted
`tool_installer`, and the (still pointer-only) auth plan to Phase 3. Echo one
line:

> Phase 2 done — preflight passed (pyoverleaf available + auth mode + project verified, no secret read). Moving to sync.
