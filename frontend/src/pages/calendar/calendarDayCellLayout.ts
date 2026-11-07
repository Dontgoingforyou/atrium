/** Высота чипа события (см. .eventChip в CalendarPage.module.css). */
export const CHIP_HEIGHT_PX = 20
/** Вертикальный gap между чипами (.dayEvents gap). */
export const CHIP_GAP_PX = 2
/** Высота кнопки «+N событий» (.dayMore). */
export const MORE_BTN_HEIGHT_PX = 20
/** Верхняя граница числа чипов в свёрнутой ячейке на очень высоких рядах. */
export const MAX_COLLAPSED_CHIPS = 5

/**
 * Сколько чипов показать до «+N», исходя из высоты контейнера `.dayEvents`.
 * Если все события влезают — показываем все (кнопки нет).
 * Иначе резервируем место под кнопку «+N».
 */
export function maxVisibleChips(containerHeight: number, total: number): number {
  if (total <= 0) return 0
  if (containerHeight <= 0) {
    return Math.min(total, MAX_COLLAPSED_CHIPS)
  }

  const slot = CHIP_HEIGHT_PX + CHIP_GAP_PX
  const fitsAll = Math.floor((containerHeight + CHIP_GAP_PX) / slot)
  if (fitsAll >= total) {
    return Math.min(total, MAX_COLLAPSED_CHIPS)
  }

  const withMore = Math.floor((containerHeight - MORE_BTN_HEIGHT_PX + CHIP_GAP_PX) / slot)
  return Math.max(0, Math.min(withMore, MAX_COLLAPSED_CHIPS, total - 1))
}
