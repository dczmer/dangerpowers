#!/usr/bin/env bash

SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/trigger-test.sh"

setUp() {
  FIXTURE="$(mktemp -d /tmp/trigger-test-suite.XXXXXXXXXX)"
  SRC="$FIXTURE/source"
  mkdir -p "$SRC/skills/alpha" "$SRC/skills/beta" "$SRC/agents"
  cat > "$SRC/skills/alpha/SKILL.md" <<'EOF'
---
name: alpha
description: Alpha skill stub.
---

Alpha body text that must not reach the stub.
EOF
  cat > "$SRC/skills/beta/SKILL.md" <<'EOF'
---
name: beta
description: Beta skill stub.
---

Beta body text.
EOF
  printf -- '---\nname: trigger-evaluator\n---\nstub agent\n' > "$SRC/agents/trigger-evaluator.md"
  WS="$("$SCRIPT" init --source "$SRC")"
  BINDIR="$FIXTURE/bin"
  mkdir -p "$BINDIR"
  SCEN="$FIXTURE/scenarios.txt"
}

tearDown() {
  if [ -n "${WS:-}" ] && [ -d "${WS:-/nonexistent}" ]; then
    "$SCRIPT" cleanup --workspace "$WS" > /dev/null 2>&1 || true
  fi
  rm -rf "$FIXTURE"
}

write_load_stub() {
  cat > "$BINDIR/opencode" <<EOF
#!/usr/bin/env bash
printf '%s\n' '{"type":"tool_use","tool":"skill","state":{"input":{"name":"$1"}}}'
EOF
  chmod +x "$BINDIR/opencode"
}

write_noload_stub() {
  cat > "$BINDIR/opencode" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' '{"type":"text","text":"no skills apply here"}'
EOF
  chmod +x "$BINDIR/opencode"
}

write_hang_stub() {
  cat > "$BINDIR/opencode" <<'EOF'
#!/usr/bin/env bash
sleep 999
EOF
  chmod +x "$BINDIR/opencode"
}

write_conditional_hang_stub() {
  cat > "$BINDIR/opencode" <<EOF
#!/usr/bin/env bash
echo "\$*" >> "$FIXTURE/invocations.log"
case "\$*" in
  *HANGME*) exec sleep 999 ;;
esac
printf '%s\n' '{"type":"text","text":"no skills apply here"}'
EOF
  chmod +x "$BINDIR/opencode"
}

write_counting_stub() {
  mkdir -p "$FIXTURE/concurrency"
  cat > "$BINDIR/opencode" <<EOF
#!/usr/bin/env bash
set -u
dir="$FIXTURE/concurrency"
until mkdir "\$dir/lock" 2>/dev/null; do sleep 0.02; done
cur="\$(cat "\$dir/cur" 2>/dev/null || echo 0)"
cur=\$((cur + 1))
echo "\$cur" > "\$dir/cur"
max="\$(cat "\$dir/max" 2>/dev/null || echo 0)"
[ "\$cur" -gt "\$max" ] && echo "\$cur" > "\$dir/max"
rmdir "\$dir/lock"
sleep 0.3
until mkdir "\$dir/lock" 2>/dev/null; do sleep 0.02; done
cur="\$(cat "\$dir/cur")"
echo \$((cur - 1)) > "\$dir/cur"
rmdir "\$dir/lock"
printf '%s\n' '{"type":"text","text":"no skills apply here"}'
EOF
  chmod +x "$BINDIR/opencode"
}

test_frontmatter_extraction_stops_at_closing_marker() {
  local expected
  expected="$(printf -- '---\nname: alpha\ndescription: Alpha skill stub.\n---')"
  assertEquals "stub holds frontmatter only" \
    "$expected" "$(cat "$WS/.agents/skills/alpha/SKILL.md")"
}

test_init_rejects_unterminated_frontmatter() {
  printf -- '---\nname: beta\ndescription: no closing marker\n' > "$SRC/skills/beta/SKILL.md"
  local out rc=0
  out="$("$SCRIPT" init --source "$SRC" 2>&1)" || rc=$?
  assertEquals "init exits 1" 1 "$rc"
  assertContains "$out" "frontmatter"
  local d
  for d in /tmp/trigger-test.*; do
    [ -f "$d/.opencode/agents/trigger-evaluator.md" ] || rm -rf "$d"
  done
}

test_unknown_subcommand_fails() {
  local out rc=0
  out="$("$SCRIPT" frobnicate 2>&1)" || rc=$?
  assertNotEquals "unknown subcommand exits non-zero" 0 "$rc"
}

test_eval_requires_skill() {
  local out rc=0
  out="$("$SCRIPT" eval --workspace "$WS" "some query" 2>&1)" || rc=$?
  assertNotEquals "eval without --skill exits non-zero" 0 "$rc"
  assertContains "$out" "--skill"
}

