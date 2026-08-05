import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("landing page keeps pending beta sign-ins in the beta flow", async () => {
  const source = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");

  assert.match(source, /beta-redemption-pending/);
  assert.match(source, /window\.location\.replace\(`\/beta\$\{window\.location\.hash\}`\)/);
  assert.match(source, /window\.location\.replace\(`\/account\$\{window\.location\.hash\}`\)/);
});
