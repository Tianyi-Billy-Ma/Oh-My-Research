# Phase 4 — Verify

**Goal:** explain how the user actually picks up the new state and close the
loop. No probing, no MCP calls — this is guidance only, kept separate from
Phase 2's audit so the user can re-audit on demand without re-reading the
verify instructions.

## Steps

### 4.1 Reload guidance

Tailor the advice to what changed in Phase 3:

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

- **Nothing changed (audit-only path that somehow reached this phase):**
  Just point at `/mcp` for live status. Don't suggest a restart.

### 4.2 Smoke check pointer

Tell the user how to confirm each server is reachable:

> Run `/mcp` and look for each of the five servers under "Connected". If
> any show as disconnected after a reload, rerun `/omr:setup --audit` to
> re-check tokens, then inspect that server's logs via `/mcp` for the
> underlying error.

Do **not** call an MCP tool from this skill as a smoke test. It burns the
user's API quota and adds nothing the `/mcp` status panel doesn't already
show.

### 4.3 Wrap-up summary

Print a final block with three sections, populated from Phase 2 + Phase 3
state:

```
✓ Reachable now:    exa, tavily, github
↻ Pending user:     brave-search (edit ./.env), huggingface (shell export)
✗ Unmappable:       (none)
```

Empty sections can be elided. Don't add anything after this block; the
skill is done.

### 4.4 Pointer for repeat runs

End with one line:

> Rerun `/omr:setup --audit` anytime to re-check token status without
> touching files.

## Handoff

This is the terminal phase. Echo:

> omr:setup complete.

…and stop.
