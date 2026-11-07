export type MessageInsightRow = {
  user_sub: string
  at: string
  kind: 'reaction' | 'read'
  emoji?: string
}

export function pluralRu(count: number, one: string, few: string, many: string): string {
  const n = Math.abs(count) % 100
  const n1 = n % 10
  if (n > 10 && n < 20) return many
  if (n1 === 1) return one
  if (n1 >= 2 && n1 <= 4) return few
  return many
}

export function viewsLabel(count: number): string {
  return `${count} ${pluralRu(count, 'просмотр', 'просмотра', 'просмотров')}`
}

export function mergeInsightRows(
  reactorsByEmoji: { emoji: string; reactors: { user_sub: string; reacted_at: string }[] }[],
  readers: { user_sub: string; read_at: string }[] | undefined,
): MessageInsightRow[] {
  const bySub = new Map<string, MessageInsightRow>()
  for (const group of reactorsByEmoji) {
    for (const r of group.reactors) {
      const prev = bySub.get(r.user_sub)
      if (!prev || prev.kind === 'read' || r.reacted_at > prev.at) {
        bySub.set(r.user_sub, {
          user_sub: r.user_sub,
          at: r.reacted_at,
          kind: 'reaction',
          emoji: group.emoji,
        })
      }
    }
  }
  for (const r of readers ?? []) {
    if (bySub.has(r.user_sub)) continue
    bySub.set(r.user_sub, {
      user_sub: r.user_sub,
      at: r.read_at,
      kind: 'read',
    })
  }
  return [...bySub.values()].sort((a, b) => (a.at < b.at ? 1 : a.at > b.at ? -1 : 0))
}
