/** Подпись задачи в drawer «Связи тега». */
export function tagUsageTaskLabel(task: { number: number | null; title: string }): string {
  const num = task.number != null ? `#${task.number} ` : ''
  const title = task.title.trim() || 'Без названия'
  return `${num}${title}`
}
