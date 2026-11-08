export type ConversionLevel = 'high' | 'medium' | 'low'

export const CONVERSION_LEVEL_COLORS: Record<ConversionLevel, string> = {
  high: '#e1e235',
  medium: '#0f766e',
  low: '#df4d12',
}

const HIGH_MIN = 3
const MEDIUM_MIN = 1.5

export function conversionLevel(value: number): ConversionLevel {
  if (value >= HIGH_MIN) return 'high'
  if (value >= MEDIUM_MIN) return 'medium'
  return 'low'
}

export function conversionLevelColor(value: number): string {
  return CONVERSION_LEVEL_COLORS[conversionLevel(value)]
}
