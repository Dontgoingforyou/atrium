import type { ReactNode } from 'react'

import type { PortalUser } from '../../types/chat'
import { getUserDisplayLabel } from '../../utils/userLabel'
import { isSafeExternalUrl } from '../../utils/safeExternalUrl'
import styles from '@/styles/modules/tasks/TaskComments.module.css'

type MentionSegment = { type: 'text' | 'mark'; value: string }

export type CommentBodySegment = { type: 'text' | 'mark' | 'link'; value: string }

/** http(s) URL в plain text; завершающая пунктуация отсекается отдельно. */
const HTTP_URL_RE = /https?:\/\/[^\s<>"']+/gi

const TRAILING_URL_PUNCT_RE = /[.,;:!?)\]}>]+$/

export function buildMentionSegments(
  body: string,
  mentionSubs: string[],
  users: PortalUser[],
): MentionSegment[] {
  const userBySub = new Map(users.map((u) => [u.sub, u]))
  const uniqueSubs = [...new Set(mentionSubs)]
  const pairs = uniqueSubs
    .map((sub) => {
      const u = userBySub.get(sub)
      const label = u ? getUserDisplayLabel(u, { trim: true }) : sub
      return { sub, label }
    })
    .filter((p) => p.label.length > 0)
    .sort((a, b) => b.label.length - a.label.length)

  const segments: MentionSegment[] = []
  let i = 0
  while (i < body.length) {
    if (body[i] !== '@') {
      const nextAt = body.indexOf('@', i + 1)
      const end = nextAt < 0 ? body.length : nextAt
      segments.push({ type: 'text', value: body.slice(i, end) })
      i = end
      continue
    }

    let matchedMention = false
    for (const { label } of pairs) {
      const n = 1 + label.length
      if (body.slice(i, i + n) === '@' + label) {
        segments.push({ type: 'mark', value: `@${label}` })
        i += n
        matchedMention = true
        break
      }
    }
    if (matchedMention) continue

    const rest = body.slice(i)
    const legacy = rest.match(/^@(\S+)/)
    if (legacy) {
      segments.push({ type: 'mark', value: legacy[0] })
      i += legacy[0].length
      continue
    }

    if (i + 1 < body.length && body[i + 1] === '@') {
      segments.push({ type: 'text', value: '@' })
      i += 1
    } else {
      segments.push({ type: 'text', value: body[i]! })
      i += 1
    }
  }

  return mergeAdjacentText(segments)
}

function mergeAdjacentText(input: MentionSegment[]): MentionSegment[] {
  const out: MentionSegment[] = []
  for (const seg of input) {
    const last = out[out.length - 1]
    if (last && last.type === 'text' && seg.type === 'text') {
      last.value += seg.value
    } else {
      out.push({ ...seg })
    }
  }
  return out
}

/**
 * Разбить plain text на text/link. Только http(s) и только после isSafeExternalUrl.
 */
export function splitTextWithSafeUrls(
  text: string,
): Array<{ type: 'text' | 'link'; value: string }> {
  if (!text) return []

  const out: Array<{ type: 'text' | 'link'; value: string }> = []
  let lastIndex = 0
  const re = new RegExp(HTTP_URL_RE.source, HTTP_URL_RE.flags)

  for (const match of text.matchAll(re)) {
    const raw = match[0]
    const start = match.index ?? 0
    if (start > lastIndex) {
      out.push({ type: 'text', value: text.slice(lastIndex, start) })
    }

    const punctMatch = raw.match(TRAILING_URL_PUNCT_RE)
    const trailing = punctMatch?.[0] ?? ''
    const candidate = trailing ? raw.slice(0, -trailing.length) : raw

    if (candidate && isSafeExternalUrl(candidate)) {
      out.push({ type: 'link', value: candidate })
      if (trailing) {
        out.push({ type: 'text', value: trailing })
      }
    } else {
      out.push({ type: 'text', value: raw })
    }

    lastIndex = start + raw.length
  }

  if (lastIndex < text.length) {
    out.push({ type: 'text', value: text.slice(lastIndex) })
  }

  return out.length > 0 ? out : [{ type: 'text', value: text }]
}

export function buildCommentBodySegments(
  body: string,
  mentionSubs: string[] | undefined,
  users: PortalUser[],
): CommentBodySegment[] {
  const mentionSegs = buildMentionSegments(body, mentionSubs ?? [], users)
  const out: CommentBodySegment[] = []
  for (const seg of mentionSegs) {
    if (seg.type === 'mark') {
      out.push(seg)
    } else {
      out.push(...splitTextWithSafeUrls(seg.value))
    }
  }
  return out
}

export function renderBodyWithMentionsNodes(
  body: string,
  mentionSubs: string[] | undefined,
  users: PortalUser[],
): ReactNode[] {
  const segments = buildCommentBodySegments(body, mentionSubs, users)
  return segments.map((seg, idx) => {
    if (seg.type === 'link') {
      return (
        <a
          key={idx}
          href={seg.value}
          target="_blank"
          rel="noopener noreferrer"
          className={styles.commentBodyLink}
          onClick={(e) => e.stopPropagation()}
        >
          {seg.value}
        </a>
      )
    }
    return <span key={idx}>{seg.value}</span>
  })
}
