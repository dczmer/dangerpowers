#!/usr/bin/env python3
"""tasks.py — zero-dependency markdown task tracker CLI.

Single file, Python 3 standard library only. Tasks live as flat markdown
files with YAML frontmatter in a project-local artifacts dir; this script
is the only writer of frontmatter.
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

# The config lives inside the default artifacts dir: tasks/tasks.yaml.
CONFIG_NAME = "tasks.yaml"
LEGACY_CONFIG_NAME = ".tasks.yaml"
DEFAULT_ARTIFACTS_DIR = "tasks"
MAX_TASK_NUMBER = 999
# The number is the durable identifier, so the slug gets a sane cap.
MAX_SLUG_LENGTH = 30

_TASK_FILE_RE = re.compile(r"^(\d{3})_[A-Za-z0-9\-_]+\.md$")

# Non-task entries allowed inside the artifacts dir: the installed CLI,
# the config, and the bundled templates dir. `validate` ignores them;
# ID resolution and grep never treat them as tasks.
NON_TASK_ENTRIES = ("tasks.py", "tasks.yaml", "templates")
_SLUG_RUN_RE = re.compile(r"[^a-z0-9\-_]+")
_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9\-_]*):(.*)$")
_ESCAPES = {"\\": "\\", '"': '"', "n": "\n", "t": "\t"}

# Canonical frontmatter key order: required fields first, then optionals.
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
# Flat YAML subset parser/emitter                                 #
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
    """Parse flat ``key: value`` pairs (flat YAML subset).

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
# Config discovery                                                #
# --------------------------------------------------------------------- #


@dataclass
class Config:
    """Resolved runtime configuration."""

    # tasks/tasks.yaml location; None when defaults are used
    path: Optional[Path]
    artifacts_dir: Path  # absolute
    author: Optional[str]  # from the config file only


def discover_config(
    config_flag: Optional[str],
    dir_flag: Optional[str],
    cwd: Path,
) -> Config:
    """Resolve config: flag → upward walk for .tasks.yaml → defaults."""
    cfg_path: Optional[Path] = None
    base = cwd
    if config_flag is not None:
        cfg_path = Path(config_flag)
        if not cfg_path.is_file():
            raise TasksError(f"config file not found: {cfg_path}")
        base = cfg_path.resolve().parent
    else:
        for directory in (cwd, *cwd.parents):
            candidate = directory / DEFAULT_ARTIFACTS_DIR / CONFIG_NAME
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
# Author resolution                                               #
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
    """Author chain: --author → config author → git config → $USER."""
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
# Slug + numbering                                                #
# --------------------------------------------------------------------- #


def slugify(title: str) -> str:
    """Lowercase slug, capped at MAX_SLUG_LENGTH chars.

    Runs outside [a-z0-9-_] collapse to one '-'; the cap may cut a run,
    and a trailing '-' left by truncation is stripped. The task number
    is the durable identifier, so a long title never yields a long name.
    """
    slug = _SLUG_RUN_RE.sub("-", title.lower()).strip("-")
    return slug[:MAX_SLUG_LENGTH].rstrip("-")


def task_numbers(artifacts_dir: Path) -> list:
    """Numbers of files matching NNN_slug.md; missing dir → empty."""
    if not artifacts_dir.is_dir():
        return []
    numbers = []
    for entry in artifacts_dir.iterdir():
        match = _TASK_FILE_RE.match(entry.name)
        if match is not None:
            numbers.append(int(match.group(1)))
    return numbers


def next_number(artifacts_dir: Path) -> int:
    """Max existing number + 1; gaps are never backfilled."""
    number = max(task_numbers(artifacts_dir), default=0) + 1
    if number > MAX_TASK_NUMBER:
        raise TasksError(
            f"task numbers exhausted (>999) in {artifacts_dir}; "
            "this project has outgrown the tool"
        )
    return number


# --------------------------------------------------------------------- #
# ID resolution                                                   #
# --------------------------------------------------------------------- #


def resolve_id(artifacts_dir: Path, arg: str) -> Path:
    """Resolve a task reference: exact filename, 3-digit number, or unique
    filename prefix. Ambiguous or unknown references raise TasksError."""
    if not artifacts_dir.is_dir():
        raise TasksError(
            f"artifacts dir not found: {artifacts_dir} "
            "(run './tasks/tasks.py init'?)"
        )
    direct = artifacts_dir / arg
    if direct.is_file() and direct.name not in NON_TASK_ENTRIES:
        return direct
    names = sorted(
        p.name
        for p in artifacts_dir.iterdir()
        if p.is_file() and p.name not in NON_TASK_ENTRIES
    )
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
# Task file IO: frontmatter + verbatim body                           #
# --------------------------------------------------------------------- #

