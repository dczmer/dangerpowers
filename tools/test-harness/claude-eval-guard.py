#!/usr/bin/env python3
"""PreToolUse hook: step-cap guard for claude eval runs (wired via a
per-run --settings file written by ClaudeStrategy._guard_settings_path).

Path confinement is NOT this script's job — --restricted already limits
file-tool paths to the working directory, Claude Code's native
equivalent of opencode's `external_directory: deny` and pi-eval-guard's
root-prefix check. This hook only replaces the half Claude Code has no
flag for: a hard cap on tool-call count, matching pi-eval-guard.ts's
EVAL_MAX_TOOL_CALLS policy.

Hooks are separate process invocations per call with no shared memory,
so the counter lives in a file next to the settings file that invoked
this hook (CLAUDE_EVAL_COUNTER_FILE), one per session.
"""

import json
import os
import sys


def main() -> int:
    json.load(sys.stdin)
    max_calls = int(os.environ.get("EVAL_MAX_TOOL_CALLS", "0"))
    if max_calls <= 0:
        print(json.dumps({}))
        return 0

    counter_path = os.environ.get("CLAUDE_EVAL_COUNTER_FILE")
    if not counter_path:
        print(json.dumps({}))
        return 0

    try:
        with open(counter_path, "r+") as f:
            count = int(f.read().strip() or "0") + 1
            f.seek(0)
            f.write(str(count))
            f.truncate()
    except FileNotFoundError:
        count = 1
        with open(counter_path, "w") as f:
            f.write(str(count))

    if count > max_calls:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            f"tool-call cap reached ({max_calls})"
                        ),
                    }
                }
            )
        )
        return 0

    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