test_status_in_sync() {
  local out rc=0
  out="$("$SCRIPT" status --skill alpha --workspace "$WS" --source "$SRC" 2>&1)" || rc=$?
  assertEquals "in-sync exits 0" 0 "$rc"
  assertContains "$out" "in-sync: alpha"
}

test_status_stale() {
  sed -i 's/description: Alpha skill stub\./description: Alpha skill stub, edited./' \
    "$SRC/skills/alpha/SKILL.md"
  local out rc=0
  out="$("$SCRIPT" status --skill alpha --workspace "$WS" --source "$SRC" 2>&1)" || rc=$?
  assertEquals "stale exits 1" 1 "$rc"
  assertContains "$out" "stale: alpha"
}

test_eval_load_verdict() {
  write_load_stub alpha
  local out rc=0
  out="$(PATH="$BINDIR:$PATH" "$SCRIPT" eval --skill alpha --workspace "$WS" \
    --timeout 10 "load case query" 2>&1)" || rc=$?
  assertEquals "eval exits 0" 0 "$rc"
  assertContains "$out" "verdict: loaded"
  assertContains "$out" "conflict: none"
  assertContains "$out" "timed_out: no"
}

test_eval_no_load_verdict() {
  write_noload_stub
  local out rc=0
  out="$(PATH="$BINDIR:$PATH" "$SCRIPT" eval --skill alpha --workspace "$WS" \
    --timeout 10 "no-load case query" 2>&1)" || rc=$?
  assertEquals "eval exits 0" 0 "$rc"
  assertContains "$out" "verdict: not-loaded"
  assertContains "$out" "conflict: none"
  assertContains "$out" "timed_out: no"
}

test_eval_sibling_load_conflict() {
  write_load_stub beta
  local out rc=0
  out="$(PATH="$BINDIR:$PATH" "$SCRIPT" eval --skill alpha --workspace "$WS" \
    --timeout 10 "sibling-load case query" 2>&1)" || rc=$?
  assertEquals "eval exits 0" 0 "$rc"
  assertContains "$out" "verdict: not-loaded"
  assertContains "$out" "conflict: wrong-skill"
  assertContains "$out" "conflict_skills: beta"
}

test_eval_timeout_reports_timed_out() {
  write_hang_stub
  local out rc=0
  out="$(PATH="$BINDIR:$PATH" "$SCRIPT" eval --skill alpha --workspace "$WS" \
    --timeout 2 "hanging query" 2>&1)" || rc=$?
  assertEquals "eval exits 0" 0 "$rc"
  assertContains "$out" "timed_out: yes"
  assertContains "$out" "exit_code: 124"
  assertContains "$out" "verdict: not-loaded"
}

test_batch_pool_bound() {
  write_counting_stub
  printf 'query one\nquery two\nquery three\nquery four\n' > "$SCEN"
  local out rc=0
  out="$(PATH="$BINDIR:$PATH" "$SCRIPT" batch --skill alpha --workspace "$WS" \
    --scenarios "$SCEN" --jobs 2 --timeout 10 2>&1)" || rc=$?
  assertEquals "batch exits 0" 0 "$rc"
  local max
  max="$(cat "$FIXTURE/concurrency/max")"
  assertTrue "max concurrency $max <= 2" "[ $max -le 2 ]"
  assertEquals "4 scenario blocks" 4 "$(printf '%s\n' "$out" | grep -c '^=== scenario ')"
  assertContains "$out" "batch summary: 4 scenarios, 0 void after serial retry"
  assertContains "$out" "timed_out: no"
}

test_batch_void_retry() {
  write_conditional_hang_stub
  printf 'plain query one\nHANGME query two\nplain query three\n' > "$SCEN"
  local out rc=0
  out="$(PATH="$BINDIR:$PATH" "$SCRIPT" batch --skill alpha --workspace "$WS" \
    --scenarios "$SCEN" --jobs 2 --timeout 2 2>&1)" || rc=$?
  assertEquals "batch exits 0" 0 "$rc"
  assertContains "$out" "verdict: void"
  assertContains "$out" "batch summary: 3 scenarios, 1 void after serial retry"
  assertEquals "void block has one target line" 1 \
    "$(printf '%s\n' "$out" | awk '/^=== scenario 1:/,/^=== scenario 2:/' | grep -c '^target: ')"
  local hang_runs
  hang_runs="$(grep -c HANGME "$FIXTURE/invocations.log")"
  assertEquals "hanging rep ran twice (initial + serial retry)" 2 "$hang_runs"
}

# shellcheck source=/dev/null
. shunit2
