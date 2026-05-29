# Supporting reference — pyoverleaf usage

Not part of the ordered execution path. Load this when the user asks "what is
pyoverleaf?", "how do I install it?", or "how do auth / cookies work?". The
ordered phases (`01`–`04`) drive the actual sync; this doc is the background
the agent can quote.

## What pyoverleaf is

`pyoverleaf` (GitHub: [jkulhanek/pyoverleaf](https://github.com/jkulhanek/pyoverleaf))
is a small Python library + CLI that talks to Overleaf's unofficial web API
using your **browser session cookie** for authentication. It can list
projects, read/write files, create folders, delete entities, and download a
whole project as a zip. This skill drives it through
`scripts/sync_overleaf.py` rather than the raw CLI, because the script wires
the project / paper-dir / cookie arguments from `./.omr/config.yaml` and keeps
the dry-run-before-push safety shape.

## Install — via the SHARED TOOL ENV only

pyoverleaf lives in an **isolated, cross-project tool environment** — never in
a research project's venv. Installing it with `uv add` / `pip install` into a
project would pollute that project's dependency set and tie a global utility to
one repo. Use a tool installer instead:

```bash
# preferred
uv tool install pyoverleaf

# fallback (if uv isn't present)
pipx install pyoverleaf
```

Phase 2 (`02-preflight.md`) auto-detects which installer to use, asks for
consent via `AskUserQuestion` before installing, and records the choice in
`./.omr/config.yaml` under `overleaf.tool_installer`. After install,
`pyoverleaf` is on `PATH` and the tool's own Python interpreter can run
`sync_overleaf.py` with `pyoverleaf` importable.

**Never** run `uv add pyoverleaf` or `pip install pyoverleaf` inside the
research project's venv. The shared tool env is the only correct home.

## Authentication — two modes

`sync_overleaf.py` accepts a `--cookies <path>` argument and behaves
differently depending on whether it's given and the file exists:

1. **Native browser / keychain login (default — no `--cookies`).**
   `pyoverleaf.Api().login_from_browser()` reads the Overleaf session cookie
   straight out of the browser you're logged into (Chrome/Firefox). On macOS
   the first run prompts for **keychain access** so the tool can read the
   browser cookie store — the user must approve it (choose "Always Allow" to
   avoid repeated prompts). The agent cannot log in for the user; browser
   auth is the user's action.

2. **Headless cookie file (`--cookies <path>`).**
   When there's no interactive browser/keychain (CI, a remote box, a headless
   shell), dump the Overleaf cookies into a JSON file and point `--cookies` at
   it. The script then calls `api.login_from_cookies(json.loads(...))`. The
   config field `overleaf.auth.cookie_path` holds the **path** to this file;
   the cookie value itself never lives in `config.yaml` or in chat.

In both modes the cookie bytes are handed only to the library — the script
never prints, logs, or echoes them.

### Keychain security note

Granting pyoverleaf keychain access lets it read your browser's cookie
storage, which can include sessions beyond Overleaf. The Overleaf session
cookie is an **account-level secret** — leaking it can grant access beyond a
single project. Keep it behind a pointer (`cookie_path` / browser keychain),
out of `config.yaml`, out of chat, out of logs. Audit the installed pyoverleaf
version before granting access if you're unsure (the codebase is small and
readable on GitHub).

## `sync_overleaf.py` command reference

The script runs under the shared pyoverleaf tool interpreter. Resolve that
interpreter (the one `uv tool install` / `pipx install` created) and invoke:

```bash
# Global options apply to every subcommand:
#   --project <name-or-24hex-id>   which Overleaf project
#   --paper-dir <path>             local directory to sync against
#   --cookies <path>               JSON cookie dump; omit for browser login

# Inventory: what's local-only / remote-only / on both sides
python sync_overleaf.py --project "ARR-26-MemoVQ" --paper-dir ./paper status

# Pull (preview first, then apply). Dry by intent; -y skips the prompt.
python sync_overleaf.py --project <id> --paper-dir ./paper pull --dry
python sync_overleaf.py --project <id> --paper-dir ./paper pull        # prompts
python sync_overleaf.py --project <id> --paper-dir ./paper pull -y     # no prompt

# Push specific files only — no recursive default. Paths are relative to --paper-dir.
python sync_overleaf.py --project <id> --paper-dir ./paper push main.tex sections/intro.tex

# Remove specific files from the remote project (paths relative to --paper-dir layout)
python sync_overleaf.py --project <id> --paper-dir ./paper rm scratch.tex
```

`--project` takes either a human project name (looked up via
`api.get_projects()`) or a raw 24-hex Overleaf project id (used directly).

## Self-hosted Overleaf

pyoverleaf honours `PYOVERLEAF_HOST` for self-hosted instances
(`export PYOVERLEAF_HOST=overleaf.mycompany.com`). The default
`overleaf.com` host can trigger a websocket redirect bug; setting
`PYOVERLEAF_HOST=www.overleaf.com` is the documented fix. This skill doesn't
manage that env var — set it in your shell if you hit redirect errors.

## Handoff

This is a supporting doc, not an ordered phase. After reading it, return to the
numbered phase you were executing (`01`–`04`).
