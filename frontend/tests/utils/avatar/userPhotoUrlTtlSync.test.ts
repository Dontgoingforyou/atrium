import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import { PORTAL_USERS_STALE_TIME_MS } from '@/api/queryKeys'

const __dirname = dirname(fileURLToPath(import.meta.url))

function readBackendPhotoTtlSeconds(): number {
  const pyPath = join(__dirname, '../../../../backend/app/core/config.py')
  const src = readFileSync(pyPath, 'utf8')
  const m = src.match(/user_photo_url_ttl_seconds:\s*int\s*=\s*Field\(\s*default=(\d+)/)
  if (!m) {
    throw new Error(`Не найден user_photo_url_ttl_seconds default в ${pyPath}`)
  }
  return Number(m[1])
}

describe('user photo URL TTL', () => {
  it('PORTAL_USERS_STALE_TIME_MS совпадает с user_photo_url_ttl_seconds', () => {
    expect(PORTAL_USERS_STALE_TIME_MS).toBe(readBackendPhotoTtlSeconds() * 1000)
  })
})
