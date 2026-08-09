import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const landing = () => readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
const review = () => readFile(new URL("../app/review/page.tsx", import.meta.url), "utf8");
const readme = () => readFile(new URL("../../README.md", import.meta.url), "utf8");

test("product copy describes deterministic review results without an LLM feature", async () => {
  const [landingSource, reviewSource, readmeSource] = await Promise.all([
    landing(),
    review(),
    readme(),
  ]);

  assert.match(landingSource, /Deterministic, rule-based findings/);
  assert.doesNotMatch(landingSource, /AI-assisted clarity review/i);

  assert.match(reviewSource, /No large language model generates the review results/);
  assert.doesNotMatch(reviewSource, /AI-Assisted Polish|Run AI polish|Sending to AI|\/api\/review/);

  assert.match(readmeSource, /No large language model generates the review results/);
  assert.match(readmeSource, /Legacy code, not part of the current product/);
});
