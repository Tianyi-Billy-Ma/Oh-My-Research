---
id: doctor
name: doctor
version: 0.11.0
description: |-
  Diagnose Oh-My-Research (omr) installation, configuration, and connectivity issues.
stages: ["setup"]
tools: ["Bash", "Read"]
summary: |-
  Read-only health check for omr. Verifies plugin integrity, MCP wiring, CLAUDE.md install state, token presence, HPC config drift, and external dependencies. Points at /omr:setup for any fix — never writes or mutates state itself.
primaryIntent: setup
intents: ["setup", "diagnostics"]
capabilities: ["tooling"]
domains: ["general"]
keywords: ["omr-doctor", "omr:doctor", "doctor omr", "check omr", "diagnose omr", "omr health", "omr broken", "what's wrong with omr", "omr troubleshoot"]
source: builtin
status: experimental
resourceFlags:
  hasReferences: false
  hasScripts: false
  hasTemplates: false
  hasAssets: false
  referenceCount: 0
  scriptCount: 0
  templateCount: 0
  assetCount: 0
---

# omr:doctor

Diagnose omr installation issues. Read-only — emits `CRITICAL` / `WARN` /
`OK` per check, then prints a summary that points at `/omr:setup` for any
needed fix.

**When this skill is invoked, immediately execute the workflow below. Do
not just restate or summarize these instructions back to the user.**

Note: paths under `~/.claude/...` respect `CLAUDE_CONFIG_DIR` when set.

## Invariants

1. **Read-only.** Never writes a file, never runs setup, never touches
   `.env`, CLAUDE.md, `.omr-config.json`, or HPC configs. If a fix is
   needed, point at `/omr:setup` with the appropriate flag.
2. **Never echoes secrets.** Token probes report presence/source only —
   same rules as `/omr:setup` Phase 2.
3. **Cross-platform commands.** Prefer constructs that work in bash 3.2
   (macOS default) — no associative arrays, no `mapfile`. Use POSIX
   utilities where possible.
4. **Aggregate at the end.** Track each step's verdict so the final
   summary lists exactly what failed and how to fix it.

## Diagnostic steps

Run each step in order. After each step, record one of `OK` / `WARN` /
`CRITICAL` plus a one-line reason. Don't print the verdicts inline —
collect them, then emit the summary in the last section.

### Step 1 — Plugin integrity

Verify the plugin's own manifest and required files are present.

```bash
# Plugin manifest
jq -r '.name + " v" + .version' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null \
  || echo "MISSING: ${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json"

# Required files
for f in .mcp.json bin/load-env-and-exec.sh skills/setup/SKILL.md; do
  if [ -e "${CLAUDE_PLUGIN_ROOT}/$f" ]; then
    echo "FOUND: $f"
  else
    echo "MISSING: $f"
  fi
done

# Shim is executable
if [ -x "${CLAUDE_PLUGIN_ROOT}/bin/load-env-and-exec.sh" ]; then
  echo "SHIM: executable"
else
  echo "SHIM: not executable"
fi
```

**Diagnosis:**
- Any `MISSING:` line → `CRITICAL` (install broken; recommend reinstalling
  the plugin).
- Plugin `name` from manifest ≠ `omr` → `CRITICAL` (wrong plugin or
  tampered manifest).
- Shim not executable → `WARN` (stdio MCPs will fail to launch; user can
  `chmod +x` to fix manually).
- Else → `OK`.

### Step 2 — MCP server declarations

Confirm `.mcp.json` declares all expected servers.

```bash
jq -r '.mcpServers | keys[]' "${CLAUDE_PLUGIN_ROOT}/.mcp.json" 2>/dev/null | sort
```

**Diagnosis:**
- Output missing any of `brave-search`, `exa`, `github`, `huggingface`,
  `tavily` → `WARN` (one or more servers no longer declared; reinstall
  the plugin).
- All five present → `OK`.

### Step 3 — CLAUDE.md install state

Check whether the omr marker block is installed in either the global or
project CLAUDE.md, and whether its version matches the plugin.

```bash
PLUGIN_V=$(jq -r '.version' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json")
echo "plugin version: $PLUGIN_V"

for path in "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/CLAUDE.md" "./.claude/CLAUDE.md"; do
  if [ -f "$path" ]; then
    INSTALLED_V=$(grep -oE 'BEGIN omr version="[^"]+"' "$path" 2>/dev/null \
      | head -1 | sed -E 's/.*version="([^"]+)"/\1/')
    if [ -n "$INSTALLED_V" ]; then
      echo "$path: omr v$INSTALLED_V"
    else
      echo "$path: no omr block"
    fi
  else
    echo "$path: (file does not exist)"
  fi
done
```

**Diagnosis:**
- At least one target has `omr v<X>` matching `PLUGIN_V` → `OK`.
- Any target has `omr v<X>` ≠ `PLUGIN_V` → `WARN` per target (CLAUDE.md
  drift; run `/omr:setup --global` or `--local` to refresh).
- Both targets are `no omr block` or `(file does not exist)` → `WARN`
  (plugin known but never registered; run `/omr:setup`).

