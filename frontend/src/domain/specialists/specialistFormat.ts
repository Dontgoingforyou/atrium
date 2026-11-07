export function formatSyncedAt(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return d.toLocaleString('ru-RU')
  } catch {
    return iso
  }
}

export function formatBirthdate(iso: string | null | undefined): string {
  if (!iso) return ''
  const [y, m, d] = iso.split('-')
  if (!d || !m || !y) return iso
  return `${d}-${m}-${y}`
}
