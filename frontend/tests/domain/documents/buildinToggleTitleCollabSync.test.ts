/**
 * Селектор chrome NodeView в summary: FE domain и collab schema-nodes.
 */
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import { BUILDIN_TOGGLE_TITLE_CHROME_SELECTOR } from '@/domain/documents/buildinToggleTitle'

const __dirname = dirname(fileURLToPath(import.meta.url))

function readCollabChromeSelector(): string {
  const mjsPath = join(
    __dirname,
    '../../../../services/document-collab/src/parse-buildin-toggle-title.mjs',
  )
  const src = readFileSync(mjsPath, 'utf8')
  const m = src.match(/BUILDIN_TOGGLE_TITLE_CHROME_SELECTOR\s*=\s*'([^']+)'/)
  if (!m) {
    throw new Error(`Не найден BUILDIN_TOGGLE_TITLE_CHROME_SELECTOR в ${mjsPath}`)
  }
  return m[1]
}

describe('buildin-toggle title chrome selector', () => {
  it('совпадает с document-collab parse-buildin-toggle-title.mjs', () => {
    expect(BUILDIN_TOGGLE_TITLE_CHROME_SELECTOR).toBe(readCollabChromeSelector())
  })
})
