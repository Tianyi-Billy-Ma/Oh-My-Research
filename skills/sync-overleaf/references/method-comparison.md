# Supporting reference — pyoverleaf vs git

Not part of the ordered execution path. Load this when the user asks "which
method should I use?" or when `overleaf.sync_method` is unset and you want to
explain the trade-offs before asking via `AskUserQuestion`.

## At a glance

| Dimension | pyoverleaf (cookie) | git (Overleaf git remote) |
| --- | --- | --- |
| Auth pointer | `cookie_path` (file) or `cookie_env` (env var) | `ssh_key_path` (SSH) or `token_env` (HTTPS token) |
| What it talks to | Unofficial Overleaf web API | Overleaf's per-project git bridge |
| Overleaf plan | Works on free tier | Git access historically needs a paid feature; confirm the project has a Git clone URL |
| Granularity | File-level upload/download | Full git history, commits, branches, rebases |
| Conflict handling | Manual (compare + choose a side) | Native git merge/rebase with conflict markers |
| Reversibility | Low — overwrites the live doc | Higher — commits are recoverable until force-pushed |
| Fragility | Cookie expires; API is unofficial and can break | Stable, but the remote URL/credential must be set up once |
| Best for | Quick one-off file pushes when git isn't enabled | Ongoing collaboration, history, careful reconciliation |

## Guidance

- Prefer **git** when the project has a Git clone URL: it gives you real history,
  safe rebases, and `--force-with-lease` as a last resort instead of a blind
  overwrite. This is the safer default for a shared paper.
- Use **pyoverleaf** when git access isn't available (free-tier projects often
  lack the git bridge) or for a quick file drop. Accept that conflict handling
  is manual and a push overwrites the live document.
- Either way, the credential is always referenced by a **pointer** in
  `config.yaml` — a file path or an env-var name — never the value. The skill
  resolves it to the actual secret only at the instant the tool needs it.

## Security notes (both methods)

- The session cookie (pyoverleaf) and the git token (HTTPS) are
  account-level secrets — leaking one can grant access beyond a single project.
  Keep them behind a pointer, out of `config.yaml`, out of chat, out of logs.
- For SSH, the key never needs to be read by this skill at all — `git` reads it
  via the agent or `GIT_SSH_COMMAND -i <path>`. That makes `ssh_key_path` the
  lowest-exposure option for the git method.
