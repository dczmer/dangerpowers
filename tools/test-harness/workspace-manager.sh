#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage:
  workspace-manager.sh init [--prefix NAME]
  workspace-manager.sh campaign-init --root DIR
  workspace-manager.sh sync --skill NAME --source DIR --workspace DIR [--full]
      [--dest-root DIR]
  workspace-manager.sh status --skill NAME --source DIR --workspace DIR [--full]
      [--dest-root DIR]
  workspace-manager.sh cleanup --workspace DIR [--prefix NAME]

init    creates one campaign workspace under /tmp/<prefix>.XXXXXXXXXX
        (default prefix: trigger-test) and prints its path on stdout.
        Pre-creates both .agents/skills (opencode/pi) and .claude/skills
        (claude) so --dest-root can point sync/status at either.
campaign-init creates one persistent campaign directory under --root, named
        campaign-YYYY-MM-DD (suffixed -2, -3, ... on same-day reruns), and
        prints its path on stdout.
sync    copies the source skill to the target workspace. Default: frontmatter
        stub only (trigger track). --full copies the entire skill directory
        (retrieval track), excluding __pycache__/ and *.pyc and rejecting
        unsafe symlinks. Run after every description change to sync the stub.
        --dest-root DIR: workspace-relative skill directory (default:
        .agents/skills; use .claude/skills for the claude harness).
status  verifies the workspace is in a valid state and that the synced skill
        matches the current source. Default: frontmatter comparison.
        --full: recursive diff with the same exclusions as sync --full;
        exit 1 on any difference. --dest-root DIR: same meaning as sync's.
cleanup removes the workspace; refuses paths outside /tmp/<prefix>.*
        (default prefix: trigger-test).
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
  local prefix="trigger-test"
  while [ $# -gt 0 ]; do
    case "$1" in
      --prefix) prefix="$2"; shift 2 ;;
      *) echo "error: unknown init argument: $1" >&2; exit 1 ;;
    esac
  done
  case "$prefix" in
    *[!A-Za-z0-9._-]* | "")
      echo "error: unsafe --prefix: '$prefix'" >&2; exit 1 ;;
  esac
  local ws
  ws="$(mktemp -d "/tmp/${prefix}.XXXXXXXXXX")"
  mkdir -p "$ws/.agents/skills" "$ws/.claude/skills"
  printf '%s\n' "$ws"
}

cmd_campaign_init() {
  local root=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --root) root="$2"; shift 2 ;;
      *) usage ;;
    esac
  done
  [ -n "$root" ] || { echo "error: --root DIR is required" >&2; usage; }
  local datestamp base dir n
  datestamp="$(date +%F)"
  base="$root/campaign-$datestamp"
  dir="$base"
  n=2
  while [ -e "$dir" ]; do
    dir="$base-$n"
    n=$((n + 1))
  done
  mkdir -p "$dir"
  echo "$dir"
}

