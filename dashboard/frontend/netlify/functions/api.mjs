const FUNCTION_PREFIX = "/.netlify/functions/api";
const METHODS = new Set(["GET", "POST"]);

function jsonResponse(status, detail) {
  return new Response(JSON.stringify({ detail }), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

export default async function handler(request) {
  if (!METHODS.has(request.method)) {
    return jsonResponse(405, "Method not allowed");
  }

  const configuredOrigin = process.env.CROSSLAYER_API_ORIGIN;
  if (!configuredOrigin) {
    return jsonResponse(503, "Dashboard API endpoint is not configured");
  }

  let origin;
  try {
    origin = new URL(configuredOrigin);
  } catch {
    return jsonResponse(500, "Dashboard API endpoint is invalid");
  }

  if (
    origin.protocol !== "https:" ||
    origin.username ||
    origin.password ||
    origin.pathname !== "/" ||
    origin.search ||
    origin.hash
  ) {
    return jsonResponse(500, "Dashboard API endpoint must be an HTTPS origin");
  }

  const requestUrl = new URL(request.url);
  const apiPath = requestUrl.pathname.slice(FUNCTION_PREFIX.length);
  if (!apiPath.startsWith("/api/v1/")) {
    return jsonResponse(404, "Not found");
  }

  const upstreamUrl = new URL(`${apiPath}${requestUrl.search}`, origin);
  const headers = new Headers();
  for (const name of ["accept", "content-type", "cookie"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  try {
    const upstream = await fetch(upstreamUrl, {
      method: request.method,
      headers,
      body: request.method === "POST" ? await request.arrayBuffer() : undefined,
      redirect: "manual",
      cache: "no-store",
    });

    const responseHeaders = new Headers();
    for (const name of ["content-type", "cache-control", "set-cookie", "location"]) {
      const value = upstream.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }

    return new Response(upstream.status === 204 ? null : await upstream.arrayBuffer(), {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch {
    return jsonResponse(502, "Dashboard API is unreachable");
  }
}
