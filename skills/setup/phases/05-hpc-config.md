# Phase 5 — HPC / remote-server config (optional)

**Goal:** offer the user a chance to drop a per-cluster YAML config file into
their environment so future omr skills (and the user's own shell scripts)
know where to find scheduler and storage details for any remote compute
target. This phase is always optional and easy to opt out of.

## Invariants

- **YAML-config-only.** Never touch `~/.ssh/config`. Never run `ssh-keygen`,
  `ssh-copy-id`, or any other authentication command on the user's behalf.
- **Universal templates only.** The plugin ships `templates/hpc.yaml`; it
  does not ship site-specific (`nersc-perlmutter.yaml`, etc.) defaults.
  Users edit the rendered file with their real values.
- **Opt-out is sticky.** A `Never` answer at the top gate persists as
  `hpcSetupOptOut: true` in `.omr-config.json` so future runs auto-skip.
- **One backup per file per day.** When refreshing an existing config,
  back up to `<file>.backup.YYYY-MM-DD` before any write — don't pile up
  backups on multiple same-day runs.

## Steps

### 5.1 Gate — should we run this phase at all?

Read `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/.omr-config.json`. If
`hpcSetupOptOut` is `true`, skip the entire phase silently. Echo one line:

> HPC config phase skipped (`hpcSetupOptOut: true` in `.omr-config.json`).
> Re-enable by editing that file or rerunning with `--force`.

If `--force` was passed, ignore the opt-out flag.

Otherwise ask via `AskUserQuestion` (single-select):

> Configure HPC / remote-server access now? This drops a per-cluster YAML
> config file into your environment that future omr skills can read.

Options:
1. **Yes, configure a cluster** — proceed to 5.2.
2. **Not now** — skip this run only; ask again next time.
3. **Never, don't ask again** — persist `hpcSetupOptOut: true` and skip.

If `Not now`, set `hpc_phase=skipped` for the current run and proceed to
Phase 6.

If `Never`, also set `hpcSetupOptOut: true` in `.omr-config.json` (use the
same `jq` merge approach Phase 6 uses), then proceed to Phase 6.

### 5.2 Cluster ID

Ask via `AskUserQuestion` (free-form expected) for the cluster identifier
the user wants to configure. Suggest examples:

> Cluster ID (used as the filename, e.g. `nersc-perlmutter`,
> `lab-workstation`, `acme-slurm`):

Validate: must match `^[a-z][a-z0-9-]{0,30}$`. If invalid, ask again with a
clarifying note. The ID becomes the filename — `<id>.yaml`.

### 5.3 Resolve destination

Determine the install path based on the scope flag from SKILL.md:

- `scope=global` → `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hpc/<id>.yaml`
- `scope=local` → `./.omr/hpc/<id>.yaml`
- `scope=all` (no flag) → ask via `AskUserQuestion`:

  > Where should `<id>.yaml` live?
  >
  > 1. **Global** (`~/.claude/hpc/<id>.yaml`) — available to every Claude
  >    Code session for this user.
  > 2. **Project** (`./.omr/hpc/<id>.yaml`) — only for this project.

`mkdir -p` the parent directory before any write.

### 5.4 Check existing state

Classify the destination:

| State | Action |
| --- | --- |
| File does not exist | `CREATE_NEW` |
| File exists, byte-identical to `templates/hpc.yaml` | `ALREADY_PRISTINE` (effectively reinstall — no user edits to preserve) |
| File exists, has been edited from the template | `REFRESH_DECISION` (ask user) |
| File exists, but starts with a different `template_version` than the shipped template | `VERSION_MISMATCH` (also ask user) |

For diff detection, do a byte-level compare against the source template.
Don't try to be clever about whitespace.

### 5.5 Write / refresh

**CREATE_NEW:** copy `${CLAUDE_PLUGIN_ROOT}/templates/hpc.yaml` to the
destination. Confirm to the user:

> Wrote `<destination>` from `templates/hpc.yaml` (template_version
> `<template_version>`). Open it and replace the `<...>` placeholders with
> your real values.

**ALREADY_PRISTINE:** echo one line, no write:

> `<destination>` is already at the current template (template_version
> `<template_version>`). Nothing to do.

**REFRESH_DECISION** or **VERSION_MISMATCH:** ask via `AskUserQuestion`:

> `<destination>` already exists and has been edited / uses an older
> template. What now?

Options:
1. **Keep mine** — leave the file untouched.
2. **Overwrite with new template** — back up the existing file to
   `<destination>.backup.YYYY-MM-DD` (skip backup if a backup from today
   already exists), then copy the shipped template over it.
3. **Save new template alongside** — write the shipped template to
   `<destination>.new.yaml` so the user can diff and merge manually. Leave
   the existing file unchanged.

Act on the choice. Do not assume.

### 5.6 Record for Phase 6

Pass forward to Phase 6 (which writes `.omr-config.json`):

```yaml
hpc_phase: configured        # or "skipped" / "opted_out"
hpc_record:                  # null if skipped/opted-out
  id: <id>
  dest: <absolute path>
  templateVersion: <from-template>
  action: CREATE_NEW | ALREADY_PRISTINE | OVERWROTE | SAVED_ALONGSIDE | KEPT_MINE
  backedUpTo: <path-or-null>
```

Phase 6 appends this to a `hpcConfigs` array in `.omr-config.json`,
deduping by `dest`.

### 5.7 Tell the user what to do next

Print a short next-steps block:

> Next:
> 1. Open `<destination>` and fill in the `<...>` placeholders.
> 2. From any shell, verify access with: `ssh <user>@<hostname>`.
> 3. Future omr skills that need cluster info will read this file
>    automatically (project-local first, then user-global).

Do **not** run `ssh` from this skill. Interactive 2FA / password prompts
would block the session.

## Handoff

> Phase 5 done — HPC config recorded. Moving to verify.

Pass `hpc_phase` and `hpc_record` to Phase 6.
