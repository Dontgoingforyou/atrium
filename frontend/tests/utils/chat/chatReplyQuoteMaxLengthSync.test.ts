/**
 * Единый контракт длины цитаты ответа: источник правды —
 * `backend/app/portal_chat/constants.py`.
 */
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import { CHAT_REPLY_QUOTE_TEXT_MAX_LENGTH } from '@/utils/chat/messageQuoteSelection'

const __dirname = dirname(fileURLToPath(import.meta.url))

function readBackendQuoteMaxLength(): number {
  const pyPath = join(
    __dirname,
    '../../../../backend/app/portal_chat/constants.py',
  )
  const src = readFileSync(pyPath, 'utf8')
  const m = src.match(/CHAT_REPLY_QUOTE_TEXT_MAX_LENGTH\s*=\s*(\d+)/)
  if (!m) {
    throw new Error(`Не найден CHAT_REPLY_QUOTE_TEXT_MAX_LENGTH в ${pyPath}`)
  }
  return Number(m[1])
}

describe('chat reply quote constants', () => {
  it('CHAT_REPLY_QUOTE_TEXT_MAX_LENGTH совпадает с portal_chat/constants.py', () => {
    expect(CHAT_REPLY_QUOTE_TEXT_MAX_LENGTH).toBe(readBackendQuoteMaxLength())
  })
})
