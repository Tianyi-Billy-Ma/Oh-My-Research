# Oh-My-Research

Research workflows and skills for Claude Code.

## Install

```bash
claude --plugin-dir /path/to/Oh-My-Research
```

For persistent installation via a marketplace, see the Claude Code plugin docs at https://code.claude.com/docs/en/plugins.

## Layout

This plugin follows the official Claude Code plugin template:

```
Oh-My-Research/
├── .claude-plugin/
│   └── plugin.json
├── skills/        # add <name>/SKILL.md folders here
├── agents/        # optional agent definitions
├── hooks/         # optional hooks.json
└── README.md
```

Only `plugin.json` lives inside `.claude-plugin/`. All component directories (skills, agents, hooks, etc.) sit at the plugin root.

## License

MIT
