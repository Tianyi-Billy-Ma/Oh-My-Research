# Oh-My-Research (`omr`)

Research workflows and skills for Claude Code. The plugin's namespace is
`omr`, so every bundled skill is invoked as `/omr:<skill-name>`.

## Install

```bash
claude --plugin-dir /path/to/Oh-My-Research
```

For persistent installation via a marketplace, see the Claude Code plugin docs at https://code.claude.com/docs/en/plugins.

## Bundled MCPs

The plugin ships an `.mcp.json` declaring five MCP servers, loaded
automatically when the plugin is enabled:

| Server | Transport | Source | Env var |
| --- | --- | --- | --- |
| Exa | stdio | `exa-mcp-server` (npx) | `EXA_API_KEY` |
| Tavily | stdio | `tavily-mcp` (npx) | `TAVILY_API_KEY` |
| Brave Search | stdio | `@brave/brave-search-mcp-server` (npx) | `BRAVE_API_KEY` |
| GitHub | http | `https://api.githubcopilot.com/mcp/` | `GITHUB_PERSONAL_ACCESS_TOKEN` |
| Hugging Face | http | `https://huggingface.co/mcp` | `HF_TOKEN` |

Stdio servers are fetched on first use by `npx`; HTTP servers are hosted by the
vendor and need only a token.

### Configuring tokens

Two layers, with shell environment always winning:

1. **Shell profile** (preferred — required for the HTTP servers) — export in
   `~/.zshrc` / `~/.bashrc`:
   ```bash
   export EXA_API_KEY=...
   export TAVILY_API_KEY=...
   export BRAVE_API_KEY=...
   export GITHUB_PERSONAL_ACCESS_TOKEN=...
   export HF_TOKEN=...
   ```
2. **Project-local `.env`** (stdio servers only) — copy `.env.example` to
   `.env` in the directory where you launch Claude Code. The loader shim picks
   up any keys not already set in your shell. The two HTTP MCPs (`github`,
   `huggingface`) cannot read `.env` because Claude Code expands their
   `Authorization` header from its own process env at startup; for those, use
   shell env or a tool like `direnv` that exports before launch.

Token sources:
- Exa <https://dashboard.exa.ai/api-keys>
- Tavily <https://app.tavily.com/home>
- Brave <https://api.search.brave.com/app/keys>
- GitHub PAT <https://github.com/settings/personal-access-tokens/new> — grant only the scopes you want the MCP to use
- Hugging Face <https://huggingface.co/settings/tokens>

Missing a token only disables that one server; the others still work. Confirm
servers are up via `/mcp` inside Claude Code — each should show as connected
with its tools listed.

## Skills

| Slash command | Keyword trigger | What it does |
| --- | --- | --- |
| `/omr:setup` | `omr-setup` | Audit MCP tokens, scaffold `.env`, point at remediation steps without ever printing secrets. |

More skills land here as they're added; all follow the `/omr:<name>`
convention.

## Layout

```
Oh-My-Research/
├── .claude-plugin/
│   └── plugin.json
├── .mcp.json           # search MCP server declarations
├── bin/                # plugin-internal scripts (env loader, etc.)
├── skills/             # add <name>/SKILL.md folders here
├── agents/             # optional agent definitions
├── hooks/              # optional hooks.json
└── README.md
```

Only `plugin.json` lives inside `.claude-plugin/`. All component directories
(skills, agents, hooks, etc.) sit at the plugin root.

## License

MIT
