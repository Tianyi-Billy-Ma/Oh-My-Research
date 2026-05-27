# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`Oh-My-Research` is a **Claude Code plugin** (not an application). It packages research-oriented skills, agents, and hooks that get loaded into Claude Code via the plugin system. The goal is an "autoresearch / viberesearch" suite — automating literature survey, idea generation, experiment loops, paper writing, and review — similar in spirit to:

- `wanshuiyin/Auto-claude-code-research-in-sleep`
- `LigphiDonk/Oh-my--paper`
- `uditgoenka/autoresearch`

Current surface area: a plugin manifest (`name: "omr"`), an `.mcp.json` declaring five MCP servers (Exa, Tavily, Brave, GitHub, Hugging Face), a `bin/load-env-and-exec.sh` shim for stdio env resolution, and one skill (`skills/setup/`). There is **no build, test, or lint pipeline** because there is no application code — do not invent one. New work means authoring plugin components (skills, agents, hooks) and bumping `plugin.json` version, not editing source.

## Naming convention (REQUIRED)

The plugin is published with `name: "omr"` in `plugin.json` — that field IS the slash-command namespace. The full name "Oh-My-Research" lives only in the description; `omr` is the shorthand everywhere else.

Skills MUST follow this scheme:

- Folder: `skills/<skill-name>/SKILL.md` (no `omr-` prefix on the folder; the namespace comes from the plugin).
- Invoked as: `/omr:<skill-name>` (e.g. `/omr:setup`).
- The `description:` field in SKILL.md frontmatter should include the keyword trigger `omr-<skill-name>` (hyphenated form) so users typing it in plain chat auto-trigger the skill. Also include `omr:<skill-name>` and a natural-language phrasing.
- Do not invent alternative namespaces (`oh-my-research:<skill>`, `research:<skill>`). They will not resolve.

Bias toward over-listing triggers in descriptions — false positives are cheap, false negatives are invisible to the user.

## Skill structure: thin router + phases

Any skill whose flow takes more than ~30 lines of instructions MUST split into a thin `SKILL.md` router plus a `phases/` directory:

```
skills/<skill-name>/
├── SKILL.md                    # router: frontmatter, flag parsing, help text, pre-check, safety rails, phase index
└── phases/
    ├── 01-<verb>.md            # one phase per file, numbered
    ├── 02-<verb>.md
    └── ...
```

Rules:

- `SKILL.md` lists phases by absolute path (`${CLAUDE_PLUGIN_ROOT}/skills/<name>/phases/NN-*.md`) and tells the agent to read each in order. Don't inline phase logic. Keep `SKILL.md` to routing concerns: frontmatter, flag parsing, help text, pre-check / already-configured handling, cross-phase safety rails, and the phase index. Routing legitimately runs ~150–200 lines for non-trivial skills; that's fine, but any step-by-step procedure belongs in a phase.
- Each phase file has a goal, numbered steps, and a one-line **Handoff** at the end that the agent echoes before moving on. This makes interrupted runs resumable and traceable.
- Cross-phase invariants (safety rails, "never echo secrets", scope guards) belong in `SKILL.md`, not duplicated across phases.
- Lookup tables, schemas, and provider-specific quirks belong in the phase that needs them — keep phases self-contained so a future contributor can refactor one without re-reading the whole skill.
- Number prefix (`01-`, `02-`) defines execution order. Use 10-step increments only if you genuinely expect to insert phases later; otherwise keep them tight.

Reference shape: `omc-setup` from oh-my-claudecode. Our `setup` skill follows this layout — copy it when authoring new multi-step skills.

## Skill convention: ask the user, don't prompt-and-wait

Every user-facing question that a skill asks — consent prompts, scope choices, conflict resolutions, branch decisions — MUST go through the built-in `AskUserQuestion` tool with explicit options. Never write a plain-text question into the chat and wait for a free-form reply.

