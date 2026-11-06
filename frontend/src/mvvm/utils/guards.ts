// isRecord narrows untrusted host data to a plain object before reading fields.
export function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}
