import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

import handler from "../netlify/functions/api.mjs";

const originalOrigin = process.env.CROSSLAYER_API_ORIGIN;
const originalFetch = globalThis.fetch;

afterEach(() => {
  if (originalOrigin === undefined) {
    delete process.env.CROSSLAYER_API_ORIGIN;
  } else {
    process.env.CROSSLAYER_API_ORIGIN = originalOrigin;
  }
  globalThis.fetch = originalFetch;
});

test("proxies API path and session cookie to the HTTPS backend", async () => {
  process.env.CROSSLAYER_API_ORIGIN = "https://crosslayer.example.ts.net";
  let forwardedUrl;
  let forwardedCookie;
  globalThis.fetch = async (url, options) => {
    forwardedUrl = String(url);
    forwardedCookie = options.headers.get("cookie");
    return new Response('{"authenticated":true}', {
      headers: {
        "content-type": "application/json",
        "set-cookie": "crosslayer_session=token; Path=/api/v1; HttpOnly; Secure; SameSite=strict",
      },
    });
  };

  const response = await handler(
    new Request(
      "https://crosslayer.netlify.app/.netlify/functions/api/api/v1/auth/session?check=1",
      { headers: { cookie: "crosslayer_session=existing" } },
    ),
  );

  assert.equal(
    forwardedUrl,
    "https://crosslayer.example.ts.net/api/v1/auth/session?check=1",
  );
  assert.equal(forwardedCookie, "crosslayer_session=existing");
  assert.equal(response.status, 200);
  assert.match(response.headers.get("set-cookie"), /HttpOnly; Secure/);
  assert.deepEqual(await response.json(), { authenticated: true });
});

test("fails closed when the API origin is not configured", async () => {
  delete process.env.CROSSLAYER_API_ORIGIN;
  const response = await handler(
    new Request("https://crosslayer.netlify.app/.netlify/functions/api/api/v1/health"),
  );

  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), {
    detail: "Dashboard API endpoint is not configured",
  });
});

test("rejects non-HTTPS API origins", async () => {
  process.env.CROSSLAYER_API_ORIGIN = "http://insecure.example.ts.net";
  const response = await handler(
    new Request("https://crosslayer.netlify.app/.netlify/functions/api/api/v1/health"),
  );

  assert.equal(response.status, 500);
});
