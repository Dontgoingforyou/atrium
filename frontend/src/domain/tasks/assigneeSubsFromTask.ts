/** Исполнители карточки: полный список, без среза до первого. */
export function assigneeSubsFromTask(task: {
  assignee_subs?: string[] | null
  assignee_sub?: string | null
}): string[] {
  if (task.assignee_subs?.length) {
    return [...task.assignee_subs]
  }
  if (task.assignee_sub) {
    return [task.assignee_sub]
  }
  return []
}