cmd_sync() {
  local skill="" ws="" source="" full=0 dest_root=".agents/skills"
  while [ $# -gt 0 ]; do
    case "$1" in
      --skill) skill="$2"; shift 2 ;;
      --workspace) ws="$2"; shift 2 ;;
      --source) source="$2"; shift 2 ;;
      --full) full=1; shift ;;
      --dest-root) dest_root="$2"; shift 2 ;;
      *) usage ;;
    esac
  done
  [ -n "$skill" ] || { echo "error: --skill NAME is required" >&2; usage; }
  [ -n "$source" ] || { echo "error: --source DIR is required" >&2; usage; }
  [ -n "$ws" ] || { echo "error: --workspace DIR is required" >&2; usage; }
  local src="$source/skills/$skill/SKILL.md"
  [ -f "$src" ] || { echo "error: missing SKILL.md: $src" >&2; exit 1; }
  local skill_dir="$source/skills/$skill"
  local dest="$ws/$dest_root/$skill"
  if [ "$full" -eq 1 ]; then
    # Symlink policy — the dir hasher (evaluator.py record --scope dir)
    # applies the SAME policy so both agree on the file set:
    #   escaping symlink  -> reject
    #   symlink to a dir  -> reject (keeps walk/diff/hash consistent)
    #   symlink to a file -> allowed (hasher reads through it)
    local link target
    while IFS= read -r link; do
      target="$(realpath -m "$link")"
      case "$target" in
        "$skill_dir"/*) ;;
        *) echo "error: symlink escapes skill dir: $link -> $target" >&2
           exit 1 ;;
      esac
      [ -d "$target" ] && {
        echo "error: symlink to a directory: $link" >&2; exit 1; }
    done < <(find "$skill_dir" -type l)
    rm -rf "$dest"
    mkdir -p "$dest"
    tar -cf - --exclude='__pycache__' --exclude='*.pyc' \
        -C "$skill_dir" . | tar -xf - -C "$dest"
  else
    mkdir -p "$dest"
    if ! extract_frontmatter "$src" > "$dest/SKILL.md"; then
      echo "error: missing or unterminated frontmatter in $src" >&2; exit 1
    fi
  fi
  grep -q "^name: $skill\$" "$dest/SKILL.md" \
    || { echo "error: frontmatter name does not match directory in $src" >&2; exit 1; }
  echo "synced: $skill"
}

cmd_status() {
  local skill="" ws="" source="" full=0 dest_root=".agents/skills"
  while [ $# -gt 0 ]; do
    case "$1" in
      --skill) skill="$2"; shift 2 ;;
      --workspace) ws="$2"; shift 2 ;;
      --source) source="$2"; shift 2 ;;
      --full) full=1; shift ;;
      --dest-root) dest_root="$2"; shift 2 ;;
      *) usage ;;
    esac
  done
  [ -n "$skill" ] || { echo "error: --skill NAME is required" >&2; usage; }
  [ -n "$source" ] || { echo "error: --source DIR is required" >&2; usage; }
  [ -n "$ws" ] || { echo "error: --workspace DIR is required" >&2; usage; }
  [ -d "$ws/$dest_root" ] || { echo "error: workspace is not initialized: $ws" >&2; exit 1; }
  local src="$source/skills/$skill/SKILL.md"
  local dest="$ws/$dest_root/$skill"
  local stub="$dest/SKILL.md"
  [ -f "$src" ] || { echo "error: missing SKILL.md: $src" >&2; exit 1; }
  [ -f "$stub" ] || { echo "error: skill stub not synced: $stub" >&2; exit 1; }
  local skill_dir="$source/skills/$skill"
  if [ "$full" -eq 1 ]; then
    if diff -r --exclude='__pycache__' --exclude='*.pyc' \
         "$skill_dir" "$dest" > /dev/null 2>&1; then
      echo "ok: $skill full dir matches source"; exit 0
    fi
    echo "error: $skill full dir differs from source:" >&2
    diff -r --exclude='__pycache__' --exclude='*.pyc' \
         "$skill_dir" "$dest" >&2
    exit 1
  fi
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
  local ws="" prefix="trigger-test"
  while [ $# -gt 0 ]; do
    case "$1" in
      --workspace) ws="$2"; shift 2 ;;
      --prefix) prefix="$2"; shift 2 ;;
      *) echo "error: unknown cleanup argument: $1" >&2; exit 1 ;;
    esac
  done
  [ -n "$ws" ] || { echo "error: --workspace DIR is required" >&2; usage; }
  case "$ws" in
    /tmp/"$prefix".*) rm -rf -- "$ws" ;;
    *) echo "error: refusing to remove path outside /tmp/$prefix.*: $ws" >&2
       exit 1 ;;
  esac
}

[ $# -ge 1 ] || usage
cmd="$1"; shift
case "$cmd" in
  init) cmd_init "$@" ;;
  campaign-init) cmd_campaign_init "$@" ;;
  sync) cmd_sync "$@" ;;
  status) cmd_status "$@" ;;
  cleanup) cmd_cleanup "$@" ;;
  *) usage ;;
esac
