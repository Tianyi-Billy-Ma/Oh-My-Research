#!/usr/bin/env python3
"""Sync a local paper directory with an Overleaf project via pyoverleaf.

Intended to run under the SHARED pyoverleaf tool environment (the isolated
env created by `uv tool install pyoverleaf` or `pipx install pyoverleaf`),
NOT inside a research project's venv. The omr:sync-overleaf skill resolves
that interpreter and invokes this script with the project/paper-dir/cookie
arguments pulled from ./.omr/config.yaml.

Auth (two modes):
  --cookies <file>  if given and the file exists, load the Overleaf session
                    from it via api.login_from_cookies(json.loads(...)).
  (no --cookies)    fall back to pyoverleaf's native browser/keychain login
                    via api.login_from_browser() (reads the cookie out of the
                    logged-in browser; on macOS this prompts for keychain
                    access on first use).
The cookie bytes are only ever handed to the library; this script never
prints or logs their contents.

Project resolution:
  --project accepts either a 24-hex Overleaf project id (used directly) or a
  human project name (looked up against api.get_projects()).

Safety shape (mirrors the skill's rails):
  * pull defaults to a dry-friendly confirm prompt (--dry to preview only,
    -y to skip the prompt).
  * push requires explicit file paths -- there is no recursive default.

Run directly:
  python sync_overleaf.py --project "ARR'26 SupraBench" --paper-dir ./paper status
  python sync_overleaf.py --project <id> --paper-dir ./paper --cookies ~/.config/pyoverleaf/cookies.json pull --dry
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import pyoverleaf
from pyoverleaf import ProjectFile, ProjectFolder

_HEX24 = re.compile(r"^[0-9a-fA-F]{24}$")


def _api(cookies: str | None) -> pyoverleaf.Api:
    """Build an authenticated pyoverleaf.Api.

    If a cookies file path is supplied and exists, log in from it; otherwise
    fall back to pyoverleaf's native browser/keychain login.
    """
    api = pyoverleaf.Api()
    if cookies:
        cookie_path = Path(cookies).expanduser()
        if cookie_path.exists():
            # Hand the JSON straight to the library; never inspect/print it.
            api.login_from_cookies(json.loads(cookie_path.read_text()))
            return api
        sys.exit(
            f"--cookies pointed at {cookie_path}, but that file does not exist.\n"
            "Either create it (a JSON cookie dump) or omit --cookies to use\n"
            "pyoverleaf's native browser/keychain login."
        )
    # No cookie file: native browser/keychain auth (may prompt on macOS).
    api.login_from_browser()
    return api


def _resolve_project_id(api: pyoverleaf.Api, project: str) -> tuple[str, str]:
    """Return (project_id, project_name) for a name-or-id argument."""
    if _HEX24.match(project):
        # A raw id: try to recover a friendly name, but don't fail if we can't.
        for p in api.get_projects():
            if getattr(p, "id", None) == project:
                return project, getattr(p, "name", project)
        return project, project
    matches = [p for p in api.get_projects() if getattr(p, "name", None) == project]
    if not matches:
        names = ", ".join(repr(getattr(p, "name", "?")) for p in api.get_projects())
        sys.exit(
            f"no Overleaf project named {project!r}. Available: {names or '(none)'}.\n"
            "Pass --project with an exact name or a 24-hex project id."
        )
    if len(matches) > 1:
        ids = ", ".join(getattr(p, "id", "?") for p in matches)
        sys.exit(
            f"project name {project!r} is ambiguous (ids: {ids}). "
            "Pass the 24-hex id via --project instead."
        )
    return matches[0].id, matches[0].name


def _walk(node, prefix: str = ""):
    """Yield (relative_path, node) for every file in the remote tree."""
    children = getattr(node, "children", None)
    if children is None:
        return
    for c in children:
        c_children = getattr(c, "children", None)
        sub = f"{prefix}{c.name}"
        if c_children is None:
            yield sub, c
        else:
            yield from _walk(c, prefix=sub + "/")


def _local_files(paper_dir: Path) -> set[str]:
    return {
        str(p.relative_to(paper_dir))
        for p in paper_dir.rglob("*")
        if p.is_file() and ".git" not in p.parts
    }


def cmd_status(api: pyoverleaf.Api, project_id: str, project_name: str,
               paper_dir: Path, args: argparse.Namespace) -> int:
    root = api.project_get_files(project_id)
    remote = sorted(p for p, _ in _walk(root))
    local = sorted(_local_files(paper_dir))
    only_remote = set(remote) - set(local)
    only_local = set(local) - set(remote)
    both = sorted(set(remote) & set(local))
    print(f"Project: {project_name} ({project_id})")
    print(f"Local  : {paper_dir}")
    print(f"\n[remote-only] ({len(only_remote)})")
    for p in sorted(only_remote):
        print(f"  + {p}")
    print(f"\n[local-only] ({len(only_local)})")
    for p in sorted(only_local):
        print(f"  - {p}")
    print(f"\n[both] ({len(both)})  (run `pull --dry` to diff contents)")
    for p in both:
        print(f"  = {p}")
    return 0


def cmd_pull(api: pyoverleaf.Api, project_id: str, project_name: str,
             paper_dir: Path, args: argparse.Namespace) -> int:
    print(f"downloading Overleaf project {project_name} ({project_id})...")
    blob = api.download_project(project_id)
    zf = zipfile.ZipFile(BytesIO(blob))
    members = [m for m in zf.namelist() if not m.endswith("/")]
    print(f"  {len(members)} files in zip")

    changes: list[tuple[str, str]] = []  # (status, relpath)
    writes: list[tuple[Path, bytes]] = []
    for m in members:
        data = zf.read(m)
        target = paper_dir / m
        if target.exists():
            if target.read_bytes() == data:
                continue
            changes.append(("modified", m))
        else:
            changes.append(("new", m))
        writes.append((target, data))

    remote_files = set(members)
    for p in sorted(_local_files(paper_dir) - remote_files):
        changes.append(("local-only", p))

    if not changes:
        print("local already matches Overleaf")
        return 0

    print("\nplanned changes:")
    for status, p in changes:
        print(f"  [{status}] {p}")

    if args.dry:
        print("\n--dry: not writing")
        return 0
    if not args.yes:
        ans = input("\napply these changes to local? [y/N] ").strip().lower()
        if ans != "y":
            print("aborted")
            return 1

    for target, data in writes:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    print(f"wrote {len(writes)} file(s)")
    return 0


def cmd_push(api: pyoverleaf.Api, project_id: str, project_name: str,
             paper_dir: Path, args: argparse.Namespace) -> int:
    root = api.project_get_files(project_id)

    remote_by_path: dict[str, ProjectFile] = {}
    folders_by_path: dict[str, ProjectFolder] = {"": root}

    def index(node: ProjectFolder, prefix: str = "") -> None:
        for c in node.children or []:
            sub = f"{prefix}{c.name}"
            if isinstance(c, ProjectFolder):
                folders_by_path[sub] = c
                index(c, prefix=sub + "/")
            else:
                remote_by_path[sub] = c

    index(root)

    pushed = 0
    for spec in args.paths:
        local = (paper_dir / spec).resolve()
        if not local.is_file():
            print(f"  skip: not a file -> {spec}")
            continue
        rel = str(local.relative_to(paper_dir.resolve()))
        data = local.read_bytes()
        parent_rel, _, name = rel.rpartition("/")
        parent = folders_by_path.get(parent_rel)
        if parent is None and parent_rel:
            # Create any missing parent folders on the remote.
            segments = parent_rel.split("/")
            cursor = ""
            for seg in segments:
                next_path = f"{cursor}/{seg}" if cursor else seg
                if next_path not in folders_by_path:
                    cursor_node = folders_by_path[cursor]
                    new_node = api.project_create_folder(project_id, cursor_node.id, seg)
                    folders_by_path[next_path] = new_node
                    print(f"  mkdir {next_path}")
                cursor = next_path
            parent = folders_by_path[parent_rel]
        if parent is None:
            print(f"  skip: remote folder {parent_rel!r} missing for {rel}")
            continue
        action = "overwrite" if rel in remote_by_path else "create"
        print(f"  push [{action}] {rel} ({len(data)} bytes)")
        api.project_upload_file(project_id, parent.id, name, data)
        pushed += 1
    print(f"\npushed {pushed} file(s)")
    return 0


def cmd_rm(api: pyoverleaf.Api, project_id: str, project_name: str,
           paper_dir: Path, args: argparse.Namespace) -> int:
    root = api.project_get_files(project_id)

    remote_by_path: dict[str, ProjectFile] = {}

    def index(node, prefix: str = "") -> None:
        for c in node.children or []:
            sub = f"{prefix}{c.name}"
            if isinstance(c, ProjectFolder):
                index(c, prefix=sub + "/")
            else:
                remote_by_path[sub] = c

    index(root)

    deleted = 0
    for rel in args.paths:
        node = remote_by_path.get(rel)
        if node is None:
            print(f"  skip: not on remote -> {rel}")
            continue
        api.project_delete_entity(project_id, node)
        print(f"  rm {rel}")
        deleted += 1
    print(f"\ndeleted {deleted} file(s) on remote")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Sync a local paper dir with Overleaf via pyoverleaf.")
    p.add_argument("--project", required=True,
                   help="Overleaf project name OR 24-hex project id")
    p.add_argument("--paper-dir", required=True,
                   help="local paper directory to sync against")
    p.add_argument("--cookies", default="",
                   help="path to a JSON cookie dump; empty/omitted = native browser login")

    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="list local vs remote inventory")

    pp = sub.add_parser("pull", help="bring remote into local working tree")
    pp.add_argument("--dry", action="store_true", help="show planned writes only")
    pp.add_argument("-y", "--yes", action="store_true", help="skip confirmation prompt")

    psh = sub.add_parser("push", help="upload specific local files to Overleaf")
    psh.add_argument("paths", nargs="+", help="paths under --paper-dir to push")

    prm = sub.add_parser("rm", help="delete specific files from the remote project")
    prm.add_argument("paths", nargs="+", help="paths under --paper-dir to delete on remote")

    args = p.parse_args()

    paper_dir = Path(args.paper_dir).expanduser()
    if not paper_dir.is_dir():
        sys.exit(f"--paper-dir {paper_dir} is not a directory")

    cookies = args.cookies.strip() or None
    api = _api(cookies)
    project_id, project_name = _resolve_project_id(api, args.project)

    handler = {
        "status": cmd_status,
        "pull": cmd_pull,
        "push": cmd_push,
        "rm": cmd_rm,
    }[args.cmd]
    return handler(api, project_id, project_name, paper_dir, args)


if __name__ == "__main__":
    raise SystemExit(main())