### Step 4 — MCP token presence

Probe each server's expected env var. Presence-only — never echo values.

```bash
for pair in \
    "EXA_API_KEY:exa:stdio" \
    "TAVILY_API_KEY:tavily:stdio" \
    "BRAVE_API_KEY:brave-search:stdio" \
    "GITHUB_PERSONAL_ACCESS_TOKEN:github:http" \
    "HF_TOKEN:huggingface:http"; do
  v="${pair%%:*}"
  rest="${pair#*:}"
  server="${rest%%:*}"
  transport="${rest#*:}"
  if [ -n "$(printenv "$v")" ]; then
    echo "$server: $v set in shell"
  elif [ -f "./.env" ] && grep -E "^${v}=." ./.env >/dev/null 2>&1; then
    if [ "$transport" = "http" ]; then
      echo "$server: $v in .env (HTTP — not read at runtime; export in shell)"
    else
      echo "$server: $v set in .env"
    fi
  else
    echo "$server: $v missing"
  fi
done
```

**Diagnosis:**
- All servers `set in shell` (or stdio servers `set in .env`) → `OK`.
- Any stdio server `missing` → `WARN` (run `/omr:setup --audit` for a full
  status report, then `/omr:setup` to scaffold `.env` if needed).
- Any HTTP server `missing` or only-in-`.env` → `WARN` (HTTP MCPs need
  shell-exported tokens; `.env` is invisible to them).

### Step 5 — HPC config drift (optional)

If `./.omr/hpc/` contains any `*.yaml` files, check each against the
current plugin version. (HPC configs are always project-local — there is
no `~/.claude/hpc/`.)

```bash
PLUGIN_V=$(jq -r '.version' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json")
found_any=0
for dir in "./.omr/hpc"; do
  [ -d "$dir" ] || continue
  for f in "$dir"/*.yaml; do
    [ -f "$f" ] || continue
    found_any=1
    INSTALLED_V=$(awk '/^template_version:/{print $2; exit}' "$f")
    if [ "$INSTALLED_V" = "$PLUGIN_V" ]; then
      echo "$f: template_version $INSTALLED_V (aligned)"
    else
      echo "$f: template_version $INSTALLED_V (plugin is $PLUGIN_V — drift)"
    fi
  done
done
if [ "$found_any" = "0" ]; then
  echo "no HPC configs installed (skip)"
fi
```

**Diagnosis:**
- `no HPC configs installed` → `OK` (nothing to check).
- All `aligned` → `OK`.
- Any `drift` line → `WARN` per file (rerun `/omr:setup` to refresh).

### Step 6 — Config marker sanity

Read `.omr-config.json` and validate it.

```bash
PLUGIN_V=$(jq -r '.version' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json")
CFG="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/.omr-config.json"
if [ -f "$CFG" ]; then
  if jq -e '.setupCompleted, .setupVersion' "$CFG" >/dev/null 2>&1; then
    INSTALLED_V=$(jq -r '.setupVersion' "$CFG")
    if [ "$INSTALLED_V" = "$PLUGIN_V" ]; then
      echo "config: ok (setupVersion $INSTALLED_V, aligned)"
    else
      echo "config: ok (setupVersion $INSTALLED_V, plugin is $PLUGIN_V — drift)"
    fi
  else
    echo "config: malformed (missing setupCompleted or setupVersion)"
  fi
else
  echo "config: not present (setup never completed?)"
fi
```

**Diagnosis:**
- `aligned` → `OK`.
- `drift` → `WARN` (run `/omr:setup` to refresh the marker).
- `malformed` → `WARN` (manual edit broke it; run `/omr:setup --force`).
- `not present` → `WARN` if Step 3 found an omr block (setup was
  partially done and the marker got removed) or if any other signal
  suggests setup ran; else `OK` (fresh install, expected before first
  setup run).

### Step 7 — External dependencies

```bash
for cmd in jq node npx; do
  if command -v "$cmd" >/dev/null 2>&1; then
    ver=$("$cmd" --version 2>&1 | head -1)
    echo "$cmd: $(command -v "$cmd") ($ver)"
  else
    echo "$cmd: MISSING"
  fi
done
```

**Diagnosis:**
- All three present → `OK`.
- `jq` missing → `WARN` (config-marker writes degrade to overwrite; Phase
  3's CLAUDE.md install loses some features).
- `node` or `npx` missing → `CRITICAL` (stdio MCPs cannot launch at all).

## Summary

After all steps, print exactly one block:

```
omr:doctor — health report

  ✓ OK        <count>
  ⚠ WARN      <count>
  ✗ CRITICAL  <count>

Findings:
  ⚠ <one-line description> — fix: <command or action>
  ✗ <one-line description> — fix: <command or action>
  ...

Next moves: <single-line suggestion based on highest-severity finding>
```

If every step is `OK`:

```
omr:doctor — all checks passed.
```

End there. Do not run any fix on the user's behalf. Do not ask follow-up
questions. The user decides whether to run `/omr:setup`.
