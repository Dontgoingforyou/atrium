/**
 * Единый контракт минимальной длины запроса: источник правды — Python
 * `backend/app/core/portal_search_constants.py`.
 */
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import {
  PORTAL_SEARCH_MIN_QUERY_LEN,
  SEARCH_PAGE_ENTITY_TYPES,
  SEMANTIC_SEARCH_ENTITY_TYPES,
} from '@/constants/search'

const __dirname = dirname(fileURLToPath(import.meta.url))

function readPortalSearchConstantsPy(): string {
  const pyPath = join(__dirname, '../../../backend/app/core/portal_search_constants.py')
  return readFileSync(pyPath, 'utf8')
}

function readBackendMinQueryLen(src: string): number {
  const m = src.match(/PORTAL_SEARCH_MIN_QUERY_LEN:\s*int\s*=\s*(\d+)/)
  if (!m) {
    throw new Error('Не найден PORTAL_SEARCH_MIN_QUERY_LEN в portal_search_constants.py')
  }
  return Number(m[1])
}

/** Имена констант entity type → строковые значения из Python. */
function readEntityTypeNameToValue(src: string): Map<string, string> {
  const map = new Map<string, string>()
  for (const m of src.matchAll(/^(PORTAL_SEARCH_ENTITY_TYPE_\w+):\s*str\s*=\s*"([^"]+)"/gm)) {
    map.set(m[1], m[2])
  }
  return map
}

function readFrozensetConstNames(src: string, constName: string): string[] {
  const start = src.indexOf(`${constName}:`)
  if (start < 0) {
    throw new Error(`Не найден ${constName} в portal_search_constants.py`)
  }
  const open = src.indexOf('{', start)
  const close = src.indexOf('}', open)
  if (open < 0 || close < 0) {
    throw new Error(`Не разобран frozenset ${constName}`)
  }
  const block = src.slice(open, close + 1)
  return [...block.matchAll(/PORTAL_SEARCH_ENTITY_TYPE_\w+/g)].map((m) => m[0])
}

function resolveTypeSet(src: string, constName: string): Set<string> {
  const nameToValue = readEntityTypeNameToValue(src)
  const names = readFrozensetConstNames(src, constName)
  const values = new Set<string>()
  for (const name of names) {
    const v = nameToValue.get(name)
    if (!v) throw new Error(`Нет значения для ${name}`)
    values.add(v)
  }
  return values
}

describe('portal search constants', () => {
  const src = readPortalSearchConstantsPy()

  it('PORTAL_SEARCH_MIN_QUERY_LEN совпадает с portal_search_constants.py', () => {
    expect(PORTAL_SEARCH_MIN_QUERY_LEN).toBe(readBackendMinQueryLen(src))
  })

  it('min query len — положительное целое (≥ 1)', () => {
    const be = readBackendMinQueryLen(src)
    expect(PORTAL_SEARCH_MIN_QUERY_LEN).toBeGreaterThanOrEqual(1)
    expect(be).toBeGreaterThanOrEqual(1)
    expect(Number.isInteger(PORTAL_SEARCH_MIN_QUERY_LEN)).toBe(true)
  })

  it('SEMANTIC_SEARCH_ENTITY_TYPES = PORTAL_SEMANTIC_DEFAULT_TYPES (без agreement)', () => {
    const be = resolveTypeSet(src, 'PORTAL_SEMANTIC_DEFAULT_TYPES')
    expect(new Set(SEMANTIC_SEARCH_ENTITY_TYPES)).toEqual(be)
    expect(SEMANTIC_SEARCH_ENTITY_TYPES).not.toContain('agreement')
  })

  it('SEARCH_PAGE_ENTITY_TYPES = PORTAL_SEARCH_ENTITY_TYPES', () => {
    const be = resolveTypeSet(src, 'PORTAL_SEARCH_ENTITY_TYPES')
    expect(new Set(SEARCH_PAGE_ENTITY_TYPES)).toEqual(be)
  })
})