STATES = ("draft", "open", "in-progress", "complete", "invalid")
TYPES = ("task", "bug", "subtask")
PARENT_TYPES = ("task", "bug")
PRIORITIES = ("low", "medium", "high")

# Shared by `new`, `set-state`, `set`, and `validate` so the warning
# wording matches across all paths.
WARNING_INVALID_NO_REASON = "state is 'invalid' but no reason given"

_FIELD_ENUMS = {"type": TYPES, "state": STATES, "priority": PRIORITIES}
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

# Link tokens are exact, uppercase, with a colon, at line start or after
# a markdown list bullet; targets are comma- or space-separated filenames.
LINK_TOKENS = ("RELATED TO", "DEPENDS ON", "DUPLICATES", "INVALIDATES")
_LINK_LINE_RE = re.compile(
    r"^\s*(?:[-*]\s+)?(RELATED TO|DEPENDS ON|DUPLICATES|INVALIDATES):(.*)$"
)


def _load_template(artifacts_dir: Path, kind: str):
    """Return ``(text, name)`` for a task template.

    Lookup chain: ``templates/`` inside the artifacts dir (installed
    layout), ``templates/`` bundled next to this script, then
    ``templates/`` next to the skill copy (when run from ``scripts/``).
    """
    candidates = (
        artifacts_dir / "templates" / f"{kind}.md",
        Path(__file__).resolve().parent / "templates" / f"{kind}.md",
        Path(__file__).resolve().parents[1] / "templates" / f"{kind}.md",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8"), candidate.name
    raise TasksError(
        f"template not found: {kind}.md (run './tasks/tasks.py init'?"
        " to install the templates)"
    )


def _today() -> str:
    """Local date, YYYY-MM-DD."""
    # Spec requires the *local* date; a tz-aware UTC date could differ near
    # midnight, so naive local is intentional here.
    return datetime.date.today().isoformat()  # noqa: DTZ011


def _warn(message: str) -> None:
    print(f"tasks.py: warning: {message}", file=sys.stderr)


def _is_date(value: object) -> bool:
    """True for real calendar dates in YYYY-MM-DD form (string only)."""
    if not isinstance(value, str) or _DATE_RE.fullmatch(value) is None:
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _validate_date(field: str, value: str) -> None:
    """Dates are YYYY-MM-DD and must be real calendar dates."""
    if _DATE_RE.fullmatch(value) is None:
        raise TasksError(f"{field} must be a date in YYYY-MM-DD form")
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        raise TasksError(f"{field} is not a valid date: {value}") from None


def scan_links(body: str) -> list:
    """Find link relationships in a task body.

    Returns ``[(token, [targets])]`` for each matching line; a trailing
    ``#`` comment on the line is ignored (filenames cannot contain it).
    """
    found = []
    for line in body.splitlines():
        match = _LINK_LINE_RE.match(line)
        if match is None:
            continue
        targets = []
        for token in re.split(r"[\s,]+", match.group(2).strip()):
            if not token or token.startswith("#"):
                break
            targets.append(token)
        found.append((match.group(1), targets))
    return found


def _validate_parent_file(artifacts_dir: Path, parent_name: str) -> None:
    """A parent must exist and be a task or bug, not a subtask."""
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
    """Read commands fail clearly when the artifacts dir is missing."""
    if not cfg.artifacts_dir.is_dir():
        raise TasksError(
            f"artifacts dir not found: {cfg.artifacts_dir} "
            "(run './tasks/tasks.py init'?)"
        )
    return cfg.artifacts_dir


# --------------------------------------------------------------------- #
# Commands                                                        #
# --------------------------------------------------------------------- #


def cmd_init(args: argparse.Namespace) -> int:
    """Create tasks/tasks.yaml and the artifacts dir; install the CLI
    script and templates next to the config. Idempotent: re-running
    installs missing files and updates any that differ.

    A legacy repo-root ``.tasks.yaml`` is moved into ``tasks/``.
    """
    if args.config:
        config_path = Path(args.config)
        root = config_path.resolve().parent
    else:
        root = args.cwd
        config_path = root / DEFAULT_ARTIFACTS_DIR / CONFIG_NAME
        _migrate_legacy_config(root, config_path)
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
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"created {config_path}")
    artifacts_dir = Path(artifacts_value)
    if not artifacts_dir.is_absolute():
        artifacts_dir = root / artifacts_dir
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    print(f"artifacts dir ready: {artifacts_dir}")
    install_dir = config_path.resolve().parent
    _install_tooling(install_dir)
    print(f"CLI ready: {install_dir / 'tasks.py'} -h")
    return 0


