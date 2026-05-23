# Oh-My-Research

Research workflows and skills for Claude Code.

## Install

```bash
claude --plugin-dir /path/to/Oh-My-Research
```

For persistent installation via a marketplace, see the Claude Code plugin docs at https://code.claude.com/docs/en/plugins.

## Search MCPs

The plugin ships an `.mcp.json` declaring three web-search MCP servers, loaded
automatically when the plugin is enabled:

| Server | Package | Env var |
| --- | --- | --- |
| Exa | `exa-mcp-server` | `EXA_API_KEY` |
| Tavily | `tavily-mcp` | `TAVILY_API_KEY` |
| Brave Search | `@brave/brave-search-mcp-server` | `BRAVE_API_KEY` |

All three start under stdio via `npx`, so no global install is required — `npx`
will fetch them on first use.

### Configuring API keys

Two layers, with shell environment taking precedence:

1. **Shell profile** (preferred) — export in `~/.zshrc` / `~/.bashrc`:
   ```bash
   export EXA_API_KEY=...
   export TAVILY_API_KEY=...
   export BRAVE_API_KEY=...
   ```
2. **Project-local `.env`** — copy `.env.example` to `.env` in the directory
   where you launch Claude Code, and fill in any keys. The `.env` is only read
   for keys that aren't already set in your shell.

Get keys: Exa <https://dashboard.exa.ai/api-keys> · Tavily <https://app.tavily.com/home> · Brave <https://api.search.brave.com/app/keys>.

Missing a key only disables that one server; the other two still work. Confirm
servers are up via `/mcp` inside Claude Code — each should show as connected
with its tools listed.

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
