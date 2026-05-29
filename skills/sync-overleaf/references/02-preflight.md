# Phase 2 — Preflight

**Goal:** confirm the chosen transport can actually run before touching any
files: the tool is installed, the auth pointer resolves to *something* (without
ever reading the secret into the conversation), and the target project /
remote is reachable. On any gap, give the user precise, actionable guidance and
stop — never auto-install or auto-configure credentials.

## Invariants

- **Resolve the secret only at the point of use, never into the chat.** Check
  *presence* of the credential, not its value. For a file pointer, check the
  file exists and is readable (`[ -r "$path" ]`) and is non-empty
  (`[ -s "$path" ]`) — never `cat` it. For an env-var pointer, check it is set
  and non-empty (`[ -n "${VAR:-}" ]`) — never `echo "$VAR"`. The actual value
  is read by the underlying tool in Phase 3, not by you.
- **No installs, no credential setup.** Don't `pip install pyoverleaf`, don't
  `git remote add`, don't `ssh-keygen`. Verify; if missing, instruct.
- **Reachability probe must not mutate.** Listing files / checking a remote is
  fine; pushing/pulling is Phase 3.

## Steps

### 2.1 Resolve the working directory

Determine the local LaTeX/paper directory to sync. Default to the current
working directory. If the directory has no `.tex` files and no obvious paper
layout, confirm the directory with the user via `AskUserQuestion`
(single-select: `use current directory` / `let me specify a path`). Record it
as `local_dir`.

### 2.2 Verify the tool is available

**If `method == pyoverleaf`:**

Check the `pyoverleaf` package/CLI is importable/available, e.g.:

```bash
python3 -c "import pyoverleaf" 2>/dev/null && echo present || echo missing
```

If missing, stop with guidance (do not install it yourself):

> `pyoverleaf` isn't installed in this environment. Install it
> (`pip install pyoverleaf`, or add it to your project's deps) and rerun. I
> don't install packages on your behalf.

**If `method == git`:**

Check `git` is available (`git --version`). Then determine the Overleaf git
remote for the chosen project. Overleaf project git URLs look like
`https://git.overleaf.com/<project-id>` (or the SSH equivalent). If the
`local_dir` is already a git repo with an `overleaf` (or `origin`) remote
pointing at `git.overleaf.com`, use it. If not, stop with guidance:

> No Overleaf git remote is configured in `<local_dir>`. Add it yourself
> (Overleaf → Menu → Git → copy the clone URL, then
> `git remote add overleaf <url>`), then rerun. I don't add remotes with
> embedded tokens on your behalf.

Do not embed a token in any remote URL you suggest — point at the env-var /
SSH-key pointer instead (step 2.3).

### 2.3 Resolve the auth pointer to a presence check (never a value)

Using the `auth_pointer` record from Phase 1:

| `auth_pointer.kind` | Presence check (no value ever printed) | If it resolves to nothing |
| --- | --- | --- |
| `cookie_path` | `[ -r "$path" ] && [ -s "$path" ]` | "Cookie file `<path>` is missing or empty. Export your Overleaf session cookie into it (keep the value out of chat), or switch the pointer to an env var via `/omr:setup`." |
| `cookie_env` | `[ -n "${VAR:-}" ]` | "Env var `$VAR` is unset/empty in this shell. Set it (e.g. in your shell profile or `.env`) so the tool can read it, then rerun. I won't read or print its value." |
| `ssh_key_path` | `[ -r "$path" ]` | "SSH key `<path>` isn't readable. Point at the right key via `/omr:setup`, or ensure the file exists with correct permissions." |
| `token_env` | `[ -n "${VAR:-}" ]` | "Env var `$VAR` is unset/empty. Set your Overleaf git token there (value stays out of chat), then rerun." |

If `auth_pointer` was `null` (Phase 1 found neither pointer for the method),
stop now with the exact field the user must fill:

> The `overleaf.auth` block has no pointer for method `<method>`. For
> `pyoverleaf` set `cookie_path` **or** `cookie_env`; for `git` set
> `ssh_key_path` **or** `token_env`. Rerun `/omr:setup` to add it (store a
> path or env-var name — never the secret itself).

**How the secret reaches the tool in Phase 3 (record the plan, don't execute):**

- `cookie_path` → Phase 3 lets the tool open the file by path, or pipes its
  contents via stdin to the tool. You never `cat` it into a variable you print.
- `cookie_env` / `token_env` → Phase 3 invokes the tool with the env var
  already in its environment (e.g. the tool reads `$VAR` itself). You never
  expand `$VAR` into a shown command.
- `ssh_key_path` → Phase 3 relies on the SSH agent / `GIT_SSH_COMMAND -i
  <path>` so `git` reads the key; the key bytes never enter the conversation.

### 2.4 Reachability probe (read-only)

A light, non-mutating check that the remote/project is reachable:

- **pyoverleaf:** list the user's projects (read-only) and confirm the resolved
  `project` name exists. If the name isn't found, show the available names and
  ask via `AskUserQuestion` to pick the right one (or stop if none match).
- **git:** `git ls-remote <remote>` (read-only) to confirm the remote answers
  with the resolved credential. If it fails with an auth error, surface the
  error class (not the credential) and point back at the pointer guidance in
  2.3.

If the probe needs the credential, this is the first point of use — wire it per
the 2.3 plan and never echo it.

### 2.5 Preflight verdict

Summarize, no secrets:

```
Preflight OK:
  tool:         git 2.43  (present)
  local_dir:    /Users/.../paper
  remote:       overleaf → git.overleaf.com/<id>  (reachable)
  auth pointer: ssh_key_path → ~/.ssh/id_ed25519  (readable; value not read)
```

If any check failed, stop here with the specific guidance from above — do not
proceed to Phase 3.

## Handoff

Hand `local_dir`, the verified tool/remote, and the (still pointer-only) auth
plan to Phase 3. Echo one line:

> Phase 2 done — preflight passed (tool + auth pointer + remote verified, no secret read). Moving to sync.
