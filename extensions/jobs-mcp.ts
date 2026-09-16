/**
 * jobs-mcp bridge for pi.
 *
 * pi has no MCP support by design ("build an extension"), so this extension
 * starts the bundled jobs-mcp server over stdio, asks it for its tools, and
 * registers each one as a native pi tool under the same name
 * (list_board_jobs, get_job, linkedin_search, scan). The skills in ../skills
 * refer to those names, so they work unchanged under pi.
 *
 * Server command, in order of precedence:
 *   1. JOBS_MCP_COMMAND  — e.g. "jobs-mcp" after `pip install -e mcp/jobs-mcp`
 *   2. uvx --from <this package>/mcp/jobs-mcp jobs-mcp   (needs uv on PATH)
 */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const SERVER_DIR = join(dirname(fileURLToPath(import.meta.url)), "..", "mcp", "jobs-mcp");
const CONNECT_TIMEOUT_MS = 60_000; // first uvx run resolves and caches the venv

function serverCommand(): { command: string; args: string[] } {
	const override = process.env.JOBS_MCP_COMMAND?.trim();
	if (override) {
		const [command, ...args] = override.split(/\s+/);
		return { command, args };
	}
	return { command: "uvx", args: ["--from", SERVER_DIR, "jobs-mcp"] };
}

type Block = { type: string; text?: string };

function blocksToText(content: unknown): string {
	if (!Array.isArray(content)) return JSON.stringify(content);
	return (content as Block[])
		.map((b) => (b.type === "text" && typeof b.text === "string" ? b.text : JSON.stringify(b)))
		.join("\n");
}

export async function connect(): Promise<Client> {
	const { command, args } = serverCommand();
	const client = new Client({ name: "pi-job-agent-skills", version: "0.1.0" });
	const transport = new StdioClientTransport({ command, args, stderr: "pipe" });
	// Surface the server's stderr (uvx download progress, Python tracebacks) but keep it quiet on success.
	let stderr = "";
	transport.stderr?.on("data", (chunk: Buffer) => {
		stderr += chunk.toString();
	});
	const timer = new Promise<never>((_, reject) =>
		setTimeout(() => reject(new Error(`jobs-mcp did not start within ${CONNECT_TIMEOUT_MS / 1000}s\n${stderr}`)), CONNECT_TIMEOUT_MS).unref(),
	);
	try {
		await Promise.race([client.connect(transport), timer]);
	} catch (err) {
		await transport.close().catch(() => {});
		const msg = err instanceof Error ? err.message : String(err);
		throw new Error(`could not start jobs-mcp (${command} ${args.join(" ")}): ${msg}${stderr ? `\n${stderr}` : ""}`);
	}
	return client;
}

export default async function (pi: ExtensionAPI) {
	let client: Client;
	let startupError: string | undefined;
	try {
		client = await connect();
	} catch (err) {
		startupError = err instanceof Error ? err.message : String(err);
		pi.on("session_start", async (_event, ctx) => {
			ctx.ui.notify(
				`job-agent-skills: jobs-mcp tools unavailable — ${startupError!.split("\n")[0]}. ` +
					"Install uv (https://docs.astral.sh/uv/) or set JOBS_MCP_COMMAND.",
				"warning",
			);
		});
		return;
	}

	const { tools } = await client.listTools();
	for (const tool of tools) {
		pi.registerTool({
			name: tool.name,
			label: `jobs-mcp: ${tool.name}`,
			description: tool.description ?? tool.name,
			promptSnippet: `${tool.name}: ${(tool.description ?? "").split("\n")[0]}`,
			// MCP inputSchema is JSON Schema; TypeBox schemas are plain JSON Schema objects.
			parameters: tool.inputSchema as any,
			async execute(_toolCallId, params, signal) {
				const result = await client.callTool({ name: tool.name, arguments: params as Record<string, unknown> }, undefined, { signal });
				const text = blocksToText(result.content);
				if (result.isError) throw new Error(text || `${tool.name} failed`);
				return { content: [{ type: "text", text }], details: result.structuredContent ?? {} };
			},
		});
	}

	pi.on("session_shutdown", async () => {
		await client.close().catch(() => {});
	});
}
