/**
 * Единый контракт title-предикатов колонок: источник — Python
 * `backend/app/portal_collab/services/_task_home_common.py`.
 */
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import {
  APPROVAL_LIKE_COLUMN_TITLE_PATTERN,
  CANCELLED_LIKE_COLUMN_TITLE_PATTERN,
  DONE_LIKE_COLUMN_TITLE_PATTERN,
} from '@/domain/tasks/taskColumns'

const __dirname = dirname(fileURLToPath(import.meta.url))

function readBackendPattern(name: string): string {
  const pyPath = join(
    __dirname,
    '../../../../backend/app/portal_collab/services/_task_home_common.py',
  )
  const src = readFileSync(pyPath, 'utf8')
  const m = src.match(new RegExp(`${name}\\s*=\\s*r?"(.+)"`))
  if (!m) {
    throw new Error(`Не найден ${name} в ${pyPath}`)
  }
  return m[1]
}

describe('task column title patterns', () => {
  it('done / approval / cancelled совпадают с _task_home_common.py', () => {
    expect(DONE_LIKE_COLUMN_TITLE_PATTERN).toBe(readBackendPattern('DONE_LIKE_COLUMN_TITLE_PATTERN'))
    expect(APPROVAL_LIKE_COLUMN_TITLE_PATTERN).toBe(
      readBackendPattern('APPROVAL_LIKE_COLUMN_TITLE_PATTERN'),
    )
    expect(CANCELLED_LIKE_COLUMN_TITLE_PATTERN).toBe(
      readBackendPattern('CANCELLED_LIKE_COLUMN_TITLE_PATTERN'),
    )
  })
})
