// Smoke test for extensions/jobs-mcp.ts without running pi: fake the ExtensionAPI,
// load the extension, and call `scan` with no sources (returns without network).
// Run: npm run test:pi   (needs Node >= 22.6 for type stripping, and uv on PATH)
import assert from "node:assert/strict";
import extension from "../extensions/jobs-mcp.ts";

const tools = new Map<string, any>();
const handlers = new Map<string, Function>();
const fakePi = {
	registerTool: (t: any) => tools.set(t.name, t),
	on: (event: string, h: Function) => handlers.set(event, h),
} as any;

await extension(fakePi);

assert.ok(!handlers.has("session_start"), "extension reported a startup error instead of registering tools");
assert.deepEqual([...tools.keys()].sort(), ["get_job", "linkedin_search", "list_board_jobs", "scan"]);
for (const t of tools.values()) {
	assert.equal(t.parameters.type, "object", `${t.name}: parameters must be a JSON-Schema object`);
	assert.ok(t.description.length > 10, `${t.name}: missing description`);
}

const result = await tools.get("scan").execute("call-1", { boards_: [], linkedin_queries: [] }, undefined, undefined, {});
const parsed = JSON.parse(result.content[0].text);
assert.deepEqual(parsed, { count: 0, scanned: 0, jobs: [], errors: [] });

await handlers.get("session_shutdown")!({ type: "session_shutdown", reason: "quit" }, {});
console.log(`ok — ${tools.size} tools registered via jobs-mcp, scan round-trip works`);
