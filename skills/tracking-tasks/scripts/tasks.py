#!/usr/bin/env python3
"""tasks.py — zero-dependency markdown task tracker CLI.

Single file, Python 3 standard library only. Tasks live as flat markdown
files with YAML frontmatter in a project-local artifacts dir; this script
is the only writer of frontmatter. Design: .tmp/task-tracker-design.md in
the skills repo (sections referenced as §N in comments below).
"""

from __future__ import annotations

import argparse
import datetime
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
# Task file IO: frontmatter + verbatim body (§4, §8)                    #
# --------------------------------------------------------------------- #

STATES = ("draft", "open", "in-progress", "complete", "invalid")
TYPES = ("task", "bug", "subtask")
PARENT_TYPES = ("task", "bug")
PRIORITIES = ("low", "medium", "high")

# Shared by `new`, `set-state`, `set`, and (Phase 4) `validate` so the
# warning wording matches across all paths.
WARNING_INVALID_NO_REASON = "state is 'invalid' but no reason given"

_FIELD_ENUMS = {"type": TYPES, "state": STATES, "priority": PRIORITIES}
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"


def _today() -> str:
    """Local date, YYYY-MM-DD (§4)."""
    # Spec requires the *local* date; a tz-aware UTC date could differ near
    # midnight, so naive local is intentional here.
    return datetime.date.today().isoformat()  # noqa: DTZ011


def _warn(message: str) -> None:
    print(f"tasks.py: warning: {message}", file=sys.stderr)


def _validate_date(field: str, value: str) -> None:
    """Dates are YYYY-MM-DD and must be real calendar dates (§4)."""
    if _DATE_RE.fullmatch(value) is None:
        raise TasksError(f"{field} must be a date in YYYY-MM-DD form")
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        raise TasksError(f"{field} is not a valid date: {value}") from None


def _validate_parent_file(artifacts_dir: Path, parent_name: str) -> None:
    """A parent must exist and be a task or bug, not a subtask (§4)."""
    parent_path = artifacts_dir / parent_name
    if not parent_path.is_file():
        raise TasksError(f"parent file not found: {parent_name}")
    parent_fields, _ = read_task(parent_path)
    parent_type = parent_fields.get("type")
    if parent_type not in PARENT_TYPES:
        raise TasksError(
            f"parent {parent_name} has type {parent_type!r}; "
            "parents must be task or bug"
        )


def _warn_if_invalid_without_reason(fields: dict) -> None:
    if fields.get("state") == "invalid" and not fields.get("reason"):
        _warn(WARNING_INVALID_NO_REASON)