def _migrate_legacy_config(root: Path, config_path: Path) -> None:
    """Move a repo-root .tasks.yaml into tasks/tasks.yaml (one-time).

    When both files exist the legacy file is left in place untouched —
    deleting user data silently is worse than a leftover file.
    """
    legacy = root / LEGACY_CONFIG_NAME
    if not legacy.is_file():
        return
    if config_path.is_file():
        _warn(
            f"{LEGACY_CONFIG_NAME} still exists but {config_path} takes "
            "precedence; remove the legacy file by hand if it is stale"
        )
        return
    config_path.parent.mkdir(parents=True, exist_ok=True)
    legacy.replace(config_path)
    print(f"moved {legacy} -> {config_path}")


def _install_file(
    source: Path, target: Path, executable: bool = False
) -> None:
    """Copy ``source`` onto ``target`` when missing or different.

    Byte-identical targets are left untouched, so re-running ``init``
    is a cheap no-op. ``target`` may be the running script itself.
    """
    data = source.read_bytes()
    if target.is_file() and target.read_bytes() == data:
        print(f"{target.name}: up to date")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    if executable:
        target.chmod(0o755)
    print(f"installed {target}")


def _install_tooling(install_dir: Path) -> None:
    """Install (or update) the CLI script and templates in ``install_dir``.

    The templates source is the ``templates/`` dir bundled next to the
    running script — the installed copy's own dir when re-running from
    the installed location, the skill's dir otherwise.
    """
    script_source = Path(__file__).resolve()
    script_target = install_dir / "tasks.py"
    if script_target == script_source:
        # Running from the install location: the script is itself by
        # definition; nothing to copy.
        print(f"{script_target.name}: already the running script")
    else:
        _install_file(script_source, script_target, executable=True)
    templates_source = script_source.parent / "templates"
    if not templates_source.is_dir():
        # Skill layout: script lives in scripts/, templates one up.
        templates_source = script_source.parents[1] / "templates"
    templates_target = install_dir / "templates"
    for template in sorted(templates_source.glob("*.md")):
        _install_file(template, templates_target / template.name)


