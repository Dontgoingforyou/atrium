export function formatSimilarityBadge(score: number): string {
  return `похожесть ${Math.round(score * 100)}%`
}
