import type { Emoji, EmojiMartData } from '@emoji-mart/data'
import baseData from '@emoji-mart/data'
import emojibaseRu from 'emojibase-data/ru/compact.json'

const SKIN_TONE = new Set(['1F3FB', '1F3FC', '1F3FD', '1F3FE', '1F3FF'])

type EmojibaseRow = {
  hexcode: string
  label?: string
  tags?: string[]
  skins?: EmojibaseRow[]
}

function wordsForRow(row: EmojibaseRow): string[] {
  const words: string[] = []
  if (row.label) {
    for (const w of row.label.split(/[:\s,]+/)) {
      const t = w.trim()
      if (t) words.push(t)
    }
  }
  if (row.tags) {
    for (const t of row.tags) {
      if (t?.trim()) words.push(t.trim())
    }
  }
  return words
}

function buildRuHexMap(): Map<string, string[]> {
  const m = new Map<string, string[]>()
  const rows: EmojibaseRow[] = Array.isArray(emojibaseRu) ? emojibaseRu : Object.values(emojibaseRu as object)
  for (const row of rows) {
    if (!row?.hexcode) continue
    const baseWords = wordsForRow(row)
    if (baseWords.length) m.set(String(row.hexcode).toUpperCase(), baseWords)
    if (row.skins) {
      for (const s of row.skins) {
        if (!s?.hexcode) continue
        const sw = wordsForRow(s)
        const merged = [...new Set([...baseWords, ...sw])]
        m.set(String(s.hexcode).toUpperCase(), merged)
      }
    }
  }
  return m
}

function ruLookupWords(map: Map<string, string[]>, unified: string): string[] {
  const u0 = unified.toUpperCase()
  const segs0 = u0.split('-').filter((s) => s !== 'FE0F')
  const candidates: string[] = [u0, segs0.join('-')]

  const segs1 = segs0.filter((s) => !SKIN_TONE.has(s))
  if (segs1.length !== segs0.length) candidates.push(segs1.join('-'))

  for (const c of candidates) {
    const w = map.get(c)
    if (w) return w
  }
  return []
}

let cached: EmojiMartData | null = null

/**
 * @emoji-mart ищет только по английским name/keywords; locale/ru i18n не меняют индекс.
 * Подмешиваем label и tags из emojibase «ru/compact» в keywords, чтобы поиск срабогал и по-русски.
 */
export function getEmojiMartDataWithRuSearch(): EmojiMartData {
  if (cached) return cached
  const data = JSON.parse(JSON.stringify(baseData)) as EmojiMartData
  const ruMap = buildRuHexMap()

  for (const id of Object.keys(data.emojis)) {
    const emoji = data.emojis[id] as Emoji
    const unified = emoji.skins[0]?.unified
    if (!unified) continue
    const extra = ruLookupWords(ruMap, unified)
    if (!extra.length) continue
    const next = new Set(emoji.keywords ?? [])
    for (const w of extra) next.add(w.toLowerCase())
    emoji.keywords = Array.from(next)
    delete (emoji as Emoji & { search?: string }).search
  }
  cached = data
  return data
}
