import { CHAT_FREQUENT_REACTIONS_KEY } from '../../constants/chatStorage'

/** Частые реакции: локально + набор по умолчанию. */

const DEFAULT_REACTIONS = ['👍', '❤️', '🔥', '😂', '🤔', '👏', '😢', '😮']
const REACTION_EMOJI_MAX_LENGTH = 32

export function getQuickReactionEmojis(): string[] {
  try {
    const raw = localStorage.getItem(CHAT_FREQUENT_REACTIONS_KEY)
    if (!raw) return [...DEFAULT_REACTIONS]
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed) || parsed.length === 0) return [...DEFAULT_REACTIONS]
    const seen = new Set<string>()
    const out: string[] = []
    for (const x of parsed) {
      const e = String(x).trim()
      if (e && e.length <= REACTION_EMOJI_MAX_LENGTH && !seen.has(e)) {
        seen.add(e)
        out.push(e)
        if (out.length >= 24) break
      }
    }
    for (const d of DEFAULT_REACTIONS) {
      if (out.length >= 8) break
      if (!seen.has(d)) {
        seen.add(d)
        out.push(d)
      }
    }
    return out.slice(0, 8)
  } catch {
    return [...DEFAULT_REACTIONS]
  }
}

export function recordReactionEmojiUse(emoji: string): void {
  const key = emoji.trim()
  if (!key || key.length > REACTION_EMOJI_MAX_LENGTH) return
  try {
    const raw = localStorage.getItem(CHAT_FREQUENT_REACTIONS_KEY)
    const arr: string[] = raw ? (JSON.parse(raw) as string[]) : []
    const next = [key, ...arr.filter((e) => e !== key)].slice(0, 32)
    localStorage.setItem(CHAT_FREQUENT_REACTIONS_KEY, JSON.stringify(next))
  } catch {
    /* ignore quota / private mode */
  }
}
