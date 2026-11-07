import type { RichMediaRead } from './richMedia'

export type ThreadCommentMedia = RichMediaRead

/** Комментарий в треде. */
export type ThreadComment = {
  id: string
  parent_id: string | null
  author_sub: string
  author_display_name?: string | null
  body: string
  mentions: string[]
  /** Версия для CAS (optimistic locking). */
  version: number
  created_at: string
  updated_at: string
  replies: ThreadComment[]
  media?: ThreadCommentMedia[]
}

export type ThreadCommentCreate = {
  body: string
  parent_id: string | null
  mentions: string[]
  media_ids?: string[]
}

export type ThreadCommentUpdate = {
  expected_version: number
  body?: string
  mentions?: string[]
}

/** Результат загрузки медиа в комментарий (подмножество RichMediaRead). */
export type CommentThreadUploadResult = Pick<
  RichMediaRead,
  'id' | 'download_url' | 'original_filename'
>
