# Phase 3 — Sync

**Goal:** perform the requested `push` / `pull` / `sync` via
`scripts/sync_overleaf.py`. ALWAYS compute and show a dry-run diff first, then
get explicit `AskUserQuestion` consent before mutating either side. Pushing to a
shared Overleaf project is risky and hard to reverse — treat every push as a
gated action.

## Invariants

- **Diff before mutate, every time.** Even with no `--dry-run`, the first thing
  this phase does is produce a diff and show it. Mutation happens only after
  consent.
- **Consent gates pushes and overwriting pulls.** A push to Overleaf and a pull
  that would overwrite local files each require an explicit `AskUserQuestion`
  consent. A `--dry-run` run stops after showing the diff — no consent prompt,
  no mutation.
- **Secrets stay behind the pointer.** Pass `--cookies <path>` to the script so
  pyoverleaf opens the file itself, or omit it for browser login. Never expand a
  cookie value into a command you display or log.
- **Push is explicit-paths only.** `sync_overleaf.py push` requires named
  files; there is no recursive default. Never synthesize a "push everything"
  invocation.

## Invocation shape

Run `sync_overleaf.py` under the pyoverleaf tool interpreter resolved in Phase 2
(the `uv tool` / `pipx` env where `pyoverleaf` is importable). The global
options come from the resolved config:

```bash
# <PY> = the tool-env python from Phase 2
# <SCRIPT> = ${CLAUDE_PLUGIN_ROOT}/skills/sync-overleaf/scripts/sync_overleaf.py
# --cookies is included only when auth_pointer.kind == cookie_path; otherwise omit it
<PY> <SCRIPT> --project "<project>" --paper-dir "<local_dir>" [--cookies "<path>"] <subcommand> ...
```

Show the command with the cookie path shown as a label, never its contents.

### 3.1 Compute the dry-run diff

Produce a human-readable diff of what *would* change, scoped to `direction`:

- **push** — files that differ local→Overleaf.
- **pull** — files that differ Overleaf→local.
- **sync** — both directions, flagging conflicts (files that differ on both
  sides).

Use the script's read-only subcommands to build the picture:

```bash
# inventory: local-only / remote-only / both
<PY> <SCRIPT> --project "<project>" --paper-dir "<local_dir>" [--cookies "<path>"] status

# content-level preview of what a pull WOULD write (never writes under --dry)
<PY> <SCRIPT> --project "<project>" --paper-dir "<local_dir>" [--cookies "<path>"] pull --dry
```

For a **push**, cross-reference the named target files against `status` output
to show which are `create` vs `overwrite` on the remote. For a **pull**, the
`pull --dry` output already lists `[new]` / `[modified]` / `[local-only]`. For a
**sync**, combine both to surface files that changed on both sides.

Present the diff compactly:

```
Dry-run (push → ARR-26-MemoVQ):
  M  sections/intro.tex   (overwrite on remote)
  A  figures/arch.pdf     (new on remote)
  2 file(s) to push
```

### 3.2 If `--dry-run`: stop here

If `dry_run` is true, echo:

> Dry-run only — nothing was changed on either side. Rerun without `--dry-run`
> to apply (you'll be asked to confirm before any write).

Then go straight to Phase 4 (which will report "no changes applied").

### 3.3 Conflict detection (sync / overwriting cases)

- **sync:** if any file changed on both sides, list the conflicting files and
  ask via `AskUserQuestion` (single-select per the set, or one decision for
  all): `prefer local (push)` / `prefer Overleaf (pull)` / `abort and let me
  resolve manually`. Do not auto-merge silently — pyoverleaf does file-level
  overwrite, so the chosen side wins wholesale for each file.
- **pull that overwrites local edits:** if `pull --dry` shows local files would
  be `[modified]` (overwritten), call this out explicitly in the consent prompt
  in 3.4.

### 3.4 Consent gate (push, or overwriting pull)

Before any mutation, ask via `AskUserQuestion` (single-select). Phrase the
question to match the action and name the irreversible part:

For a **push**:

> Apply this push to Overleaf project `<project>`? This uploads the files above
> to the shared project — collaborators will see them, and an overwrite
> replaces the remote file (Overleaf keeps version history, but it's still a
> live edit).

Options:
1. **Yes, push** — apply the changes shown.
2. **No, cancel** — change nothing.
3. **Show full diff first** — render the full per-line diff, then re-ask 3.4.

For an **overwriting pull**:

> Apply this pull? It will overwrite these local files: `<list>`. Local changes
> to them will be lost.

Options:
1. **Yes, overwrite local** — apply.
2. **Back up local first** — copy the about-to-be-overwritten files to
   `<file>.local.backup.YYYY-MM-DD`, then apply.
3. **No, cancel** — change nothing.

A non-overwriting pull (only `[new]` files, clean target) may proceed after the
dry-run is shown, but still announce what you're applying.

### 3.5 Apply

Only after consent, run the mutating subcommand, wiring the cookie per the Phase
2 plan (never echoing it):

- **push:** `<PY> <SCRIPT> --project "<project>" --paper-dir "<local_dir>"
  [--cookies "<path>"] push <file> [<file> ...]` — only the explicitly named,
  consented files.
- **pull:** `<PY> <SCRIPT> ... pull -y` (consent already gathered in 3.4; `-y`
  skips the script's own prompt). If the user chose "back up local first" in
  3.4, make the `.local.backup.YYYY-MM-DD` copies *before* running the pull.
- **sync:** apply the user's per-file choice from 3.3 — push the files where
  local wins, pull the files where Overleaf wins. Drive each side with the
  matching subcommand above.

Show the command you ran with the cookie path shown as a label (e.g.
`--cookies <cookies.json>`), never its contents.

## Handoff

Hand the applied action (or "no changes / cancelled / dry-run") and the list of
changed files to Phase 4. Echo one line:

> Phase 3 done — `<applied push|applied pull|sync reconciled|dry-run only|cancelled>`. Moving to verify.
