import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const landing = () => readFile(new URL("../app/page.tsx", import.meta.url), "utf8");

test("the sample reviewed document is shown before what the pass includes", async () => {
  const source = await landing();

  assert.match(source, /review-output-sample\.png/);
  const sample = source.indexOf("review-output-sample.png");
  const includes = source.indexOf("What your pass includes");
  assert.ok(sample < includes, "the sample must appear before the pass contents");
});

test("feedback fields are visible against the dark section", async () => {
  const source = await landing();

  // Dark text with no background renders invisible in a browser's dark mode.
  const fields = source.match(/<(input|textarea)[^>]*name="(name|contact|message)"[^>]*>/g) ?? [];
  assert.equal(fields.length, 3);
  for (const field of fields) {
    assert.match(field, /bg-white/, `missing background: ${field}`);
  }
});

test("the help contact sits near the buying decision, not at the page foot", async () => {
  const source = await landing();

  const help = source.indexOf("Need help?");
  const feedback = source.indexOf('id="feedback"');
  assert.ok(help !== -1, "the help contact must still exist");
  assert.ok(help < feedback, "the help line must appear above the feedback section");
});