def parse_task(text: str, name: str):
    """Split a task file into (fields, body); body is preserved verbatim."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise TasksError(f"{name}: missing frontmatter opening '---'")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise TasksError(f"{name}: missing frontmatter closing '---'")
    fields = parse_yaml_subset("\n".join(lines[1:end]))
    body = "\n".join(lines[end + 1 :])
    return fields, body


def render_task(fields: dict, body: str) -> str:
    return "---\n" + emit_yaml(fields) + "---\n" + body


def read_task(path: Path):
    return parse_task(path.read_text(encoding="utf-8"), path.name)


def _load_config(args: argparse.Namespace) -> Config:
    return discover_config(args.config, args.dir, args.cwd)


def _require_artifacts_dir(cfg: Config) -> Path:
    """Read commands fail clearly when the artifacts dir is missing (§8)."""
    if not cfg.artifacts_dir.is_dir():
        raise TasksError(
            f"artifacts dir not found: {cfg.artifacts_dir} "
            "(run 'tasks.py init'?)"
        )
    return cfg.artifacts_dir


# --------------------------------------------------------------------- #
# Commands (§8)                                                         #
# --------------------------------------------------------------------- #


def _not_implemented(args: argparse.Namespace) -> int:
    print(
        f"tasks.py: error: {args.command}: not implemented yet",
        file=sys.stderr,
    )
    return 1


def cmd_init(args: argparse.Namespace) -> int:
    """Create .tasks.yaml in cwd plus the artifacts dir; idempotent (§8)."""
    if args.config:
        config_path = Path(args.config)
        base = config_path.resolve().parent
    else:
        config_path = args.cwd / CONFIG_NAME
        base = args.cwd
    if config_path.exists():
        print(f"{config_path} already exists; leaving it unchanged")
        existing = parse_yaml_subset(config_path.read_text(encoding="utf-8"))
        artifacts_value = args.dir or existing.get(
            "artifacts_dir", DEFAULT_ARTIFACTS_DIR
        )
    else:
        artifacts_value = args.dir or DEFAULT_ARTIFACTS_DIR
        lines = [f"artifacts_dir: {_quote(artifacts_value)}"]
        if args.author:
            lines.append(f"author: {_quote(args.author)}")
        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"created {config_path}")
    artifacts_dir = Path(artifacts_value)
    if not artifacts_dir.is_absolute():
        artifacts_dir = base / artifacts_dir
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    print(f"artifacts dir ready: {artifacts_dir}")
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    """Clone a template, fill frontmatter, assign the next number (§7/§8)."""
    cfg = _load_config(args)
    artifacts_dir = cfg.artifacts_dir
    author = resolve_author(args.author, cfg.author, args.cwd)
    if args.parent and args.kind != "subtask":
        raise TasksError("--parent is only valid for subtask")
    # Create the artifacts dir up front so parent resolution can scan it (§2).
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    parent_name = None
    if args.parent:
        parent_path = resolve_id(artifacts_dir, args.parent)
        parent_fields, _ = read_task(parent_path)
        if parent_fields.get("type") not in PARENT_TYPES:
            raise TasksError(
                f"parent {parent_path.name} has type "
                f"{parent_fields.get('type')!r}; parents must be task or bug"
            )
        parent_name = parent_path.name
    if args.kind == "subtask" and parent_name is None:
        raise TasksError("subtask requires --parent FILE")
    template_path = TEMPLATE_DIR / f"{args.kind}.md"
    template = template_path.read_text(encoding="utf-8")
    filled = (
        template.replace("{{title}}", args.title)
        .replace("{{author}}", author)
        .replace("{{date}}", _today())
        .replace("{{parent}}", parent_name or "")
    )
    fields, body = parse_task(filled, template_path.name)
    if parent_name is not None:
        fields["parent"] = parent_name
    fields["state"] = args.state or "draft"
    if args.priority:
        fields["priority"] = args.priority
    if args.tags is not None:
        fields["tags"] = [
            item.strip() for item in args.tags.split(",") if item.strip()
        ]
    if args.reason:
        fields["reason"] = args.reason
    _warn_if_invalid_without_reason(fields)
    if args.slug:
        slug = args.slug
        if re.fullmatch(r"[A-Za-z0-9\-_]+", slug) is None:
            raise TasksError(
                f"invalid slug {slug!r}: allowed characters are "
                "[a-zA-Z0-9-_]"
            )
    else:
        slug = slugify(args.title)
        if not slug:
            raise TasksError(
                "could not derive a slug from the title; pass --slug SLUG"
            )
    # Best-effort concurrency: re-scan right before write, fail on collision.
    number = next_number(artifacts_dir)
    path = artifacts_dir / f"{number:03d}_{slug}.md"
    if path.exists():
        raise TasksError(f"filename collision: {path.name} already exists")
    path.write_text(render_task(fields, body), encoding="utf-8")
    print(path)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """One line per task: `ID  state  type  title` (§8)."""
    artifacts_dir = _require_artifacts_dir(_load_config(args))
    rows = []
    for path in sorted(artifacts_dir.iterdir()):
        match = _TASK_FILE_RE.match(path.name)
        if match is None:
            continue
        fields, _ = read_task(path)
        rows.append((int(match.group(1)), fields))
    if args.state:
        wanted = set(args.state)
        rows = [row for row in rows if row[1].get("state") in wanted]
    if args.type:
        wanted = set(args.type)
        rows = [row for row in rows if row[1].get("type") in wanted]
    if args.author:
        wanted = set(args.author)
        rows = [row for row in rows if row[1].get("author") in wanted]
    if args.tag:
        wanted = set(args.tag)
        rows = [row for row in rows if wanted & set(row[1].get("tags") or [])]
    for number, fields in rows:
        print(
            f"{number:03d}  {fields.get('state', '')}  "
            f"{fields.get('type', '')}  {fields.get('title', '')}"
        )
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """Print the task file verbatim (§8)."""
    cfg = _load_config(args)
    path = resolve_id(cfg.artifacts_dir, args.id)
    sys.stdout.write(path.read_text(encoding="utf-8"))
    return 0


def cmd_next_id(args: argparse.Namespace) -> int:
    """Print the next task number, e.g. `017` (§8)."""
    artifacts_dir = _require_artifacts_dir(_load_config(args))
    print(f"{next_number(artifacts_dir):03d}")
    return 0


def cmd_set_state(args: argparse.Namespace) -> int:
    """Change a task's state (any→any, no workflow enforcement); the
    ``reason`` field is set when given; ``updated`` is refreshed (§5/§8)."""
    artifacts_dir = _require_artifacts_dir(_load_config(args))
    path = resolve_id(artifacts_dir, args.id)
    fields, body = read_task(path)
    fields["state"] = args.state
    if args.reason is not None:
        fields["reason"] = args.reason
    fields["updated"] = _today()
    _warn_if_invalid_without_reason(fields)
    path.write_text(render_task(fields, body), encoding="utf-8")
    print(path)
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    """Generic validated frontmatter edit; every field except ``created``
    is settable (locked decision), each with per-field validation (§4/§8).
    ``updated`` is refreshed unless it is the field being set."""
    artifacts_dir = _require_artifacts_dir(_load_config(args))
    path = resolve_id(artifacts_dir, args.id)
    field, value = args.field, args.value
    if field == "created":
        raise TasksError(
            "'created' cannot be set; it is fixed at creation time"
        )
    if field not in CANONICAL_ORDER:
        settable = ", ".join(
            name for name in CANONICAL_ORDER if name != "created"
        )
        raise TasksError(f"unknown field {field!r}; settable: {settable}")
    fields, body = read_task(path)
    if field == "tags":
        fields["tags"] = [
            item.strip() for item in value.split(",") if item.strip()
        ]
    elif field == "parent":
        if fields.get("type") != "subtask":
            raise TasksError(
                "'parent' is only allowed on subtasks; use "
                "`new subtask --parent` to create one"
            )
        parent_path = resolve_id(artifacts_dir, value)
        _validate_parent_file(artifacts_dir, parent_path.name)
        fields["parent"] = parent_path.name
    elif field == "type":
        if value not in TYPES:
            raise TasksError(f"type must be one of: {', '.join(TYPES)}")
        if value != "subtask" and fields.get("parent"):
            raise TasksError(
                f"cannot set type to {value!r}: 'parent' is set and "
                "parent is forbidden on non-subtasks"
            )
        fields["type"] = value
        if value == "subtask":
            parent_name = fields.get("parent")
            if not parent_name:
                raise TasksError(
                    "subtask requires a parent; create it with "
                    "`new subtask --parent` instead"
                )
            _validate_parent_file(artifacts_dir, parent_name)
    elif field == "updated":
        _validate_date("updated", value)
        fields["updated"] = value
    elif field in ("title", "author", "reason"):
        if not value.strip():
            raise TasksError(f"{field} must be non-empty")
        fields[field] = value
    else:  # state / priority, validated against their enums
        valid = _FIELD_ENUMS[field]
        if value not in valid:
            raise TasksError(f"{field} must be one of: {', '.join(valid)}")
        fields[field] = value
    if field != "updated":
        fields["updated"] = _today()
    _warn_if_invalid_without_reason(fields)
    path.write_text(render_task(fields, body), encoding="utf-8")
    print(path)
    return 0


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

    p = sub.add_parser("init", help="create .tasks.yaml and the artifacts dir")
    _add_global(p)
    p.add_argument("--author", metavar="NAME")
    p.set_defaults(command="init", func=cmd_init)

    p = sub.add_parser("new", help="create a task/bug/subtask from a template")
    _add_global(p)
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
    p.add_argument("--reason")
    p.set_defaults(command="new", func=cmd_new)

    p = sub.add_parser("list", help="list tasks, one per line")
    _add_global(p)
    p.add_argument("--state", action="append")
    p.add_argument("--type", action="append")
    p.add_argument("--tag", action="append")
    p.add_argument("--author", action="append")
    p.set_defaults(command="list", func=cmd_list)

    p = sub.add_parser("show", help="print a task file verbatim")
    _add_global(p)
    p.add_argument("id")
    p.set_defaults(command="show", func=cmd_show)

    p = sub.add_parser("set-state", help="change a task's state")
    _add_global(p)
    p.add_argument("id")
    p.add_argument("state", choices=STATES)
    p.add_argument("--reason")
    p.set_defaults(command="set-state", func=cmd_set_state)

    p = sub.add_parser("set", help="edit a frontmatter field")
    _add_global(p)
    p.add_argument("id")
    p.add_argument("field")
    p.add_argument("value")
    p.set_defaults(command="set", func=cmd_set)

    stub("validate", "check tasks against the schema").add_argument(
        "id", nargs="*"
    )

    stub("links", "show outbound/inbound links").add_argument("id")

    stub("grep", "pass-through to rg over the artifacts dir").add_argument(
        "rg_args", nargs=argparse.REMAINDER
    )

    p = sub.add_parser("next-id", help="print the next task number")
    _add_global(p)
    p.set_defaults(command="next-id", func=cmd_next_id)
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