Why: free-form chat replies depend on Claude's interpretation of intent, which is fragile across runs and frustrating to debug. `AskUserQuestion` makes the decision space explicit, deterministic, and reviewable. The tool also surfaces a structured UI for the user, which is a much better experience than parsing prose.

When writing a phase that needs user input, the instruction should literally say "Use AskUserQuestion" and list the option labels you expect. If you find yourself drafting prose like "Ask the user whether…", treat that as a bug and switch to `AskUserQuestion`.

## Skill convention: writing into user files (CLAUDE.md, settings.json, etc.)

When a skill needs to inject plugin content into a user-owned file:

- **Use a versioned marker block.** Wrap the content in HTML comments like
  `<!-- BEGIN omr version="X.Y.Z" -->` and `<!-- END omr -->`. The version tag
  lets the next run detect whether a refresh is needed.
- **Insert-block only, never full-overwrite.** Preserve everything outside
  the markers. Users have their own content; the plugin only owns its block.
- **Idempotent at the same version.** If the block is already installed at
  the current plugin version, skip the write with a one-line confirmation.
- **Backup before refresh.** Take a backup to `<file>.backup.YYYY-MM-DD`
  before any write. One backup per file per day — don't pile up.
- **Stop on malformed state.** If the markers are unbalanced or nested, do
  not try to repair. Stop and ask the user.

The canonical content for each marker block lives under `templates/` (e.g.
`templates/CLAUDE.md.partial`), versioned alongside the rest of the plugin.
Bump `plugin.json` version whenever a template's content changes — that's the
signal for installed instances to refresh on next setup run.

## Skill convention: per-resource YAML templates (`templates/<name>.yaml`)

For resources that are pure config (not docs), ship a YAML template at
`templates/<resource>.yaml` and have a setup phase copy it to a user-chosen
destination on consent. Pattern conventions:

- **Template content is universal.** No personal infra, no site-specific
  defaults. Every concrete value is a `<placeholder>` the user fills in.
- **`template_version` field at the top** lets future setup runs diff the
  installed copy against the shipped one. Bump the field whenever the
  template's schema or comments meaningfully change.
- **Comments carry the docs.** A YAML block at the bottom (between two
  `# ---` rulers) serves as quick-reference text — readable in any editor,
  invisible to parsers.
- **Scope-aware destination.** Install to `~/.claude/<resource>/<id>.yaml`
  (global) or `./.omr/<resource>/<id>.yaml` (project-local). Future skills
  that read these resolve project-local first, then user-global — same
  precedence as `.env`.
- **Refresh policy is diff-check.** If the installed file matches the
  shipped template byte-for-byte, treat as `ALREADY_PRISTINE`. If it
  differs, AskUserQuestion: keep mine / overwrite / save alongside as
  `<id>.new.yaml`. One backup per file per day before any overwrite.
- **Never touch system config.** A YAML template never modifies
  `~/.ssh/config`, `/etc/hosts`, or anything else outside its own
  destination tree. The setup phase that installs it also never runs
  authentication commands (`ssh-keygen`, `ssh-copy-id`, etc.) on the user's
  behalf.

Current example: `templates/hpc.yaml` (installed by Phase 5 of `omr:setup`).

## Plugin layout contract

Follow the official Claude Code plugin template exactly — the README pins this and the loader depends on it:

```
Oh-My-Research/
├── .claude-plugin/
│   └── plugin.json          # ONLY file under .claude-plugin/
├── .mcp.json                # MCP server declarations loaded by the plugin
├── bin/                     # plugin-internal scripts (e.g. env loader shim)
├── templates/               # canonical content injected into user files (e.g. CLAUDE.md.partial, hpc.yaml)
├── skills/                  # one folder per skill, each containing SKILL.md
│   └── <skill-name>/SKILL.md
├── agents/                  # optional: <name>.md agent definitions
├── hooks/                   # optional: hooks.json
└── commands/                # optional: slash-command markdown files
```

