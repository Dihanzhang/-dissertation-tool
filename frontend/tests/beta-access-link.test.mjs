import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const read = (path) => readFile(new URL(path, import.meta.url), "utf8");

test("the beta page takes its token from the private URL path", async () => {
  const source = await read("../app/beta/page.tsx");

  assert.match(source, /window\.location\.pathname/);
  assert.match(source, /localStorage\.setItem\("beta-access-token"/);
  assert.match(source, /router\.replace\("\/review"\)/);
});

test("the beta page no longer sends magic-link emails", async () => {
  const source = await read("../app/beta/page.tsx");

  assert.doesNotMatch(source, /auth\/v1\/otp/);
  assert.doesNotMatch(source, /email_redirect_to/);
  assert.doesNotMatch(source, /beta-redemption-pending/);
});

test("the beta page hands off to the review page without a server round trip", async () => {
  const source = await read("../app/beta/page.tsx");

  // The review page already validates the token; checking it here too made the
  // tester wait for two server calls instead of one.
  assert.doesNotMatch(source, /fetch\(/);
  assert.doesNotMatch(source, /api\/beta\/access/);
});

test("the review page explains a slow cold start instead of looking frozen", async () => {
  const source = await read("../app/review/page.tsx");

  assert.match(source, /waking up/i);
});

test("the review page authorises requests with the beta header", async () => {
  const source = await read("../app/review/page.tsx");

  assert.match(source, /"X-Beta-Access"/);
  assert.match(source, /beta-access-token/);
  assert.match(source, /\/api\/beta\/access/);
});

test("the landing and account pages drop the magic-link beta detour", async () => {
  const landing = await read("../app/page.tsx");
  const account = await read("../app/account/page.tsx");

  assert.doesNotMatch(landing, /beta-redemption-pending/);
  assert.doesNotMatch(account, /beta-redemption-pending/);
});

test("private beta URLs are not advertised on the landing page", async () => {
  const landing = await read("../app/page.tsx");

  assert.doesNotMatch(landing, /href="\/beta/);
});

test("netlify serves the beta page for every private beta URL", async () => {
  const config = await read("../../netlify.toml");

  assert.match(config, /from = "\/beta\/\*"/);
  assert.match(config, /to = "\/beta\.html"/);
  assert.match(config, /status = 200/);
});
