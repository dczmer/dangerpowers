#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage:
  trigger-test.sh init
  trigger-test.sh sync --skill NAME --source DIR --workspace DIR
  trigger-test.sh status --skll NAME --source DIR --workspace DIR
  trigger-test.sh cleanup --workspace DIR

init    creates one campaign workspace and prints its path on stdout.
sync    copys the source skill (front-matter only) to the target workspace,
        along with any other required resources for the campaign.
        run after every description change to sync the stub file.
status  provides an easy way to verify the workspace is in a a valid state
        and that the skill stub file matches the current version of the real
        skill description.
cleanup removes the workspace (--workspace or $TRIGGER_TEST_WORKSPACE).
EOF
  exit 1
}

extract_frontmatter() {
  awk '
    NR==1 { if ($0 != "---") exit 1; print; next }
    { print; if ($0 == "---") { found=1; exit } }
    END { if (!found) exit 1 }
  ' "$1"
}

cmd_init() {
  local ws
  ws="$(mktemp -d /tmp/trigger-test.XXXXXXXXXX)"
  mkdir -p "$ws/.agents/"{skills,agents}
  echo "$ws"
}

cmd_sync() {
  local skill="" ws="" source=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --skill) skill="$2"; shift 2 ;;
      --workspace) ws="$2"; shift 2 ;;
      --source) source="$2"; shift 2 ;;
      *) usage ;;
    esac
  done
  [ -n "$skill" ] || { echo "error: --skill NAME is required" >&2; usage; }
  [ -n "$source" ] || { echo "error: --source DIR is required" >&2; usage; }
  [ -n "$ws" ] || { echo "error: --workspace DIR is required" >&2; usage; }
  local src="$source/skills/$skill/SKILL.md"
  [ -f "$src" ] || { echo "error: missing SKILL.md: $src" >&2; exit 1; }
  mkdir -p "$ws/.agents/skills/$skill"
  if ! extract_frontmatter "$src" > "$ws/.agents/skills/$skill/SKILL.md"; then
    echo "error: missing or unterminated frontmatter in $src" >&2; exit 1
  fi
  grep -q "^name: $skill\$" "$ws/.agents/skills/$skill/SKILL.md" \
    || { echo "error: frontmatter name does not match directory in $src" >&2; exit 1; }
  echo "synced: $skill"
}

cmd_status() {
  local skill="" ws="" source=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --skill) skill="$2"; shift 2 ;;
      --workspace) ws="$2"; shift 2 ;;
      --source) source="$2"; shift 2 ;;
      *) usage ;;
    esac
  done
  [ -n "$skill" ] || { echo "error: --skill NAME is required" >&2; usage; }
  [ -n "$source" ] || { echo "error: --source DIR is required" >&2; usage; }
  [ -n "$ws" ] || { echo "error: --workspace DIR is required" >&2; usage; }
  [ -d "$ws/.agents/skills" ] || { echo "error: workspace is not initialized: $ws" >&2; exit 1; }
  local src="$source/skills/$skill/SKILL.md"
  local stub="$ws/.agents/skills/$skill/SKILL.md"
  [ -f "$src" ] || { echo "error: missing SKILL.md: $src" >&2; exit 1; }
  [ -f "$stub" ] || { echo "error: skill stub not synced: $stub" >&2; exit 1; }
  local current
  if ! current="$(extract_frontmatter "$src")"; then
    echo "error: missing or unterminated frontmatter in $src" >&2; exit 1
  fi
  if [ "$current" = "$(cat "$stub")" ]; then
    echo "ok: $skill stub matches source"
  else
    echo "error: $skill stub is out of date; run sync" >&2
    diff <(printf '%s\n' "$current") "$stub" >&2 || true
    exit 1
  fi
}

cmd_cleanup() {
  local ws=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --workspace) ws="$2"; shift 2 ;;
      *) usage ;;
    esac
  done
  [ -n "$ws" ] || { echo "error: --workspace DIR is required" >&2; usage; }
  case "$ws" in
    /tmp/trigger-test.*) rm -rf -- "$ws" ;;
    *) echo "error: refusing to remove non-trigger-test path: $ws" >&2; exit 1 ;;
  esac
}

[ $# -ge 1 ] || usage
cmd="$1"; shift
case "$cmd" in
  init) cmd_init "$@" ;;
  sync) cmd_sync "$@" ;;
  status) cmd_status "$@" ;;
  cleanup) cmd_cleanup "$@" ;;
  *) usage ;;
esac