Hard rules:
- Only `plugin.json` belongs inside `.claude-plugin/`. Everything else (skills, agents, hooks, commands) lives at the **plugin root**, not nested under `.claude-plugin/`.
- Each skill is a directory under `skills/` with a `SKILL.md` entry point; supporting scripts/templates go alongside it in the same directory.
- When adding a skill or agent, also bump `version` in `.claude-plugin/plugin.json` so installations refresh.

## Installing locally for testing

```bash
claude --plugin-dir /Users/billyma/Workspace/Oh-My-Research
```

This loads the plugin into a Claude Code session without publishing to a marketplace. Use it to verify skills surface under `/<plugin>:<skill>` before committing.

## Authoring notes

- This plugin is intended to compose with the user's existing `oh-my-claudecode` and `claude-mem` plugins (already installed globally). Don't duplicate skills that those provide (e.g., `autopilot`, `ralph`, `ultrawork`, `make-plan`); instead, add research-domain capabilities that *call* them when appropriate.
- The workspace also hosts `omp:*` and `billyverse:*` skills geared at academic research (literature search, paper writing, experiment dispatch). Before adding a skill here, check whether one of those already covers the workflow — this plugin should add what's missing, not re-implement.
- Inspiration repos above are good references for shape (skill names, prompt structure, loop semantics) but their code is not vendored here; consult them externally when designing a new workflow.

## MCP servers (`.mcp.json`)

Five MCPs ship at the root, split by transport:

**Stdio (launched via the env-loader shim):**
- `exa` → `npx -y exa-mcp-server` (env: `EXA_API_KEY`)
- `tavily` → `npx -y tavily-mcp` (env: `TAVILY_API_KEY`)
- `brave-search` → `npx -y @brave/brave-search-mcp-server` (env: `BRAVE_API_KEY`, stdio is default in 2.x)

**HTTP (vendor-hosted, Streamable HTTP transport):**
- `github` → `https://api.githubcopilot.com/mcp/` (header: `Authorization: Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}`)
- `huggingface` → `https://huggingface.co/mcp` (header: `Authorization: Bearer ${HF_TOKEN}`)

### Stdio: the env-loader shim

All stdio servers are launched through `${CLAUDE_PLUGIN_ROOT}/bin/load-env-and-exec.sh`, which:

1. Reads `$PWD/.env` if it exists.
2. Exports any `KEY=VALUE` pairs that are **not already set** in the inherited environment (so shell exports win over `.env`).
3. `exec`s the actual MCP server command.

When adding a new stdio MCP that needs API keys, reuse this shim — don't bypass it. Append another entry to `.mcp.json` with the same `command` and the new server's `npx` (or other launcher) invocation in `args`. The shim is intentionally provider-agnostic and handles quoted values, `export`-prefixed lines, comments, and malformed lines.

### HTTP: shell env only

Claude Code expands `${VAR}` in HTTP `headers` against its own `process.env` at startup, which is inherited from the launching shell. The loader shim never runs for HTTP servers because there is no subprocess to wrap. That means **`.env` fallback does not apply to HTTP MCPs** — tokens must be exported in the user's shell profile (or via a tool like `direnv` that exports before `claude` launches). Document this limitation when adding any new HTTP MCP, and prefer `${VAR}`-style references over hard-coded tokens.

If a vendor's HTTP MCP supports a stdio mode (e.g., a Docker image or local binary), wrapping that path through the shim is preferable when `.env` fallback matters — but accept the trade-off of an extra dependency.

### Versioning

Anything that touches MCP wiring (new server, env var rename, shim change, transport switch) is user-visible and should bump the `version` in `.claude-plugin/plugin.json`.

## Repository-specific conventions

- `.omc/` is git-ignored and holds local OMC runtime state (sessions, project memory, HUD cache) — never commit it.
- `.env` is git-ignored; only `.env.example` is checked in. Never put real keys in the example.
- The repo lives at `github.com/Tianyi-Billy-Ma/Oh-My-Research`; the **plugin name** in `plugin.json` is `omr` (the namespace), not `oh-my-research`. Don't conflate the repo name with the plugin name.
