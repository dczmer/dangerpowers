#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage:
  trigger-test.sh init [--source DIR]
  trigger-test.sh eval --skill NAME [--workspace DIR] [--model PROVIDER/MODEL] [--scenario-file PATH] [SCENARIO_TEXT]
  trigger-test.sh sync --skill NAME [--workspace DIR] [--source DIR]
  trigger-test.sh cleanup [--workspace DIR]

init    creates one campaign workspace and prints its path on stdout:
        frontmatter-only stubs of every skills/<name>/SKILL.md under SOURCE
        go to WORKSPACE/.agents/skills/<name>/SKILL.md, and
        SOURCE/agents/trigger-evaluator.md is copied to
        WORKSPACE/.opencode/agents/. SOURCE defaults to the repository
        root containing this script.
eval    runs one scenario in the workspace and prints a verdict block:
          verdict: loaded | not-loaded
          target: <skill>
          loaded_skills: <comma-separated names, or none>
          conflict: none | wrong-skill | additional-skills
          conflict_skills: <comma-separated names, or none>
        The workspace comes from --workspace or $TRIGGER_TEST_WORKSPACE.
sync    re-extracts the frontmatter of skills/NAME/SKILL.md (from --source,
        defaulting to the repository root) into the workspace stub, so evals
        measure the description just revised. Run after every description
        edit; the workspace stub is an init-time snapshot and does not track
        the real SKILL.md. Workspace comes from --workspace or
        $TRIGGER_TEST_WORKSPACE.
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
  local source=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --source) source="$2"; shift 2 ;;
      *) usage ;;
    esac
  done
  if [ -z "$source" ]; then
    source="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
  fi
  [ -d "$source/skills" ] || { echo "error: no skills/ directory under source: $source" >&2; exit 1; }
  [ -f "$source/agents/trigger-evaluator.md" ] || { echo "error: missing agent definition: $source/agents/trigger-evaluator.md" >&2; exit 1; }

  local ws
  ws="$(mktemp -d /tmp/trigger-test.XXXXXXXXXX)"
  mkdir -p "$ws/.agents/skills" "$ws/.opencode/agents"

  local count=0 skill_dir name src
  for skill_dir in "$source"/skills/*/; do
    src="$skill_dir/SKILL.md"
    [ -f "$src" ] || { echo "error: missing SKILL.md in $skill_dir" >&2; exit 1; }
    name="$(basename "$skill_dir")"
    mkdir -p "$ws/.agents/skills/$name"
    if ! extract_frontmatter "$src" > "$ws/.agents/skills/$name/SKILL.md"; then
      echo "error: missing or unterminated frontmatter in $src" >&2; exit 1
    fi
    grep -q "^name: $name\$" "$ws/.agents/skills/$name/SKILL.md" \
      || { echo "error: frontmatter name does not match directory in $src" >&2; exit 1; }
    count=$((count + 1))
  done
  [ "$count" -gt 0 ] || { echo "error: no skills found under $source/skills" >&2; exit 1; }

  cp "$source/agents/trigger-evaluator.md" "$ws/.opencode/agents/trigger-evaluator.md"
  echo "$ws"
}

cmd_eval() {
  local skill="" ws="" model="" scenario_file="" scenario=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --skill) skill="$2"; shift 2 ;;
      --workspace) ws="$2"; shift 2 ;;
      --model) model="$2"; shift 2 ;;
      --scenario-file) scenario_file="$2"; shift 2 ;;
      -*) usage ;;
      *) scenario="$1"; shift ;;
    esac
  done
  [ -n "$skill" ] || { echo "error: --skill NAME is required" >&2; usage; }
  ws="${ws:-${TRIGGER_TEST_WORKSPACE:-}}"
  [ -n "$ws" ] && [ -d "$ws/.agents/skills/$skill" ] \
    || { echo "error: workspace unset or has no stub for skill '$skill': ${ws:-<unset>}" >&2; exit 1; }

  if [ -n "$scenario_file" ]; then
    local real_ws real_file
    real_ws="$(realpath "$ws")"
    real_file="$(realpath "$scenario_file")"
    case "$real_file" in
      "$real_ws"/*) ;;
      *) echo "error: scenario file must reside inside the workspace: $scenario_file" >&2; exit 1 ;;
    esac
    scenario="$(cat -- "$scenario_file")"
  fi
  [ -n "$scenario" ] || { echo "error: no scenario text provided" >&2; usage; }

  local model_args=()
  [ -n "$model" ] && model_args=(--model "$model")

  local out="$ws/.trigger-test-last-run.jsonl"
  local rc=0
  timeout 300 opencode run --dir "$ws" --agent trigger-evaluator --format json \
    ${model_args[@]+"${model_args[@]}"} "$scenario" > "$out" 2>&1 || rc=$?

  local loaded
  loaded="$(jq -R 'fromjson? // empty' "$out" | jq -s '
    [ .[] | .. | objects
      | select(.type? == "tool_use")
      | select((.tool? // .part?.tool?) == "skill")
      | (.state?.input?.name // .part?.state?.input?.name)
      | strings ]
    + [ .[] | .. | objects
      | select(.type? == "text")
      | (.text? // .part?.text?)
      | strings
      | select(startswith("Skill loaded: "))
      | ltrimstr("Skill loaded: ") ]
    | unique
  ')"

  local target_loaded others verdict conflict loaded_csv
  target_loaded="$(jq -r --arg s "$skill" 'if index($s) then "yes" else "no" end' <<<"$loaded")"
  others="$(jq -r --arg s "$skill" '[.[] | select(. != $s)] | join(",")' <<<"$loaded")"
  loaded_csv="$(jq -r 'if length == 0 then "none" else join(",") end' <<<"$loaded")"

  if [ "$target_loaded" = "yes" ]; then
    verdict="loaded"
    if [ -n "$others" ]; then conflict="additional-skills"; else conflict="none"; fi
  else
    verdict="not-loaded"
    if [ -n "$others" ]; then conflict="wrong-skill"; else conflict="none"; fi
  fi

  printf 'verdict: %s\ntarget: %s\nloaded_skills: %s\nconflict: %s\nconflict_skills: %s\nexit_code: %s\n' \
    "$verdict" "$skill" "$loaded_csv" "$conflict" "${others:-none}" "$rc"
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
  ws="${ws:-${TRIGGER_TEST_WORKSPACE:-}}"
  [ -n "$ws" ] && [ -d "$ws/.agents/skills/$skill" ] \
    || { echo "error: workspace unset or has no stub for skill '$skill': ${ws:-<unset>}" >&2; exit 1; }
  if [ -z "$source" ]; then
    source="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
  fi
  local src="$source/skills/$skill/SKILL.md"
  [ -f "$src" ] || { echo "error: missing SKILL.md: $src" >&2; exit 1; }
  if ! extract_frontmatter "$src" > "$ws/.agents/skills/$skill/SKILL.md"; then
    echo "error: missing or unterminated frontmatter in $src" >&2; exit 1
  fi
  grep -q "^name: $skill\$" "$ws/.agents/skills/$skill/SKILL.md" \
    || { echo "error: frontmatter name does not match directory in $src" >&2; exit 1; }
  echo "synced: $skill"
}

cmd_cleanup() {
  local ws=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --workspace) ws="$2"; shift 2 ;;
      *) usage ;;
    esac
  done
  ws="${ws:-${TRIGGER_TEST_WORKSPACE:-}}"
  [ -n "$ws" ] || { echo "error: no workspace given" >&2; exit 1; }
  case "$ws" in
    /tmp/trigger-test.*) rm -rf -- "$ws" ;;
    *) echo "error: refusing to remove non-trigger-test path: $ws" >&2; exit 1 ;;
  esac
}

[ $# -ge 1 ] || usage
cmd="$1"; shift
case "$cmd" in
  init) cmd_init "$@" ;;
  eval) cmd_eval "$@" ;;
  sync) cmd_sync "$@" ;;
  cleanup) cmd_cleanup "$@" ;;
  *) usage ;;
esac
