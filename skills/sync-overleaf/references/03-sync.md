# Phase 3 — Sync

**Goal:** perform the requested `push` / `pull` / `sync`. ALWAYS compute and
show a dry-run diff first, then get explicit `AskUserQuestion` consent before
mutating either side. Pushing to a shared Overleaf project is risky and hard to
reverse — treat every push as a gated action. Force-push needs its own consent.

## Invariants

- **Diff before mutate, every time.** Even with no `--dry-run`, the first thing
  this phase does is produce a diff and show it. Mutation happens only after
  consent.
- **Consent gates pushes and overwriting pulls.** A push to Overleaf and a pull
  that would overwrite local files each require an explicit `AskUserQuestion`
  consent. A `--dry-run` run stops after showing the diff — no consent prompt,
  no mutation.
- **Secrets stay behind the pointer.** Wire the credential into the tool per
  the Phase 2 plan (env var the tool reads, stdin, or `GIT_SSH_COMMAND -i`).
  Never expand a secret into a command you display or log.
- **No force without explicit consent.** `git push --force` /
  `--force-with-lease` requires a separate consent naming the consequence.

## Steps

### 3.1 Compute the dry-run diff

Produce a human-readable diff of what *would* change, scoped to `direction`:

- **push** — files that differ local→Overleaf: added, modified, deleted on the
  Overleaf side.
- **pull** — files that differ Overleaf→local: added, modified, deleted locally.
- **sync** — both directions, flagging conflicts (a file changed on both sides
  since the last common state).

**git method:**

```bash
# fetch is read-only; uses the Phase 2 auth wiring (no secret echoed)
git fetch overleaf
git --no-pager diff --stat HEAD overleaf/master   # or the project's default branch
```

For `push` also show `git --no-pager log --oneline HEAD ^overleaf/master`
(local commits not yet on Overleaf). For `pull` show the reverse.

**pyoverleaf method:** list remote files and compare against `local_dir`
(size/mtime/hash). Render an added/modified/deleted table. Use a temp scratch
area for any downloaded comparison copies; never overwrite `local_dir` during
the dry-run.

Present the diff compactly:

```
Dry-run (push → ARR-26-MemoVQ):
  M  sections/intro.tex      (+12 / -3)
  M  main.tex                (+1 / -1)
  A  figures/arch.pdf        (new, 84 KB)
  D  scratch.tex             (would be removed on Overleaf)
  3 modified, 1 added, 1 deleted
```

### 3.2 If `--dry-run`: stop here

If `dry_run` is true, echo:

> Dry-run only — nothing was changed on either side. Rerun without `--dry-run`
> to apply (you'll be asked to confirm before any write).

Then go straight to Phase 4 (which will report "no changes applied").

### 3.3 Conflict detection (sync / overwriting cases)

- **sync:** if any file changed on both sides, list the conflicting files and
  ask via `AskUserQuestion` (single-select per the set, or one decision for
  all): `prefer local` / `prefer Overleaf` / `abort and let me resolve
  manually`. Do not auto-merge silently. For git, prefer a rebase/merge that
  surfaces conflict markers over any `-X ours/theirs` shortcut unless the user
  explicitly picks a side.
- **pull that overwrites local edits:** if the dry-run shows local files would
  be overwritten (modified locally but also changed remotely, or simply
  replaced), call this out explicitly in the consent prompt in 3.4.

### 3.4 Consent gate (push, or overwriting pull)

Before any mutation, ask via `AskUserQuestion` (single-select). Phrase the
question to match the action and name the irreversible part:

For a **push**:

> Apply this push to Overleaf project `<project>`? This uploads the changes
> above to the shared project — collaborators will see them and it's not easily
> reversible.

Options:
1. **Yes, push** — apply the changes shown.
2. **No, cancel** — change nothing.
3. **Show full diff first** — render the full per-line diff, then re-ask 3.4.

For an **overwriting pull**:

> Apply this pull? It will overwrite these local files: `<list>`. Local changes
> to them will be lost.

Options:
1. **Yes, overwrite local** — apply.
2. **Stash/back up local first** — copy the about-to-be-overwritten files to
   `<file>.local.backup.YYYY-MM-DD` (or `git stash`), then apply.
3. **No, cancel** — change nothing.

A non-overwriting pull (clean/empty target) may proceed after the dry-run is
shown, but still announce what you're applying.

### 3.5 Apply

Only after consent, run the mutation, wiring the credential per the Phase 2
plan (never echoing it):

- **git push:** `git push overleaf HEAD:master` (or the project branch). Do
  **not** add `--force`. If a non-fast-forward rejection occurs, do NOT retry
  with `--force` automatically — go to 3.6.
- **git pull:** `git pull --ff-only overleaf master` when possible; if a merge
  is needed and the user chose to proceed, run the merge surfacing conflicts.
- **pyoverleaf push/pull:** upload/download the diffed files only. Apply
  deletions only if the diff showed them and the user consented to that diff.

Show the command you ran with the secret redacted (e.g. `GIT_SSH_COMMAND='ssh
-i <key>' git push overleaf HEAD:master` — show `<key>` as the path label, never
key contents; for token remotes show the host, never the token).

### 3.6 Force-push (only on explicit, separate consent)

If a push is rejected as non-fast-forward, do not force automatically. Ask via
`AskUserQuestion` (single-select):

> The push was rejected because Overleaf has commits your local branch doesn't.
> A force-push would **overwrite the Overleaf history** with your local version,
> discarding those remote commits. How do you want to proceed?

Options:
1. **Pull/rebase first, then push** (recommended, non-destructive) — fetch,
   rebase local onto `overleaf/master`, resolve any conflicts (3.3), re-attempt
   a normal push.
2. **Force-push (overwrite Overleaf)** — only on this explicit choice run
   `git push --force-with-lease overleaf HEAD:master`. Prefer
   `--force-with-lease` over `--force`.
3. **Cancel** — change nothing.

Never reach option 2 without the user selecting it here.

## Handoff

Hand the applied action (or "no changes / cancelled / dry-run") and the list of
changed files to Phase 4. Echo one line:

> Phase 3 done — `<applied push|applied pull|sync reconciled|dry-run only|cancelled>`. Moving to verify.
