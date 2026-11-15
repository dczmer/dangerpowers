#!/usr/bin/env python3
"""tasks.py — zero-dependency markdown task tracker CLI.

Single file, Python 3 standard library only. Tasks live as flat markdown
files with YAML frontmatter in a project-local artifacts dir; this script
is the only writer of frontmatter. Design: .tmp/task-tracker-design.md in
the skills repo (sections referenced as §N in comments below).
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn, Optional, Union

YamlValue = Union[str, list]

CONFIG_NAME = ".tasks.yaml"
DEFAULT_ARTIFACTS_DIR = "tasks"
MAX_TASK_NUMBER = 999

_TASK_FILE_RE = re.compile(r"^(\d{3})_[A-Za-z0-9\-_]+\.md$")
_SLUG_RUN_RE = re.compile(r"[^a-z0-9\-_]+")
_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9\-_]*):(.*)$")
_ESCAPES = {"\\": "\\", '"': '"', "n": "\n", "t": "\t"}

# Canonical frontmatter key order (§4): required fields first, then optionals.
CANONICAL_ORDER = (
    "title",
    "type",
    "state",
    "author",
    "created",
    "updated",
    "parent",
    "reason",
    "priority",
    "tags",
)


class TasksError(Exception):
    """Fatal user-facing error; exit 1, printed with a prefix."""


class YamlError(TasksError):
    """Input outside the supported flat-YAML subset."""


# --------------------------------------------------------------------- #
# Flat YAML subset parser/emitter (§8)                                  #
# --------------------------------------------------------------------- #


def _strip_comment(line: str) -> str:
    """Cut a trailing ``#`` comment that is not inside quotes."""
    in_single = False
    in_double = False
    i = 0
    while i < len(line):
        ch = line[i]
        if in_double:
            if ch == "\\":
                i += 2
                continue
            in_double = ch != '"'
        elif in_single:
            in_single = ch != "'"
        elif ch == '"':
            in_double = True
        elif ch == "'":
            in_single = True
        elif ch == "#":
            return line[:i]
        i += 1
    return line


def parse_yaml_subset(text: str) -> dict:
    """Parse flat ``key: value`` pairs (§8 subset).

    Supports plain/single/double-quoted scalars, inline lists, and ``#``
    comments outside quotes. Rejects nesting, indented lines, duplicate
    keys, and unterminated quotes with :class:`YamlError`.
    """
    result: dict = {}
    for lineno, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped == "---":
            continue
        if raw[0] in (" ", "\t"):
            raise YamlError(
                f"line {lineno}: nested/indented YAML is not supported"
            )
        line = _strip_comment(raw).strip()
        if not line or line == "---":
            continue
        match = _KEY_RE.match(line)
        if match is None:
            raise YamlError(
                f"line {lineno}: expected 'key: value', got: {line!r}"
            )
        key, raw_value = match.group(1), match.group(2).strip()
        if key in result:
            raise YamlError(f"line {lineno}: duplicate key: {key}")
        result[key] = _parse_value(raw_value, lineno)
    return result


def _parse_value(text: str, lineno: int) -> YamlValue:
    if text == "":
        return ""
    if text.startswith('"'):
        return _parse_double_quoted(text, lineno)
    if text.startswith("'"):
        return _parse_single_quoted(text, lineno)
    if text.startswith("["):
        return _parse_inline_list(text, lineno)
    if text.startswith("]"):
        raise YamlError(f"line {lineno}: malformed inline list: {text!r}")
    return text


