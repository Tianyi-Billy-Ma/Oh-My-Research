# Phase 3 — Install plugin instructions into CLAUDE.md

**Goal:** idempotently register omr's plugin-level instructions inside the
user's CLAUDE.md so any Claude Code session in that scope knows about the
plugin (skills, MCP servers, conventions) without having to re-discover
them. Uses a versioned marker block, never destroys user content.

## Invariants

- **Insert-block only.** Never full-overwrite the target file.
- **One backup per target per day.** Don't pile up backups on re-runs.
- **Idempotent at the same version.** If the block is already installed at
  the current plugin version, skip silently with a one-line confirmation.
- **Stop on malformed state.** If markers are mismatched (only BEGIN, only
  END, nested, or wrong order), do not attempt to repair — stop and ask the
  user.

## Steps

### 3.1 Resolve targets from scope

Read `OMR_VERSION` from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`
(`.version` field).

Decide the target list based on the scope flag passed from SKILL.md:

- `scope=global` → `["${CLAUDE_CONFIG_DIR:-$HOME/.claude}/CLAUDE.md"]`
- `scope=local` → `["./.claude/CLAUDE.md"]`
- `scope=all` (no flag): use AskUserQuestion (single-select):

  > Where should omr install its plugin-level instructions?
  >
  > 1. **Global** (`~/.claude/CLAUDE.md`) — applies to every Claude Code
  >    session for this user. (Recommended for first-time install.)
  > 2. **Project** (`./.claude/CLAUDE.md`) — applies only to this project.
  > 3. **Both** — install in both files.
  > 4. **Skip** — don't touch any CLAUDE.md. Re-run with `--global` or
  >    `--local` later.

  Then resolve to one or both paths. If "Skip", record `skipped=true` and
  proceed to Phase 4 with no writes.

### 3.2 Load the template

Read `${CLAUDE_PLUGIN_ROOT}/templates/CLAUDE.md.partial` into a variable
`TEMPLATE_BODY`. If the file is missing, the plugin install is broken —
stop and tell the user to reinstall.

Construct the full block:

```
<!-- BEGIN omr version="$OMR_VERSION" -->
$TEMPLATE_BODY
<!-- END omr -->
```

The marker lines are the **only** strings phase 3 relies on for detection.
Don't change their format without updating the checker below.

### 3.3 Check each target

For each target path, classify the existing state. Use this decision matrix:

| State of target | Marker BEGIN | Marker END | Block version | Action |
| --- | --- | --- | --- | --- |
| File does not exist | — | — | — | `CREATE_NEW` |
| File exists, no markers | absent | absent | — | `APPEND` |
| File exists, markers balanced, same version | present | present | `=OMR_VERSION` | `ALREADY_INSTALLED` |
| File exists, markers balanced, older version | present | present | `<OMR_VERSION` | `REFRESH` |
| File exists, markers balanced, newer version | present | present | `>OMR_VERSION` | `DOWNGRADE_WARN` |
| File exists, markers unbalanced | only one | only the other | — | `MALFORMED` — stop and ask |
| File exists, nested markers (`BEGIN omr` inside an existing `BEGIN omr` block) | — | — | — | `MALFORMED` — stop and ask |

How to parse:

```bash
# count BEGIN / END markers
grep -c '^<!-- BEGIN omr ' "$TARGET" 2>/dev/null
grep -c '^<!-- END omr -->$' "$TARGET" 2>/dev/null

# extract existing block version (only when both markers are present once)
existing_version=$(grep -oE 'BEGIN omr version="[^"]+"' "$TARGET" \
  | head -1 | sed -E 's/.*version="([^"]+)"/\1/')
```

String-equality comparison is enough for the version check. Don't bother
with semver math — refresh is acceptable in either direction once the user
opts in.

### 3.4 Confirm consent before writes

For every target that maps to `CREATE_NEW`, `APPEND`, `REFRESH`, or
`DOWNGRADE_WARN`, ask via AskUserQuestion (one prompt that lists all
targets and their actions at once — don't fire a prompt per target):

> About to update the following CLAUDE.md file(s) with the omr v$OMR_VERSION block:
>
> - `~/.claude/CLAUDE.md` — REFRESH (currently v0.6.0)
> - `./.claude/CLAUDE.md` — CREATE_NEW
>
> Existing files will be backed up first. Continue?

Options:
1. Yes, apply all
2. Yes for a subset (list which)
3. No, skip the install entirely

Skip without consent. `ALREADY_INSTALLED` targets need no prompt — just
note them in the summary.

For `DOWNGRADE_WARN`, append a stronger note in the prompt:

> Note: `~/.claude/CLAUDE.md` already has omr v0.9.0 installed; refreshing
> with v0.7.0 will downgrade. Continue only if you know why.

### 3.5 Backup, then write

For each consented target:

1. **Backup.** Compute today's backup path: `<target>.backup.YYYY-MM-DD`.
   If it already exists (e.g. user reran today), skip the backup — don't
   overwrite an earlier one. If `CREATE_NEW`, no backup is needed.

   ```bash
   today=$(date +%Y-%m-%d)
   backup="$TARGET.backup.$today"
   if [ -f "$TARGET" ] && [ ! -f "$backup" ]; then
     cp "$TARGET" "$backup"
   fi
   ```

2. **Apply the action.**

   - `CREATE_NEW`: `mkdir -p "$(dirname "$TARGET")"` then write the full
     block to `$TARGET`. End with a trailing newline.
   - `APPEND`: open the file, ensure it ends with a blank line, append the
     block, end with a trailing newline.
   - `REFRESH` / `DOWNGRADE_WARN`: replace the marker-bounded region in
     place. Use a script — do NOT just splice strings naively, because the
     template body can contain `</summary>` or any markdown that breaks
     ad-hoc sed:

     ```bash
     python3 - <<'PY'
     import os, re, sys
     target = os.environ['TARGET']
     new_block = os.environ['NEW_BLOCK']  # full block including markers
     text = open(target).read()
     pattern = re.compile(r'^<!-- BEGIN omr [^>]*-->\n.*?\n<!-- END omr -->\n?', re.S | re.M)
     out = pattern.sub(new_block.rstrip() + "\n", text, count=1)
     open(target, 'w').write(out)
     PY
     ```

3. Verify the result: re-grep BEGIN and END counts, confirm exactly one
   each. If verification fails, restore from backup and stop.

### 3.6 Summary

Print a short table of what happened per target:

```
~/.claude/CLAUDE.md    REFRESH      v0.6.0 → v0.7.0   backup: ~/.claude/CLAUDE.md.backup.2026-05-25
./.claude/CLAUDE.md    CREATE_NEW   —      → v0.7.0   (no prior file)
```

Or, when nothing was done:

```
~/.claude/CLAUDE.md    ALREADY_INSTALLED at v0.7.0 — no action
```

Or, when user skipped:

```
CLAUDE.md install skipped — rerun /omr:setup with --global or --local later.
```

## Handoff

> Phase 3 done — CLAUDE.md state captured. Moving to remediation.

Pass these to Phase 4: the list of targets actually touched, and the
`skipped` flag (so Phase 5's wrap-up can mention it).