def cmd_new(args: argparse.Namespace) -> int:
    """Clone a template, fill frontmatter, assign the next number."""
    cfg = _load_config(args)
    artifacts_dir = cfg.artifacts_dir
    author = resolve_author(args.author, cfg.author, args.cwd)
    if args.parent and args.kind != "subtask":
        raise TasksError("--parent is only valid for subtask")
    # Create the artifacts dir up front so parent resolution can scan it.
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
    template, template_name = _load_template(artifacts_dir, args.kind)
    filled = (
        template.replace("{{title}}", args.title)
        .replace("{{author}}", author)
        .replace("{{date}}", _today())
        .replace("{{parent}}", parent_name or "")
    )
    fields, body = parse_task(filled, template_name)
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
        if len(slug) > MAX_SLUG_LENGTH:
            raise TasksError(
                f"slug is {len(slug)} characters; the maximum is "
                f"{MAX_SLUG_LENGTH}. The task number is the durable "
                "identifier — pick a shorter slug."
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
    """One line per task: `ID  state  type  title`.

    Unparseable files are skipped with a stderr warning so one corrupt
    file cannot take down the survey of the whole corpus.
    """
    artifacts_dir = _require_artifacts_dir(_load_config(args))
    rows = []
    for path in sorted(artifacts_dir.iterdir()):
        match = _TASK_FILE_RE.match(path.name)
        if match is None:
            continue
        try:
            fields, _ = read_task(path)
        except TasksError as exc:
            _warn(f"skipping {path.name}: {exc}")
            continue
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
    """Print the task file verbatim."""
    cfg = _load_config(args)
    path = resolve_id(cfg.artifacts_dir, args.id)
    sys.stdout.write(path.read_text(encoding="utf-8"))
    return 0


def cmd_next_id(args: argparse.Namespace) -> int:
    """Print the next task number, e.g. `017`."""
    artifacts_dir = _require_artifacts_dir(_load_config(args))
    print(f"{next_number(artifacts_dir):03d}")
    return 0


def cmd_set_state(args: argparse.Namespace) -> int:
    """Change a task's state (any→any, no workflow enforcement); the
    ``reason`` field is set when given; ``updated`` is refreshed."""
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
    is settable, each with per-field validation.
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


def _validate_file(path: Path, artifacts_dir: Path) -> list:
    """Check one file against the schema; returns ``[(level, message)]``
    where level is ``"error"`` or ``"warning"``. Never raises for file
    content problems; parse failures become errors."""
    name = path.name
    issues = []
    if _TASK_FILE_RE.match(name) is None:
        issues.append(
            ("error", f"{name}: filename does not match NNN_slug.md")
        )
        return issues
    try:
        fields, body = read_task(path)
    except TasksError as exc:
        issues.append(("error", f"{name}: {exc}"))
        return issues
    issues.extend(_field_issues(name, fields, artifacts_dir))
    for token, targets in scan_links(body):
        for target in targets:
            if not (artifacts_dir / target).is_file():
                issues.append(("error", f"{name}: dangling {token}: {target}"))
    return issues


def _field_issues(name: str, fields: dict, artifacts_dir: Path) -> list:
    """Schema checks for one parsed frontmatter."""
    issues = []

    def err(message: str) -> None:
        issues.append(("error", f"{name}: {message}"))

    def warn(message: str) -> None:
        issues.append(("warning", f"{name}: {message}"))

    for field in ("title", "type", "state", "author", "created", "updated"):
        if field not in fields:
            err(f"missing required field '{field}'")
    for field in ("title", "author"):
        if field in fields and (
            not isinstance(fields[field], str) or not fields[field].strip()
        ):
            err(f"{field} must be a non-empty string")
    for field, valid in _FIELD_ENUMS.items():
        value = fields.get(field)
        if field in fields and (
            not isinstance(value, str) or value not in valid
        ):
            err(f"{field} {value!r} is not one of: {', '.join(valid)}")
    for field in ("created", "updated"):
        if field in fields and not _is_date(fields[field]):
            err(f"{field} must be a date in YYYY-MM-DD form")

    type_value = fields.get("type")
    parent = fields.get("parent")
    if type_value == "subtask":
        if not isinstance(parent, str) or not parent:
            err("subtask is missing required field 'parent'")
        else:
            parent_path = artifacts_dir / parent
            if not parent_path.is_file():
                err(f"parent file not found: {parent}")
            else:
                try:
                    parent_fields, _ = read_task(parent_path)
                except TasksError as exc:
                    err(f"parent {parent}: {exc}")
                else:
                    if parent_fields.get("type") not in PARENT_TYPES:
                        err(
                            f"parent {parent} has type "
                            f"{parent_fields.get('type')!r}; parents must "
                            "be task or bug"
                        )
    elif parent:
        err(
            f"'parent' is forbidden on non-subtask "
            f"(type is {type_value!r})"
        )

    if fields.get("state") == "invalid" and not fields.get("reason"):
        warn(WARNING_INVALID_NO_REASON)
    reason = fields.get("reason")
    if reason is not None and (
        not isinstance(reason, str) or not reason.strip()
    ):
        err("reason must be a non-empty string")
    tags = fields.get("tags")
    if tags is not None:
        if not isinstance(tags, list):
            err("tags must be an inline list, e.g. [cli, auth]")
        elif any(not isinstance(item, str) or not item for item in tags):
            err("tags items must be non-empty strings")
    for key in sorted(k for k in fields if k not in CANONICAL_ORDER):
        warn(f"unknown frontmatter key '{key}'")
    return issues


def cmd_validate(args: argparse.Namespace) -> int:
    """Run every schema check on the given tasks (or all of them).

    Errors exit 2; warnings-only still exits 0, with all issues listed on
    stdout as ``error: <file>: ...`` / ``warning: <file>: ...`` lines.
    Any file in the artifacts dir not matching ``NNN_slug.md`` is an
    error, except the installed tooling (``tasks.py``, ``tasks.yaml``,
    and the ``templates/`` dir), which is ignored.
    """
    cfg = _load_config(args)
    if args.id:
        paths = [resolve_id(cfg.artifacts_dir, arg) for arg in args.id]
        artifacts_dir = cfg.artifacts_dir
    else:
        artifacts_dir = _require_artifacts_dir(cfg)
        paths = sorted(
            p
            for p in artifacts_dir.iterdir()
            if p.is_file() and p.name not in NON_TASK_ENTRIES
        )
    issues = []
    for path in paths:
        issues.extend(_validate_file(path, artifacts_dir))
    for level, message in issues:
        print(f"{level}: {message}")
    return 2 if any(level == "error" for level, _ in issues) else 0


def cmd_links(args: argparse.Namespace) -> int:
    """Print outbound and inbound link relationships for a task.
    Dangling targets are flagged but do not change the exit code."""
    artifacts_dir = _require_artifacts_dir(_load_config(args))
    path = resolve_id(artifacts_dir, args.id)
    _, body = read_task(path)
    name = path.name
    print(name)
    print("outbound:")
    outbound = scan_links(body)
    if not outbound:
        print("  (none)")
    for token, targets in outbound:
        for target in targets:
            if (artifacts_dir / target).is_file():
                dangling = ""
            else:
                dangling = " (dangling)"
            print(f"  {token}: {target}{dangling}")
    print("inbound:")
    inbound = []
    for other in sorted(artifacts_dir.iterdir()):
        if other.name == name or _TASK_FILE_RE.match(other.name) is None:
            continue
        try:
            _, other_body = read_task(other)
        except TasksError:
            continue
        for token, targets in scan_links(other_body):
            if name in targets:
                inbound.append((other.name, token))
    if not inbound:
        print("  (none)")
    for source, token in inbound:
        print(f"  {source} ({token})")
    return 0


def cmd_grep(args: argparse.Namespace) -> int:
    """Pass-through: ``rg <args> <artifacts_dir>``; exit code propagated.

    The installed tooling (tasks.py, tasks.yaml, templates/) is excluded
    so hits are always task content.
    """
    artifacts_dir = _require_artifacts_dir(_load_config(args))
    excludes = [
        "--glob",
        "!tasks.py",
        "--glob",
        "!tasks.yaml",
        "--glob",
        "!templates",
    ]
    try:
        proc = subprocess.run(
            ["rg", *excludes, *args.rg_args, str(artifacts_dir)], check=False
        )
    except FileNotFoundError:
        raise TasksError(
            "rg (ripgrep) not found in PATH; install it to use grep"
        ) from None
    return proc.returncode


class _Parser(argparse.ArgumentParser):
    """ArgumentParser that exits 1 (not 2) on usage errors."""

    def error(self, message: str) -> NoReturn:
        self.exit(1, f"{self.prog}: error: {message}\n")


def _add_global(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        metavar="PATH",
        help=(
            "path to the config file (default: walk upward from cwd for "
            f"{DEFAULT_ARTIFACTS_DIR}/{CONFIG_NAME})"
        ),
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

    p = sub.add_parser(
        "init",
        help=(
            "create the config, artifacts dir, and install the CLI + "
            "templates into tasks/"
        ),
    )
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

    p = sub.add_parser("validate", help="check tasks against the schema")
    _add_global(p)
    p.add_argument("id", nargs="*")
    p.set_defaults(command="validate", func=cmd_validate)

    p = sub.add_parser("links", help="show outbound/inbound links")
    _add_global(p)
    p.add_argument("id")
    p.set_defaults(command="links", func=cmd_links)

    # `grep` takes no parsed flags: everything after the subcommand is
    # passed to rg verbatim (see _split_grep_argv).
    p = sub.add_parser(
        "grep", help="pass-through to rg over the artifacts dir"
    )
    p.set_defaults(command="grep", func=cmd_grep)

    p = sub.add_parser("next-id", help="print the next task number")
    _add_global(p)
    p.set_defaults(command="next-id", func=cmd_next_id)
    return parser


def _split_grep_argv(argv: list) -> tuple:
    """Split argv into (parseable prefix, grep tail).

    Everything after the ``grep`` subcommand is passed to rg verbatim,
    including tokens that look like options, so argparse never sees them.
    Global flags and their values before the subcommand stay parseable.
    """
    prefix = []
    i = 0
    while i < len(argv):
        token = argv[i]
        prefix.append(token)
        if token == "grep":
            return prefix, argv[i + 1 :]
        if token in ("--config", "--dir") and i + 1 < len(argv):
            prefix.append(argv[i + 1])
            i += 2
            continue
        i += 1
    return prefix, []


def main(
    argv: Optional[list] = None,
    cwd: Optional[Union[str, Path]] = None,
) -> int:
    root = Path(cwd) if cwd is not None else Path.cwd()
    root = root.resolve()
    raw = [str(a) for a in argv] if argv is not None else sys.argv[1:]
    parse_argv, grep_tail = _split_grep_argv(raw)
    if grep_tail == ["-h"]:
        # Standard CLI help, not rg's own -h.
        parse_argv.append("-h")
        grep_tail = []
    parser = build_parser()
    args = parser.parse_args(parse_argv)
    if not hasattr(args, "func"):
        parser.print_usage(sys.stderr)
        return 1
    args.cwd = root
    if args.command == "grep":
        args.rg_args = grep_tail
    try:
        return int(args.func(args) or 0)
    except TasksError as exc:
        print(f"tasks.py: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
