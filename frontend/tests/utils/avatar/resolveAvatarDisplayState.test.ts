import { describe, expect, it } from 'vitest'

import {
  avatarInnerKind,
  resolveAvatarDisplayState,
} from '@/utils/avatar/resolveAvatarDisplayState'
import { selectStableImageUrl } from '@/utils/avatar/selectStableImageUrl'

const proxy = '/api/v1/portal/users/u1/photo?exp=1&sig=x'
const blob = 'blob:http://localhost/abc'

describe('resolveAvatarDisplayState', () => {
  it('без URL — инициалы', () => {
    expect(
      resolveAvatarDisplayState({
        cleanUrl: null,
        isPhotoProxy: false,
        canFetchProxy: false,
        blobUrl: null,
        proxyFailed: false,
      }),
    ).toEqual({ kind: 'none' })
  })

  it('обычный URL (группа MinIO) отдаёт сразу', () => {
    expect(
      resolveAvatarDisplayState({
        cleanUrl: 'https://minio.example/avatars/chats/g.jpg',
        isPhotoProxy: false,
        canFetchProxy: false,
        blobUrl: null,
        proxyFailed: false,
      }),
    ).toEqual({ kind: 'url', href: 'https://minio.example/avatars/chats/g.jpg' })
  })

  it('пока proxy грузится — pending, не none', () => {
    expect(
      resolveAvatarDisplayState({
        cleanUrl: proxy,
        isPhotoProxy: true,
        canFetchProxy: true,
        blobUrl: null,
        proxyFailed: false,
      }),
    ).toEqual({ kind: 'pending' })
  })

  it('после blob — url', () => {
    expect(
      resolveAvatarDisplayState({
        cleanUrl: proxy,
        isPhotoProxy: true,
        canFetchProxy: true,
        blobUrl: blob,
        proxyFailed: false,
      }),
    ).toEqual({ kind: 'url', href: blob })
  })

  it('после отказа proxy — инициалы', () => {
    expect(
      resolveAvatarDisplayState({
        cleanUrl: proxy,
        isPhotoProxy: true,
        canFetchProxy: true,
        blobUrl: null,
        proxyFailed: true,
      }),
    ).toEqual({ kind: 'none' })
  })

  it('proxy без токена — инициалы', () => {
    expect(
      resolveAvatarDisplayState({
        cleanUrl: proxy,
        isPhotoProxy: true,
        canFetchProxy: false,
        blobUrl: null,
        proxyFailed: false,
      }),
    ).toEqual({ kind: 'none' })
  })
})

describe('avatarInnerKind', () => {
  it('пока proxy pending и кадра нет — инициалы, не пустой круг', () => {
    expect(avatarInnerKind(null, null)).toBe('initials')
  })

  it('есть живой URL — картинка', () => {
    expect(avatarInnerKind(blob, null)).toBe('img')
  })

  it('битый кадр — снова инициалы', () => {
    expect(avatarInnerKind(blob, blob)).toBe('initials')
  })
})

describe('selectStableImageUrl', () => {
  it('при holdWhenEmpty держит предыдущий кадр', () => {
    expect(selectStableImageUrl(null, blob, true)).toBe(blob)
  })

  it('без hold сбрасывает кадр', () => {
    expect(selectStableImageUrl(null, blob, false)).toBeNull()
  })

  it('пока есть новый URL — возвращает displayedUrl (ждём загрузку)', () => {
    expect(selectStableImageUrl('https://new', blob, false)).toBe(blob)
  })
})
