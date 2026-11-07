import { parseJsonOrThrowApi } from './parseResponse'
import { authenticatedFetch } from './rawClient'
import type { RichMediaRead } from './richMediaApi'
import type { ThreadComment, ThreadCommentCreate, ThreadCommentUpdate } from '../types/commentThread'

export function createCommentThreadApi(basePath: string) {
  return {
    async list(): Promise<ThreadComment[]> {
      const res = await authenticatedFetch(basePath)
      return parseJsonOrThrowApi(res)
    },

    async uploadMedia(file: File): Promise<RichMediaRead> {
      const formData = new FormData()
      formData.append('file', file)
      const res = await authenticatedFetch(`${basePath}/rich-media`, {
        method: 'POST',
        body: formData,
      })
      return parseJsonOrThrowApi(res)
    },

    async create(body: ThreadCommentCreate): Promise<ThreadComment> {
      const res = await authenticatedFetch(basePath, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      return parseJsonOrThrowApi(res)
    },

    async update(commentId: string, body: ThreadCommentUpdate): Promise<ThreadComment> {
      const res = await authenticatedFetch(
        `${basePath}/${encodeURIComponent(commentId)}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        },
      )
      return parseJsonOrThrowApi(res)
    },

    async remove(commentId: string): Promise<void> {
      const res = await authenticatedFetch(
        `${basePath}/${encodeURIComponent(commentId)}`,
        { method: 'DELETE' },
      )
      await parseJsonOrThrowApi(res)
    },
  }
}
