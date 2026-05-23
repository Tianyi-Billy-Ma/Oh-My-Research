# Phase 2 — Audit

**Goal:** for each server discovered in Phase 1, determine whether its token
is reachable, and from where. Output is a status table the user can act on.
Read-only — no filesystem writes, no secret echoing.

## Steps

### 2.1 Probe shell env

For each server's env var, check whether the launching shell exported it.
Use a presence probe — never echo the value:

```bash
[ -n "${VAR_NAME:-}" ] && echo "set" || echo "unset"
```

Run all probes in one Bash call where possible (parallel-friendly). Record
the result per server.

### 2.2 Probe project-local `.env`

If a server's env var is `unset` in shell **and** the server's transport is
`stdio` (`.env` is irrelevant for HTTP — see safety rails), check
`./.env` (project root, i.e. current working directory):

1. If `./.env` does not exist, mark source as `none`.
2. If it exists, parse `KEY=VALUE` pairs. Treat the var as **set via `.env`**
   only when the line exists AND the value (after stripping surrounding
   quotes/whitespace) is non-empty. Lines like `EXA_API_KEY=` count as
   unset.
3. Do not display the value, the matched line, or any other file contents.
   You may report the line number if useful for the remediation phase, but
   nothing more.

For HTTP servers, skip the `.env` probe entirely. Their source is either
`shell` or `none` — never `.env`.

### 2.3 Print the status table

Render exactly one table. Columns and example:

```
Server         Transport  Token                              Source   Status
exa            stdio      EXA_API_KEY                        shell    ✓ set
tavily         stdio      TAVILY_API_KEY                     .env     ✓ set
brave-search   stdio      BRAVE_API_KEY                      —        ✗ missing
github         http       GITHUB_PERSONAL_ACCESS_TOKEN       shell    ✓ set
huggingface    http       HF_TOKEN                           —        ✗ missing  (HTTP — .env won't help)
```

Rules for the table:

- `Source` is `shell`, `.env`, or `—` (em dash) for missing.
- `Status` is `✓ set` or `✗ missing`. Nothing else.
- For HTTP rows with `✗ missing`, append `(HTTP — .env won't help)` so the
  user understands why `.env` isn't a fix. Don't repeat this on stdio rows.
- If `env_var` was `UNKNOWN` from Phase 1, render the Token column as the
  literal string `UNKNOWN` and the Status as `✗ unmappable`; surface it
  separately in Phase 3 so the user can file an issue.
- No values, no lengths, no partial reveals. The table is a presence
  audit, not a diagnostic dump.

### 2.4 Summarize gaps

Right after the table, print a one-line summary:

> N of 5 servers reachable. Missing: brave-search (stdio), huggingface (HTTP).

If everything is set:

> All 5 servers have tokens. Skipping remediation; proceed to verify.

## Branch on `--audit` / `--check`

If the user invoked the skill with `--audit` or `--check`, stop here. Echo:

> Audit-only mode — stopping before remediation. Rerun without `--audit` to
> apply fixes.

Otherwise continue to Phase 3.

## Handoff

> Phase 2 done — audit complete. Moving to remediation.

Pass the per-server status records (with source and missing flag) to Phase 3.
