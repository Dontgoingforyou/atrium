/**
 * Скачивание `Blob` как файла в браузере (экспорт CSV/TXT/XLSX и т.п.).
 *
 * Общий хелпер для API-функций экспорта — не дублировать парсинг `Content-Disposition`
 * и связку `URL.createObjectURL` + `<a>.click()` в каждом `*Api.ts`.
 */

/** Извлекает имя файла из заголовка `Content-Disposition`, иначе — `fallback`. */
export function filenameFromContentDisposition(
  contentDisposition: string | null,
  fallback: string,
): string {
  const match = (contentDisposition ?? '').match(/filename="?([^";]+)"?/)
  return match?.[1] ?? fallback
}

/** Инициирует скачивание `blob` браузером под именем `filename`. */
export function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
