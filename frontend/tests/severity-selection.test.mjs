import assert from "node:assert/strict";
import test from "node:test";
import { SEVERITIES, isSeveritySelected } from "../app/review/severity.ts";

const findings = [
  { severity: "error", message: "Missing reference" },
  { severity: "warning", message: "Check formatting" },
  { severity: "suggestion", message: "Optional style change" },
  { severity: "info", message: "Check program preference" },
];

test("default selection shows all four severities", () => {
  assert.deepEqual(SEVERITIES, ["error", "warning", "suggestion", "info"]);
  assert.deepEqual(findings.filter(f => isSeveritySelected(f.severity, SEVERITIES)), findings);
});

test("focus view and empty selection preserve the complete review", () => {
  assert.deepEqual(findings.filter(f => isSeveritySelected(f.severity, ["error", "warning"])), findings.slice(0, 2));
  assert.deepEqual(findings.filter(f => isSeveritySelected(f.severity, [])), []);
  assert.equal(findings.length, 4);
  assert.deepEqual(findings.filter(f => isSeveritySelected(f.severity, SEVERITIES)), findings);
});

test("legacy citation results without severity use the export's warning default", () => {
  assert.equal(isSeveritySelected(undefined, ["error"]), false);
  assert.equal(isSeveritySelected(undefined, ["warning"]), true);
});
