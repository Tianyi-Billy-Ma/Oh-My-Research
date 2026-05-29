# Phase 5 — HPC / remote-server config (optional)

**Goal:** offer the user a chance to drop a per-cluster YAML config file into
their environment so future omr skills (and the user's own shell scripts)
know where to find scheduler and storage details for any remote compute
target. This phase is always optional and easy to opt out of.

## Invariants

- **YAML-config-only.** Never touch `~/.ssh/config`. Never run `ssh-keygen`,
  `ssh-copy-id`, or any other authentication command on the user's behalf.
- **Universal templates only.** The plugin ships `skills/setup/templates/hpc.yaml`; it
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

### 5.3 Render the template

Before any classification or write, render the shipped template by
substituting `{{omr_version}}` with the current plugin version. Read the
version from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` → `.version`.

```bash
OMR_VERSION=$(jq -r '.version' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json")
RENDERED=$(sed "s/{{omr_version}}/${OMR_VERSION}/g" "${CLAUDE_PLUGIN_ROOT}/skills/setup/templates/hpc.yaml")
```

Subsequent steps (`5.5` classification, `5.6` writes) operate on `RENDERED`,
not the raw template. This keeps the installed YAML's `template_version`
in lockstep with the plugin version it was installed under.

### 5.4 Resolve destination

HPC configs are always project-local. The install path is:

- `./.omr/hpc/<id>.yaml`

There is no global (`~/.claude/hpc/`) option — every HPC config lives in the
project under `./.omr/hpc/`, the same way `./.omr/config.yaml` does. The
`--global` / `--local` flags do **not** affect this phase; they only scope
the CLAUDE.md install (Phase 3) and token remediation (Phase 4). Don't ask
the user where to put the file.

`mkdir -p ./.omr/hpc` before any write.

### 5.5 Check existing state

Classify the destination by comparing against the **rendered** template
from 5.3 (not the raw file on disk):

| State | Action |
| --- | --- |
| File does not exist | `CREATE_NEW` |
| File byte-identical to `RENDERED` | `ALREADY_PRISTINE` (no user edits to preserve) |
| File `template_version` matches `OMR_VERSION` but content differs | `REFRESH_DECISION` (user edited it) |
| File `template_version` differs from `OMR_VERSION` | `VERSION_MISMATCH` (template itself changed) |

For diff detection, do a byte-level compare against `RENDERED`. Don't try
to be clever about whitespace.

### 5.6 Write / refresh

**CREATE_NEW:** write `RENDERED` to the destination (don't `cp` the raw
template — write the version-substituted string). Confirm to the user:

> Wrote `<destination>` from `skills/setup/templates/hpc.yaml` (template_version
> `<OMR_VERSION>`). Open it and replace the `<...>` placeholders with
> your real values.

**ALREADY_PRISTINE:** echo one line, no write:

> `<destination>` is already at the current template (template_version
> `<OMR_VERSION>`). Nothing to do.

**REFRESH_DECISION** or **VERSION_MISMATCH:** ask via `AskUserQuestion`:

> `<destination>` already exists and has been edited / uses an older
> template_version (`<file's version>` → `<OMR_VERSION>`). What now?

Options:
1. **Keep mine** — leave the file untouched.
2. **Overwrite with new template** — back up the existing file to
   `<destination>.backup.YYYY-MM-DD` (skip backup if a backup from today
   already exists), then write `RENDERED` over it.
3. **Save new template alongside** — write `RENDERED` to
   `<destination>.new.yaml` so the user can diff and merge manually.
   Leave the existing file unchanged.

Act on the choice. Do not assume.

### 5.7 Record for Phase 6

Pass forward to Phase 6 (which writes `.omr-config.json`):

```yaml
hpc_phase: configured        # or "skipped" / "opted_out"
hpc_record:                  # null if skipped/opted-out
  id: <id>
  dest: <absolute path>
  templateVersion: <OMR_VERSION>      # always equal to the omr plugin version at install
  action: CREATE_NEW | ALREADY_PRISTINE | OVERWROTE | SAVED_ALONGSIDE | KEPT_MINE
  backedUpTo: <path-or-null>
```

Phase 6 appends this to a `hpcConfigs` array in `.omr-config.json`,
deduping by `dest`.

### 5.8 Tell the user what to do next

Print a short next-steps block:

> Next:
> 1. Open `<destination>` and fill in the `<...>` placeholders.
> 2. From any shell, verify access with: `ssh <user>@<hostname>`.
> 3. Future omr skills that need cluster info will read this file from
>    `./.omr/hpc/`. Set `hpc.default_cluster` in `./.omr/config.yaml` to
>    make this cluster the project default.

Do **not** run `ssh` from this skill. Interactive 2FA / password prompts
would block the session.

## Handoff

> Phase 5 done — HPC config recorded. Moving to verify.

Pass `hpc_phase` and `hpc_record` to Phase 6.
