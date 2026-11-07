import { parseJsonOrThrowApi } from './parseResponse'
import { API_BASE, authenticatedFetch } from './rawClient'
import type { RichMediaRead } from '../types/richMedia'

export type { RichMediaRead }

const RICH_MEDIA_PATH_RE = /\/api\/v1\/portal\/rich-media\/([0-9a-f-]{36})\/file/gi
const RICH_MEDIA_CACHE_TTL_MS = 3.5 * 60 * 60 * 1000

type CachedRichMedia = { data: RichMediaRead; expiresAt: number }
const richMediaCache = new Map<string, CachedRichMedia>()

export function extractRichMediaIdsFromHtml(html: string): string[] {
  const ids = new Set<string>()
  for (const match of html.matchAll(RICH_MEDIA_PATH_RE)) {
    if (match[1]) ids.add(match[1])
  }
  return [...ids]
}

export function richMediaFilePath(mediaId: string): string {
  return `${API_BASE}/portal/rich-media/${mediaId}/file`
}

export async function getRichMedia(mediaId: string): Promise<RichMediaRead> {
  const cached = richMediaCache.get(mediaId)
  if (cached && cached.expiresAt > Date.now()) {
    return cached.data
  }
  const res = await authenticatedFetch(`/portal/rich-media/${mediaId}`)
  const data = await parseJsonOrThrowApi<RichMediaRead>(res)
  richMediaCache.set(mediaId, { data, expiresAt: Date.now() + RICH_MEDIA_CACHE_TTL_MS })
  return data
}

export async function uploadTaskRichMedia(taskId: string, file: File): Promise<RichMediaRead> {
  const form = new FormData()
  form.append('file', file)
  const res = await authenticatedFetch(`/portal/tasks/${taskId}/rich-media`, {
    method: 'POST',
    body: form,
  })
  return parseJsonOrThrowApi<RichMediaRead>(res)
}

export async function uploadDocumentRichMedia(documentId: string, file: File): Promise<RichMediaRead> {
  const form = new FormData()
  form.append('file', file)
  const res = await authenticatedFetch(`/portal/documents/${documentId}/rich-media`, {
    method: 'POST',
    body: form,
  })
  return parseJsonOrThrowApi<RichMediaRead>(res)
}

/** Подставляет presigned URL вместо стабильных путей API (img не шлёт Bearer). */
export async function resolveRichMediaUrlsInHtml(html: string): Promise<string> {
  const ids = extractRichMediaIdsFromHtml(html)
  if (ids.length === 0) return html

  const urlById = new Map<string, string>()
  await Promise.all(
    ids.map(async (id) => {
      try {
        const media = await getRichMedia(id)
        urlById.set(id, media.download_url)
      } catch {
        /* оставляем исходный src */
      }
    }),
  )

  let out = html
  for (const [id, url] of urlById) {
    const escaped = id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const re = new RegExp(`(/api/v1/portal/rich-media/${escaped}/file)`, 'gi')
    out = out.replace(re, url)
  }
  return out
}
