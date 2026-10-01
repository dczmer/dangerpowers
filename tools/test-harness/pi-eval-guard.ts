/**
 * Eval guard for pi harness runs (loaded by the evaluator's pi
 * strategy with `-e`; honored even under --no-extensions).
 *
 * Two policies, both env-parameterized by PiStrategy.build_env:
 *
 *   EVAL_WS_ROOT         absolute workspace root. Any tool call whose
 *                        path argument is absolute and outside this
 *                        root is blocked — the pi equivalent of
 *                        opencode's `external_directory: deny`, which
 *                        pi has no native counterpart for.
 *   EVAL_MAX_TOOL_CALLS  integer >= 0; 0 = no cap. Every tool_call
 *                        event counts (parallel calls included); calls
 *                        beyond the cap are blocked — the pi
 *                        equivalent of opencode's `steps:` agent cap,
 *                        which pi has no CLI flag for.
 *
 * Blocked calls reach the model as error results; the run continues
 * so the agent can still write its mandated final answer. The path
 * guard covers path-carrying tools (read/grep/find/ls); bash is never
 * in an eval agent's allowlist, so command-line escape is structurally
 * impossible.
 *
 * The extension API types come from the ambient stub
 * pi-eval-guard.d.ts beside this file (the real package ships inside
 * pi, not in this repo); both files are covered by `npm run
 * typecheck`.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
	const root = process.env.EVAL_WS_ROOT ?? "";
	const maxCalls = Number(process.env.EVAL_MAX_TOOL_CALLS ?? "0");
	let calls = 0;
	pi.on("tool_call", async (event) => {
		calls++;
		if (maxCalls > 0 && calls > maxCalls) {
			return {
				block: true,
				reason: `tool-call cap reached (${maxCalls})`,
			};
		}
		const input: Record<string, unknown> = event.input ?? {};
		const target: unknown = input.path ?? input.pattern ?? "";
		if (
			root &&
			typeof target === "string" &&
			target.startsWith("/") &&
			target !== root &&
			!target.startsWith(root + "/")
		) {
			return { block: true, reason: `outside workspace: ${target}` };
		}
	});
}
