/**
 * Единый контракт срока хранения документа в корзине: источник правды — Python
 * `backend/app/portal_documents/services/portal_document_trash.py`.
 */
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import { DOCUMENT_TRASH_TTL_DAYS } from '@/constants/documentTrash'

const __dirname = dirname(fileURLToPath(import.meta.url))

function readBackendTrashTtlDays(): number {
  const pyPath = join(
    __dirname,
    '../../../backend/app/portal_documents/services/portal_document_trash.py',
  )
  const src = readFileSync(pyPath, 'utf8')
  const m = src.match(/DOCUMENT_TRASH_TTL_DAYS\s*[:=]\s*(\d+)/)
  if (!m) {
    throw new Error(`Не найден DOCUMENT_TRASH_TTL_DAYS в ${pyPath}`)
  }
  return Number(m[1])
}

describe('document trash constants', () => {
  it('DOCUMENT_TRASH_TTL_DAYS совпадает с portal_document_trash.py', () => {
    expect(DOCUMENT_TRASH_TTL_DAYS).toBe(readBackendTrashTtlDays())
  })

  it('TTL — положительное число дней (не 0 и не NaN)', () => {
    const be = readBackendTrashTtlDays()
    expect(DOCUMENT_TRASH_TTL_DAYS).toBeGreaterThan(0)
    expect(be).toBeGreaterThan(0)
    expect(Number.isInteger(DOCUMENT_TRASH_TTL_DAYS)).toBe(true)
  })
})
