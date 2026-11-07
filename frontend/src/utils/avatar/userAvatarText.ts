/** Инициалы для запасного отображения аватара (1–2 символа). */
export function initialsFromLabel(label: string): string {
  const t = label.trim()
  if (!t) return '?'
  const parts = t.split(/\s+/).filter(Boolean)
  if (parts.length >= 2) {
    return (parts[0]!.charAt(0) + parts[1]!.charAt(0)).toUpperCase()
  }
  if (t.length >= 2) {
    return t.slice(0, 2).toUpperCase()
  }
  return t.charAt(0).toUpperCase()
}
