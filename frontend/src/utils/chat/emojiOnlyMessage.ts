/** Максимум grapheme-эмодзи в сообщении для пасхалки. */
export const EMOJI_ONLY_MAX_COUNT = 3

/** Начальная скорость мяча (доля высоты поля / сек). */
export const EMOJI_PONG_SPEED_INITIAL = 1.7

/** Прирост скорости за каждое очко матча. */
export const EMOJI_PONG_SPEED_PER_POINT = 0.08

/** Максимальная скорость. */
export const EMOJI_PONG_SPEED_MAX = 3.2

/** Ширина ракетки относительно ширины поля. */
export const EMOJI_PONG_PADDLE_WIDTH_RATIO = 0.28

/** Высота ракетки относительно высоты поля. */
export const EMOJI_PONG_PADDLE_HEIGHT_RATIO = 0.028

/** Радиус «мяча»-эмодзи относительно меньшей стороны поля. */
export const EMOJI_PONG_BALL_RADIUS_RATIO = 0.055

/**
 * Верх игровой зоны (ниже шапки рекордов), доля высоты поля.
 */
export const EMOJI_PONG_PLAY_TOP_RATIO = 0.09

/** Побед до конца онлайн-матча. */
export const EMOJI_PONG_WINS_TO_FINISH = 5

/** Интервал синка state host→guest, мс. */
export const EMOJI_PONG_STATE_SYNC_MS = 20

/** Интервал синка ракетки guest→host, мс. */
export const EMOJI_PONG_PADDLE_SYNC_MS = 20

/** Название мини-игры в модалке. */
export const EMOJI_PONG_GAME_TITLE = 'Эмодзи-понг'

/** Ширина модалки игры, px. */
export const EMOJI_PONG_MODAL_MAX_WIDTH_PX = 560

/** Маркер тела сообщения со счётом (для разбора и особого рендера). */
const EMOJI_GAME_SCORE_BODY_RE = /^(.+?)\s+Игра:\s+(\d+)$/u

export type EmojiOnlyBody = {
  emojis: string[]
}

export type EmojiGameScoreBody = {
  emoji: string
  score: number
}

function segmentGraphemes(text: string): string[] {
  if (typeof Intl !== 'undefined' && 'Segmenter' in Intl) {
    const segmenter = new Intl.Segmenter(undefined, { granularity: 'grapheme' })
    return [...segmenter.segment(text)].map((s) => s.segment)
  }
  return Array.from(text)
}

/** Один grapheme является эмодзи (pictographic, флаг, keycap). */
export function isEmojiGrapheme(segment: string): boolean {
  if (!segment) return false
  if (/\p{Extended_Pictographic}/u.test(segment)) return true
  if (/^\p{Regional_Indicator}{2}$/u.test(segment)) return true
  if (/^[#*0-9]\uFE0F?\u20E3$/u.test(segment)) return true
  return false
}

/**
 * Разбирает тело сообщения: 1–3 эмодзи без другого текста.
 * Иначе возвращает null.
 */
export function parseEmojiOnlyBody(body: string): EmojiOnlyBody | null {
  const trimmed = body.trim()
  if (!trimmed) return null

  const graphemes = segmentGraphemes(trimmed)
  if (graphemes.length < 1 || graphemes.length > EMOJI_ONLY_MAX_COUNT) {
    return null
  }
  if (!graphemes.every(isEmojiGrapheme)) return null

  return { emojis: graphemes }
}

export function isEmojiOnlyMessage(body: string): boolean {
  return parseEmojiOnlyBody(body) != null
}

/** Текст обычного сообщения со счётом пасхалки (хранится в body). */
export function formatEmojiGameScoreMessage(emoji: string, score: number): string {
  return `${emoji} Игра: ${score}`
}

/** Разбор сообщения со счётом; иначе null. */
export function parseEmojiGameScoreMessage(body: string): EmojiGameScoreBody | null {
  const m = body.trim().match(EMOJI_GAME_SCORE_BODY_RE)
  if (!m) return null
  const score = Number(m[2])
  if (!Number.isFinite(score)) return null
  return { emoji: m[1]!, score }
}

/** Подпись для UI: кто сколько набрал (шрифт даты в пузыре). */
export function formatEmojiGameScoreCaption(authorLabel: string, score: number): string {
  return `${authorLabel}: ${score}`
}

/** Три цифры счёта, как в Instagram (025). */
export function formatEmojiGameScoreDigits(score: number): string {
  const n = Math.min(999, Math.max(0, Math.floor(score)))
  return String(n).padStart(3, '0')
}

type ScoreMessageLike = {
  author_sub: string
  body: string
  deleted_for_all_at?: string | null
}

/** Лучшие счёты по автору из сообщений пасхалки в чате. */
export function bestEmojiGameScoresByAuthor(
  messages: ScoreMessageLike[],
): Record<string, number> {
  const best: Record<string, number> = {}
  for (const m of messages) {
    if (m.deleted_for_all_at) continue
    const parsed = parseEmojiGameScoreMessage(m.body)
    if (!parsed) continue
    const prev = best[m.author_sub] ?? 0
    if (parsed.score > prev) best[m.author_sub] = parsed.score
  }
  return best
}
