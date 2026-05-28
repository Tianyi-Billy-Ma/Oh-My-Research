# Phase 4 — Remediate

**Goal:** close the gaps Phase 2 found, scoped to the flag the user picked.
The only filesystem write this phase performs is `cp .env.example .env`, and
only with explicit consent.

This phase respects two flags from SKILL.md:

- `scope=local` → only act on project-local `.env`. List HTTP gaps but do
  not emit `export` advice.
- `scope=global` → only act on shell exports. Skip `.env` scaffolding even if
  stdio tokens are missing.
- `scope=all` (default, no flag) → handle both.

## Steps

### 4.1 Short-circuit if nothing to do

If Phase 2 reported zero missing tokens, skip to Phase 5. Echo:

> Nothing to remediate. Moving to verify.

### 4.2 Split missing tokens by transport

Build two lists from Phase 2's status records:

- `stdio_missing`: stdio servers with no token reachable.
- `http_missing`: http servers with no token reachable.

### 4.3 Remediate stdio gaps

**Skip this entire section if `scope=global`.** Echo:

> Scope `--global` — skipping project-local `.env` remediation. Stdio gaps
> deferred to a `--local` (or default) run.

If `stdio_missing` is empty, skip to 4.4.

Check whether `./.env` exists.

**Case A — no `.env` present:**

Use AskUserQuestion (single-select) to ask:

> No `.env` in the current project. Want me to copy `.env.example` to `.env`
> so you can fill in the missing keys?

Options:
1. **Yes, scaffold `.env`** — runs `cp "${CLAUDE_PLUGIN_ROOT}/.env.example" ./.env`.
2. **No, I'll handle it manually** — skip the copy.

If yes:

1. Run `cp "${CLAUDE_PLUGIN_ROOT}/.env.example" ./.env`. Do NOT `chmod`,
   do NOT seed values, do NOT open it.
2. Confirm the file was created.
3. Print which keys to fill in (the env vars from `stdio_missing`) and the
   canonical URL for each. Pull URLs from the README's "Bundled MCPs" /
   "Configuring tokens" section — don't hardcode them here.

**Case B — `.env` exists:**

Don't copy over it. Tell the user which keys are still empty in the
existing `.env` (by env var name, no values) and link to the doc URLs from
the README. Example output:

> `.env` already exists. The following stdio keys are still empty there;
> please open `.env` and fill them in:
> - `BRAVE_API_KEY` — https://api.search.brave.com/app/keys

Do NOT cat, sed, or otherwise modify `.env`.

### 4.4 Remediate HTTP gaps

**Skip this entire section if `scope=local`.** Echo:

> Scope `--local` — skipping shell-export remediation. HTTP gaps deferred
> to a `--global` (or default) run.

If `http_missing` is empty, skip to 4.5.

HTTP servers need shell-exported tokens. Print the exact `export` lines the
user should add to their shell profile (`~/.zshrc`, `~/.bashrc`, or
equivalent). Pull env var names from `http_missing`. Example:

> HTTP MCPs (`github`, `huggingface`) read their tokens from the shell at
> launch — `.env` is not consulted. Add these to your shell profile and
> open a new terminal (or `source` the profile) before relaunching
> `claude`:
>
> ```bash
> export GITHUB_PERSONAL_ACCESS_TOKEN=...
> export HF_TOKEN=...
> ```
>
> Alternative: use `direnv` (`.envrc` with `export` lines) for
> project-scoped tokens — it exports before `claude` starts and avoids
> polluting your global shell.

Include the canonical URL for each missing HTTP token, again sourced from
the README.

### 4.5 Surface unmappable servers

If Phase 1 emitted any `UNKNOWN` env vars, tell the user:

> Couldn't determine the env var for: `<server-name>`. This is likely a bug
> in `/omr:setup` — please open an issue at
> https://github.com/Tianyi-Billy-Ma/Oh-My-Research/issues with the
> contents of `.mcp.json`.

Don't try to guess.

### 4.6 Summary

Print one-line summary of what changed:

- `.env` scaffolded? Yes/no, path.
- HTTP exports user still needs to add? List env var names (no values).
- Scope flag applied? Mention it so deferred work is visible.

## Handoff

> Phase 4 done — remediation complete. Moving to verify.
