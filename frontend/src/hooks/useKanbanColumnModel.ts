import { useMemo } from 'react'
import { computeKanbanDisplay } from '../domain/tasks/taskBoardPref'
import type { PortalTask, PortalTaskColumn, TaskBoardPref } from '../types/task'

/**
 * Модель колонок и задач для канбана: обёртка над {@link computeKanbanDisplay}
 * (единый источник правды вместе с {@link KanbanBoard} при отсутствии явных override).
 */
export function useKanbanColumnModel(
  columns: PortalTaskColumn[],
  boardPref: TaskBoardPref | null | undefined,
  tasks: PortalTask[],
  showAllHiddenColumns: boolean,
) {
  return useMemo(
    () => computeKanbanDisplay(columns, boardPref ?? null, tasks, showAllHiddenColumns),
    [columns, boardPref, tasks, showAllHiddenColumns],
  )
}
