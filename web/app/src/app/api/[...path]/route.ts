// Same-origin proxy: the browser calls /api/* here and this server forwards to tracker-api.
// A route handler (not next.config rewrites) so API_URL is read at runtime — docker-compose
// sets it to http://api:8000 without a rebuild. Only the api container ever sees the token.

import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const API_URL = () => (process.env.API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const FORWARD = ["authorization", "content-type", "accept"];

async function proxy(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const url = `${API_URL()}/api/${path.join("/")}${req.nextUrl.search}`;
  const headers = new Headers();
  for (const h of FORWARD) {
    const v = req.headers.get(h);
    if (v) headers.set(h, v);
  }
  let upstream: Response;
  try {
    upstream = await fetch(url, {
      method: req.method,
      headers,
      body: req.method === "GET" || req.method === "HEAD" ? undefined : await req.arrayBuffer(),
      cache: "no-store",
      redirect: "manual",
    });
  } catch (e) {
    return Response.json({ detail: `tracker-api unreachable at ${API_URL()}: ${String(e)}` }, { status: 502 });
  }
  const out = new Headers();
  for (const h of ["content-type", "www-authenticate"]) {
    const v = upstream.headers.get(h);
    if (v) out.set(h, v);
  }
  return new Response(upstream.body, { status: upstream.status, headers: out });
}

export { proxy as GET, proxy as POST, proxy as PATCH, proxy as PUT, proxy as DELETE };
