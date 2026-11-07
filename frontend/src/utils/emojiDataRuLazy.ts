import type { EmojiMartData } from '@emoji-mart/data'

/**
 * Тяжёлый слой (emojibase ru + клон @emoji-mart/data) в отдельном чанке —
 * не тянем его в основной бандл до первого открытия пикера.
 */
export function loadEmojiMartDataWithRuSearch(): Promise<EmojiMartData> {
  return import('./emojiDataRu').then((m) => m.getEmojiMartDataWithRuSearch())
}
