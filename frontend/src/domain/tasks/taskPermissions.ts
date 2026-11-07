import type { PortalTask } from '../../types/task'

/** Соответствует ``user_can_edit_task`` на API: править может автор, исполнитель или portal_admin. */
export function userCanEditTask(
  task: Pick<PortalTask, 'creator_sub' | 'assignee_sub'> & {
    assignee_subs?: string[] | null
  },
  currentUserSub: string,
  isPortalAdmin = false,
): boolean {
  if (isPortalAdmin) return true
  if (task.creator_sub === currentUserSub) return true
  if (task.assignee_sub === currentUserSub) return true
  return (task.assignee_subs ?? []).includes(currentUserSub)
}

/** Соответствует ``user_can_change_task_assignees`` на API: автор или portal_admin. */
export function userCanChangeTaskAssignees(
  task: Pick<PortalTask, 'creator_sub' | 'assignee_sub'> & {
    assignee_subs?: string[] | null
  },
  currentUserSub: string,
  isPortalAdmin = false,
): boolean {
  if (isPortalAdmin) return true
  return task.creator_sub === currentUserSub
}

/** Соответствует ``user_can_delete_task`` на API: admin; автор tour-demo; менеджер — свои. */
export function userCanDeleteTask(
  task: Pick<PortalTask, 'creator_sub' | 'is_tour_demo'>,
  currentUserSub: string,
  isPortalAdmin = false,
  isManagerOrAdmin = false,
): boolean {
  if (isPortalAdmin) return true
  if (task.creator_sub !== currentUserSub) return false
  if (task.is_tour_demo) return true
  return isManagerOrAdmin
}
