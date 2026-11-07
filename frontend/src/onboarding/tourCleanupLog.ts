const SILENT_CLEANUP_MESSAGES = new Set([
  'Запрошенные данные не найдены.',
  'Недостаточно прав для этого действия.',
  'Не удалось связаться с сервером. Проверьте сеть.',
])


export function warnTourCleanupError(label: string, e: unknown): void {
  if (!import.meta.env.DEV) return
  if (e instanceof Error && SILENT_CLEANUP_MESSAGES.has(e.message)) return
  console.warn(`[guided-tour cleanup] ${label}`, e)
}
