/** Приводит unknown к Record<string, unknown> или null (массивы и примитивы отбрасываются). */
export function asRecord(v: unknown): Record<string, unknown> | null {
  return v !== null && typeof v === 'object' && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : null
}
