import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import { changelogSeenStorageKey } from '@/constants/changelog'
import {
  WHATS_NEW_ENTRIES,
  WHATS_NEW_PAGE_SIZE,
  formatWhatsNewDate,
  hasUnseenWhatsNew,
  whatsNewPage,
} from '@/domain/changelog/whatsNew'

const changelogPath = join(dirname(fileURLToPath(import.meta.url)), '../../../../CHANGELOG.md')

function changelogVersions(): string[] {
  const src = readFileSync(changelogPath, 'utf8')
  return [...src.matchAll(/^## \[(\d+\.\d+\.\d+)\]/gm)].map((match) => match[1])
}

describe('whatsNew', () => {
  it('первая порция — 1.3.23–1.3.14, вторая — 1.3.13–1.3.4, хвост — 1.3.3–1.3.1', () => {
    const first = whatsNewPage(WHATS_NEW_ENTRIES, 0)
    const second = whatsNewPage(WHATS_NEW_ENTRIES, 1)
    const tail = whatsNewPage(WHATS_NEW_ENTRIES, 2)

    expect(first).toHaveLength(WHATS_NEW_PAGE_SIZE)
    expect(first[0]?.version).toBe('1.3.23')
    expect(first.at(-1)?.version).toBe('1.3.14')
    expect(second[0]?.version).toBe('1.3.13')
    expect(second.at(-1)?.version).toBe('1.3.4')
    expect(second).toHaveLength(WHATS_NEW_PAGE_SIZE)
    expect(tail.map((entry) => entry.version)).toEqual(['1.3.3', '1.3.2', '1.3.1'])
    expect(whatsNewPage(WHATS_NEW_ENTRIES, 3)).toEqual([])
  })

  it('дата для сотрудника без сдвига суток', () => {
    expect(formatWhatsNewDate('2026-10-20')).toBe('20 октября')
  })

  it('отметка просмотра своя у каждой учётки', () => {
    expect(changelogSeenStorageKey('manager')).not.toBe(changelogSeenStorageKey('employee'))
    expect(changelogSeenStorageKey('manager')).toContain('manager')
  })

  it('кружок горит, пока последняя версия не открыта', () => {
    expect(hasUnseenWhatsNew(null, '1.3.15')).toBe(true)
    expect(hasUnseenWhatsNew('1.3.14', '1.3.15')).toBe(true)
    expect(hasUnseenWhatsNew('1.3.15', '1.3.15')).toBe(false)
    expect(hasUnseenWhatsNew(null, null)).toBe(false)
  })

  it('на сайте нет ключей задач, версии совпадают с CHANGELOG.md', () => {
    expect(WHATS_NEW_ENTRIES.map((entry) => entry.version)).toEqual(changelogVersions())
    expect(WHATS_NEW_ENTRIES.every((entry) => !/DEV-\d+/.test(entry.text))).toBe(true)
    expect(
      WHATS_NEW_ENTRIES.every((entry) =>
        entry.text.split('\n').every((line) => /^(?:- )?(FIX|NEW|CHANGE)\. /.test(line)),
      ),
    ).toBe(true)
  })
})
