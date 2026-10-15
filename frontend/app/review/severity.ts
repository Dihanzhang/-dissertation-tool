export const SEVERITIES = ["error", "warning", "suggestion", "info"] as const;
export type Severity = typeof SEVERITIES[number];

export function isSeveritySelected(severity: string | undefined, selected: readonly Severity[]) {
  return selected.includes((severity ?? "warning") as Severity);
}
