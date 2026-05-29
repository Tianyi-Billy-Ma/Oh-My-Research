# Phase 4 — Verify

**Goal:** confirm the sync result matches intent, report exactly what changed
(no secrets), and close the loop. This is the terminal phase.

## Invariants

- **Read-only.** Verification probes only; no further mutation.
- **No secrets in the report.** The summary names files, counts, and the
  pointer *location* — never the cookie/token/key value.

## Steps

### 4.1 Confirm the post-state

Re-run the read-only comparison from Phase 3.1 (`sync_overleaf.py ... status`,
and `pull --dry` for content-level confirmation) and confirm it now reflects the
applied action:

- **After a push:** re-run `status` (and `pull --dry` for the pushed paths) and
  confirm the targeted files now match between local and Overleaf — they should
  no longer appear as `[modified]`/remote-only diffs.
- **After a pull:** the local files should now match what Overleaf had. Confirm
  the previously-differing files are reconciled (`pull --dry` reports "local
  already matches Overleaf" for them).
- **After a sync:** confirm both sides agree (or that the only remaining
  differences are ones the user chose to leave).
- **After dry-run / cancel:** confirm nothing changed — both sides are exactly
  as before.

If the post-state does not match intent (e.g. a push appears partial), say so
plainly and suggest the next action (rerun the same direction, or inspect via
the native Overleaf UI). Do not silently retry.

### 4.2 Report what changed

Print a final block populated from Phase 3:

```
✓ sync-overleaf complete
  action:    push → ARR-26-MemoVQ (pyoverleaf)
  changed:   2 pushed
             M sections/intro.tex
             A figures/arch.pdf
  backups:   (none)            # or list any .local.backup.YYYY-MM-DD made in 3.4
  auth:      cookie_path → ~/.config/pyoverleaf/cookies.json (value never read)
             # or: native browser/keychain login (no cookie file)
```

For a cancelled or dry-run run, render `action: dry-run only (nothing applied)`
or `action: cancelled (nothing applied)` and an empty `changed` list.

### 4.3 Pointer for next steps

End with one line tailored to the action:

- After a **push:** "Open the project in Overleaf to confirm the compile is
  green — this skill doesn't compile LaTeX."
- After a **pull:** "Local files updated; rebuild/compile locally as needed."
- After **sync:** "Both sides reconciled. Rerun `/omr:sync-overleaf --dry-run`
  anytime to check for new drift."
- After **dry-run/cancel:** "Rerun without `--dry-run` (and confirm at the
  prompt) when you're ready to apply."

## Handoff

This is the terminal phase. Echo:

> omr:sync-overleaf complete.

…and stop.
