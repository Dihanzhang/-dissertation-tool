import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const account = () => readFile(new URL("../app/account/page.tsx", import.meta.url), "utf8");

test("sign-in asks Supabase for a code, not a clickable link", async () => {
  const source = await account();

  // A link in the email is what Microsoft Safe Links consumes before the user clicks it.
  assert.doesNotMatch(source, /email_redirect_to/);
  assert.match(source, /auth\/v1\/otp/);
});

test("the entered code is exchanged for a session", async () => {
  const source = await account();

  assert.match(source, /auth\/v1\/verify/);
  assert.match(source, /type:\s*"email"/);
  assert.match(source, /access_token/);
});

test("the page collects a numeric code of whatever length Supabase sends", async () => {
  const source = await account();

  assert.match(source, /inputMode="numeric"/);
  assert.match(source, /autoComplete="one-time-code"/);
  // Supabase's OTP length is a project setting, so no fixed length may be assumed.
  assert.doesNotMatch(source, /maxLength=\{6\}/);
  assert.doesNotMatch(source, /6-digit/);
});

test("an expired session returns the user to the sign-in form", async () => {
  const source = await account();

  // Without this the page shows a signed-in view backed by a dead token, and
  // there is no way to request a new code.
  assert.match(source, /status === 401/);
  assert.match(source, /removeItem\("submission-pass-token"\)/);
});
