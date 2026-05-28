# Phase 6 — Verify

**Goal:** explain how the user picks up the new state, persist the
"configured" marker so subsequent runs can short-circuit, and close the loop.
No probing, no MCP calls — guidance + bookkeeping only.

## Steps

### 6.1 Reload guidance

Tailor the advice to what Phase 3 (CLAUDE.md install), Phase 4
(remediation), and Phase 5 (HPC config) actually did:

- **`.env` was created or already existed and the user just edited it
  (stdio servers):**
  The env-loader shim re-reads `.env` every time an MCP server is launched.
  In Claude Code, run `/mcp` to inspect server state; reconnect any server
  that's currently disconnected, or restart the session to be safe.

- **Shell `export`s were added (HTTP servers):**
  Claude Code reads `process.env` only at startup. The new keys won't apply
  until the user either opens a new terminal that has the exports
  available, or runs `source ~/.zshrc` (or equivalent) and then relaunches
  `claude`. A `/mcp` reconnect inside an already-running session will not
  pick up the new env.

- **CLAUDE.md was installed or refreshed (Phase 3):**
  The new instructions take effect on the next Claude Code session in that
  scope. Project-level (`./.claude/CLAUDE.md`) applies on next `claude`
  launch in that directory; global (`~/.claude/CLAUDE.md`) applies on
  every new session. No reload trick exists for the currently-running
  session — restart to pick up.

- **HPC config was written or refreshed (Phase 5):**
  The YAML file is config-only — nothing runs until the user (or a future
  omr skill) reads it. Remind the user to open the file and replace the
  `<...>` placeholders. No restart needed.

- **Audit-only run or nothing changed:**
  Just point at `/mcp` for live status. Don't suggest a restart.

If a scope flag was set, mention what was deferred so the user knows the
state is partial:

> Scope `--local` ran — HTTP gaps (if any) and global CLAUDE.md install
> remain. Rerun `/omr:setup --global` when you're ready.

### 6.2 Persist the configured marker

**Skip this step entirely if `audit_only` is true** — audit runs are
read-only by contract.

Path:

```bash
CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
CONFIG_FILE="$CONFIG_DIR/.omr-config.json"
```

Write a JSON blob with these fields:

- `setupCompleted`: ISO-8601 timestamp of *this* completion (current time).
- `setupVersion`: the omr plugin version (read from
  `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` → `.version`).
- `lastAuditAt`: same as `setupCompleted` on a remediation run.
- `lastScope`: `local`, `global`, or `all`.
- `tokensReachableAtSetup`: per-server bool map — true when Phase 2 said
  `✓ set`. Do NOT include the token values; the names are the keys.
- `claudeMdTargets`: list of CLAUDE.md paths Phase 3 actually wrote to
  (empty list if Phase 3 was skipped or all targets were
  `ALREADY_INSTALLED`).
- `hpcConfigs`: append-only list of HPC config records. Each entry:
  `{id, dest, templateVersion, installedAt, lastAction}`. Dedupe by
  `dest` — if a record with the same dest exists, overwrite it. Skip if
  Phase 5 was opted-out or skipped.
- `hpcSetupOptOut`: bool, set when the user picks `Never` in Phase 5.
  Preserve across runs.

Procedure:

1. `mkdir -p "$CONFIG_DIR"` (idempotent).
2. If the file exists, read it with `jq` to preserve unknown fields:
   ```bash
   jq --argjson new "$NEW_OBJ" '. + $new' "$CONFIG_FILE" > "$CONFIG_FILE.tmp"
   mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
   ```
   If `jq` isn't available, fall back to overwriting with the new object —
   our schema is small and we don't promise to merge.
3. If the file doesn't exist, write the new object directly.

The marker is **global** (per Claude Code config dir), not per-project — it
records that the user has been through this flow at least once. Per-project
state is encoded by the presence/contents of `./.env`,
`./.claude/CLAUDE.md`, and `./.omr/hpc/*.yaml` themselves.

### 6.3 Audit-only marker update

If `audit_only` is true and `.omr-config.json` already exists, update only
`lastAuditAt` to the current ISO timestamp (preserving every other field).
If it doesn't exist, do nothing — audit alone isn't enough to claim setup.

### 6.4 Smoke check pointer

> Run `/mcp` and look for each of the five servers under "Connected". If
> any show as disconnected after a reload, rerun `/omr:setup --audit` to
> re-check tokens, then inspect that server's logs via `/mcp` for the
> underlying error.

Do **not** call an MCP tool from this skill as a smoke test.

### 6.5 Wrap-up summary

Print a final block populated from Phase 2, 3, 4, and 5 state:

```
✓ Reachable now:    exa, tavily, github
↻ Pending user:     brave-search (edit ./.env), huggingface (shell export)
✗ Unmappable:       (none)
CLAUDE.md:          ~/.claude/CLAUDE.md (REFRESH v0.6.0 → v0.7.0)
HPC config:         ~/.claude/hpc/acme-slurm.yaml (CREATE_NEW)
Scope:              all
Marker written:     ~/.claude/.omr-config.json
```

Empty sections can be elided. The `Marker written` line is omitted on
audit-only runs. If Phase 5 was skipped or opted-out, render the `HPC
config` line as `skipped` or `opted out (hpcSetupOptOut: true)`.

### 6.6 Pointer for repeat runs

End with one line:

> Rerun `/omr:setup --audit` anytime to re-check token status without
> touching files. Rerun `/omr:setup --force` to redo the full wizard.

## Handoff

This is the terminal phase. Echo:

> omr:setup complete.

…and stop.