def _parse_double_quoted(text: str, lineno: int) -> str:
    if len(text) < 2 or not text.endswith('"'):
        raise YamlError(f"line {lineno}: unterminated double-quoted string")
    inner = text[1:-1]
    out = []
    i = 0
    while i < len(inner):
        ch = inner[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        i += 1
        if i >= len(inner) or inner[i] not in _ESCAPES:
            raise YamlError(
                f"line {lineno}: bad escape in double-quoted string"
            )
        out.append(_ESCAPES[inner[i]])
        i += 1
    return "".join(out)


def _parse_single_quoted(text: str, lineno: int) -> str:
    if len(text) < 2 or not text.endswith("'"):
        raise YamlError(f"line {lineno}: unterminated single-quoted string")
    return text[1:-1].replace("''", "'")


def _parse_inline_list(text: str, lineno: int) -> list:
    if len(text) < 2 or not text.endswith("]"):
        raise YamlError(f"line {lineno}: unterminated inline list")
    inner = text[1:-1].strip()
    if not inner:
        return []
    items = []
    for part in _split_list_items(inner, lineno):
        item = part.strip()
        if item.startswith('"'):
            items.append(_parse_double_quoted(item, lineno))
        elif item.startswith("'"):
            items.append(_parse_single_quoted(item, lineno))
        else:
            items.append(item)
    return items


def _split_list_items(inner: str, lineno: int) -> list:
    """Split on commas outside quotes."""
    parts = []
    start = 0
    in_single = False
    in_double = False
    i = 0
    while i < len(inner):
        ch = inner[i]
        if in_double:
            if ch == "\\":
                i += 2
                continue
            in_double = ch != '"'
        elif in_single:
            in_single = ch != "'"
        elif ch == '"':
            in_double = True
        elif ch == "'":
            in_single = True
        elif ch == ",":
            parts.append(inner[start:i])
            start = i + 1
        i += 1
    if in_single or in_double:
        raise YamlError(f"line {lineno}: unterminated quote in inline list")
    parts.append(inner[start:])
    return parts


def _needs_quoting(value: str) -> bool:
    """Quote only when a plain scalar would parse ambiguously (locked)."""
    if value == "" or value != value.strip():
        return True
    if value[0] in "'\"":
        return True
    return any(ch in value for ch in (":", "#", "[", "]"))


def _quote(value: str) -> str:
    if not _needs_quoting(value):
        return value
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def emit_yaml(fields: dict) -> str:
    """Emit normalized flat YAML: one key per line, canonical key order."""
    keys = [key for key in CANONICAL_ORDER if key in fields]
    keys += sorted(key for key in fields if key not in CANONICAL_ORDER)
    lines = []
    for key in keys:
        value = fields[key]
        if isinstance(value, list):
            rendered = ", ".join(_quote(item) for item in value)
            lines.append(f"{key}: [{rendered}]")
        else:
            lines.append(f"{key}: {_quote(value)}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------- #
# Config discovery (§2)                                                 #
# --------------------------------------------------------------------- #


@dataclass
class Config:
    """Resolved runtime configuration."""

    path: Optional[Path]  # .tasks.yaml location; None when defaults are used
    artifacts_dir: Path  # absolute
    author: Optional[str]  # from the config file only


def discover_config(
    config_flag: Optional[str],
    dir_flag: Optional[str],
    cwd: Path,
) -> Config:
    """Resolve config: flag → upward walk for .tasks.yaml → defaults (§2)."""
    cfg_path: Optional[Path] = None
    base = cwd
    if config_flag is not None:
        cfg_path = Path(config_flag)
        if not cfg_path.is_file():
            raise TasksError(f"config file not found: {cfg_path}")
        base = cfg_path.resolve().parent
    else:
        for directory in (cwd, *cwd.parents):
            candidate = directory / CONFIG_NAME
            if candidate.is_file():
                cfg_path = candidate
                base = directory
                break
    author: Optional[str] = None
    if cfg_path is not None:
        data = parse_yaml_subset(cfg_path.read_text(encoding="utf-8"))
        raw_dir = data.get("artifacts_dir", DEFAULT_ARTIFACTS_DIR)
        if not isinstance(raw_dir, str):
            raise TasksError(
                f"{cfg_path}: artifacts_dir must be a plain string"
            )
        artifacts_dir = base / raw_dir
        raw_author = data.get("author")
        if isinstance(raw_author, str) and raw_author.strip():
            author = raw_author.strip()
    else:
        artifacts_dir = cwd / DEFAULT_ARTIFACTS_DIR
    if dir_flag is not None:
        override = Path(dir_flag)
        artifacts_dir = override if override.is_absolute() else cwd / override
    return Config(
        path=cfg_path,
        artifacts_dir=artifacts_dir.resolve(),
        author=author,
    )


# --------------------------------------------------------------------- #
# Author resolution (§4)                                                #
# --------------------------------------------------------------------- #


def _git_config_user_name(cwd: Path) -> Optional[str]:
    try:
        proc = subprocess.run(
            ["git", "config", "user.name"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    name = proc.stdout.strip()
    return name or None


def resolve_author(
    flag_author: Optional[str],
    cfg_author: Optional[str],
    cwd: Path,
) -> str:
    """Author chain: --author → config author → git config → $USER (§4)."""
    if flag_author and flag_author.strip():
        return flag_author.strip()
    if cfg_author:
        return cfg_author
    git_name = _git_config_user_name(cwd)
    if git_name:
        return git_name
    env_user = os.environ.get("USER", "").strip()
    if env_user:
        return env_user
    raise TasksError("could not determine author; pass --author NAME")


# --------------------------------------------------------------------- #
# Slug + numbering (§3)                                                 #
# --------------------------------------------------------------------- #


def slugify(title: str) -> str:
    """Lowercase slug; runs outside [a-z0-9-_] collapse to one '-'."""
    return _SLUG_RUN_RE.sub("-", title.lower()).strip("-")


def task_numbers(artifacts_dir: Path) -> list:
    """Numbers of files matching NNN_slug.md; missing dir → empty (§3)."""
    if not artifacts_dir.is_dir():
        return []
    numbers = []
    for entry in artifacts_dir.iterdir():
        match = _TASK_FILE_RE.match(entry.name)
        if match is not None:
            numbers.append(int(match.group(1)))
    return numbers


def next_number(artifacts_dir: Path) -> int:
    """Max existing number + 1; gaps are never backfilled (§3)."""
    number = max(task_numbers(artifacts_dir), default=0) + 1
    if number > MAX_TASK_NUMBER:
        raise TasksError(
            f"task numbers exhausted (>999) in {artifacts_dir}; "
            "this project has outgrown the tool"
        )
    return number


# --------------------------------------------------------------------- #
# ID resolution (§8)                                                    #
# --------------------------------------------------------------------- #


def resolve_id(artifacts_dir: Path, arg: str) -> Path:
    """Resolve a task reference: exact filename, 3-digit number, or unique
    filename prefix. Ambiguous or unknown references raise TasksError."""
    if not artifacts_dir.is_dir():
        raise TasksError(
            f"artifacts dir not found: {artifacts_dir} "
            "(run 'tasks.py init'?)"
        )
    direct = artifacts_dir / arg
    if direct.is_file():
        return direct
    names = sorted(p.name for p in artifacts_dir.iterdir() if p.is_file())
    if re.fullmatch(r"\d{3}", arg):
        matches = [name for name in names if name.startswith(arg + "_")]
        if len(matches) == 1:
            return artifacts_dir / matches[0]
        if not matches:
            raise TasksError(
                f"no task file with number {arg} in {artifacts_dir}"
            )
        raise TasksError(f"ambiguous task number {arg}: {', '.join(matches)}")
    matches = [name for name in names if name.startswith(arg)]
    if len(matches) == 1:
        return artifacts_dir / matches[0]
    if len(matches) > 1:
        raise TasksError(
            f"ambiguous id {arg!r}; matches: {', '.join(matches)}"
        )
    raise TasksError(f"no task file matching {arg!r} in {artifacts_dir}")


# --------------------------------------------------------------------- #
# CLI skeleton (§8): stubs for phases 2–4                               #
# --------------------------------------------------------------------- #


def _not_implemented(args: argparse.Namespace) -> int:
    print(
        f"tasks.py: error: {args.command}: not implemented yet",
        file=sys.stderr,
    )
    return 1


class _Parser(argparse.ArgumentParser):
    """ArgumentParser that exits 1 (not 2) on usage errors (§8 exit codes)."""

    def error(self, message: str) -> NoReturn:
        self.exit(1, f"{self.prog}: error: {message}\n")


def _add_global(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        metavar="PATH",
        help=f"path to {CONFIG_NAME} (default: walk upward from cwd)",
    )
    parser.add_argument(
        "--dir",
        metavar="PATH",
        help="override the configured artifacts dir",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="tasks.py",
        description="Zero-dependency markdown task tracker.",
    )
    _add_global(parser)
    sub = parser.add_subparsers(dest="command", metavar="command")

    def stub(name: str, help_text: str) -> argparse.ArgumentParser:
        cmd = sub.add_parser(name, help=help_text)
        _add_global(cmd)
        cmd.set_defaults(command=name, func=_not_implemented)
        return cmd

    p = stub("init", "create .tasks.yaml and the artifacts dir")
    p.add_argument("--author", metavar="NAME")

    p = stub("new", "create a task/bug/subtask from a template")
    p.add_argument("kind", choices=["task", "bug", "subtask"])
    p.add_argument("title")
    p.add_argument("--parent", metavar="FILE")
    p.add_argument("--author", metavar="NAME")
    p.add_argument("--priority", choices=["low", "medium", "high"])
    p.add_argument("--tags", metavar="A,B")
    p.add_argument("--slug", metavar="SLUG")
    p.add_argument(
        "--state",
        choices=["draft", "open", "in-progress", "complete", "invalid"],
    )

    p = stub("list", "list tasks, one per line")
    p.add_argument("--state", action="append")
    p.add_argument("--type", action="append")
    p.add_argument("--tag", action="append")
    p.add_argument("--author", action="append")

    stub("show", "print a task file verbatim").add_argument("id")

    p = stub("set-state", "change a task's state")
    p.add_argument("id")
    p.add_argument("state")
    p.add_argument("--reason")

    p = stub("set", "edit a frontmatter field")
    p.add_argument("id")
    p.add_argument("field")
    p.add_argument("value")

    stub("validate", "check tasks against the schema").add_argument(
        "id", nargs="*"
    )

    stub("links", "show outbound/inbound links").add_argument("id")

    stub("grep", "pass-through to rg over the artifacts dir").add_argument(
        "rg_args", nargs=argparse.REMAINDER
    )

    sub.add_parser("next-id", help="print the next task number").set_defaults(
        command="next-id", func=_not_implemented
    )
    return parser


def main(
    argv: Optional[list] = None,
    cwd: Optional[Union[str, Path]] = None,
) -> int:
    root = Path(cwd) if cwd is not None else Path.cwd()
    root = root.resolve()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_usage(sys.stderr)
        return 1
    args.cwd = root
    try:
        return int(args.func(args) or 0)
    except TasksError as exc:
        print(f"tasks.py: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
