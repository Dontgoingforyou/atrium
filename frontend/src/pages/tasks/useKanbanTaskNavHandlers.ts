import type { MutableRefObject, MouseEvent } from 'react'
import { useLocation, useNavigate } from 'react-router'

import { buildTaskOpenNavState } from './taskBackNav'
import { handleRichTextContainerClick } from '../../utils/html/richTextLinkClick'

export function useKanbanTaskNavHandlers(
  taskId: string,
  suppressNavAfterDragRef: MutableRefObject<string | null>,
  onOpenTaskDetail?: (taskId: string) => void,
) {
  const navigate = useNavigate()
  const location = useLocation()
  const navState = buildTaskOpenNavState(location)

  function handleTitleClick(e: MouseEvent<HTMLAnchorElement>) {
    if (suppressNavAfterDragRef.current === taskId) {
      e.preventDefault()
      suppressNavAfterDragRef.current = null
      return
    }
    if (onOpenTaskDetail && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
      e.preventDefault()
      onOpenTaskDetail(taskId)
    }
  }

  function handleBodyClick(e: MouseEvent<HTMLElement>) {
    handleRichTextContainerClick(e, () => {
      if (suppressNavAfterDragRef.current === taskId) {
        suppressNavAfterDragRef.current = null
        return
      }
      if (onOpenTaskDetail) {
        onOpenTaskDetail(taskId)
        return
      }
      navigate(`/tasks/${taskId}`, { state: navState })
    })
  }

  return { handleTitleClick, handleBodyClick, navState }
}
