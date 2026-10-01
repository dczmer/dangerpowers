/**
 * Minimal ambient typings for the pi extension API surface the eval
 * guard uses. The real package (@earendil-works/pi-coding-agent) ships
 * inside pi and is not a repo dependency, so this stub lets
 * `npm run typecheck` verify pi-eval-guard.ts against the documented
 * event and return shapes (pi docs/extensions.md, "Tool interaction"
 * and the tool_call examples). Keep in sync with the shipped API;
 * drift here fails typecheck, not a silent eval-time break.
 */
declare module "@earendil-works/pi-coding-agent" {
	export interface ToolCallEvent {
		toolName: string;
		input: Record<string, unknown>;
	}

	export interface ToolCallBlock {
		block: true;
		reason: string;
	}

	export interface ExtensionAPI {
		on(
			event: "tool_call",
			handler: (
				event: ToolCallEvent,
			) =>
				| ToolCallBlock
				| void
				| Promise<ToolCallBlock | void>,
		): () => void;
	}
}
