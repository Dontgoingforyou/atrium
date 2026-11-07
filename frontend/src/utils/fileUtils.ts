/** Утилиты для работы с файлами вложений (иконки, размеры). */

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`
}

/**
 * Иконка-эмодзи для типа содержимого файла (по content_type).
 * Используется для отображения скачанных вложений в ленте сообщений.
 */
export function fileIcon(contentType: string): string {
  if (contentType.startsWith('image/')) return '🖼'
  if (contentType === 'application/pdf') return '📕'
  if (
    contentType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
    contentType === 'application/msword'
  )
    return '📝'
  if (
    contentType === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
    contentType === 'application/vnd.ms-excel'
  )
    return '📊'
  if (
    contentType === 'application/vnd.openxmlformats-officedocument.presentationml.presentation' ||
    contentType === 'application/vnd.ms-powerpoint'
  )
    return '📈'
  if (contentType.startsWith('video/')) return '🎬'
  if (contentType.startsWith('audio/')) return '🎵'
  if (contentType === 'application/zip' || contentType === 'application/x-rar-compressed') return '🗜'
  return '📄'
}

/**
 * Иконка-эмодзи для типа файла объекта `File` (по file.type).
 * Используется для предпросмотра прикреплённых (ещё не загруженных) файлов.
 */
export function fileChipIcon(file: File): string {
  return fileIcon(file.type)
}
