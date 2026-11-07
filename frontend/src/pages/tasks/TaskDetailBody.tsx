import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router'

import { TaskComments } from '../../components/tasks/detail/TaskComments'
import { TaskContextLinksEditor } from '../../components/tasks/detail/TaskContextLinksEditor'
import { TaskDetailPanel } from '../../components/tasks/detail/TaskDetailPanel'
import type { TaskDetailPanelId } from '../../components/tasks/detail/taskDetailPanelState'
import { TaskFiles } from '../../components/tasks/detail/TaskFiles'
import { TaskLinks } from '../../components/tasks/detail/TaskLinks'
import { PageViewersBanner } from '../../components/common/PageViewersBanner'
import {
  countCommentsPanelContent,
  countLinksPanelContent,
  panelContentCountWhenLoaded,
} from '../../domain/tasks/taskDetailPanelContent'
import { userCanChangeTaskAssignees, userCanDeleteTask, userCanEditTask } from '../../domain/tasks/taskPermissions'
import { useTaskPageViewers } from '../../hooks/useTaskPageViewers'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { HistoryBlock } from './HistoryBlock'
import { SubtasksSection } from './SubtasksSection'
import { TaskDetailEditor } from './TaskDetailEditor'
import { buildTaskOpenNavState } from './taskBackNav'
import { useTaskDetailData } from './useTaskDetailData'
import pageStyles from '@/styles/modules/tasks/TaskDetailPage.module.css'
import modalStyles from '@/styles/modules/tasks/TaskDetailModal.module.css'

type Layout = 'page' | 'modal'

type PanelIds = {
  comments: TaskDetailPanelId
  extLinks: TaskDetailPanelId
  files: TaskDetailPanelId
  links: TaskDetailPanelId
  subtasks: TaskDetailPanelId
  history: TaskDetailPanelId
}

const PAGE_PANEL_IDS: PanelIds = {
  comments: 'comments',
  extLinks: 'extLinks',
  files: 'files',
  links: 'links',
  subtasks: 'subtasks',
  history: 'history',
}

const MODAL_PANEL_IDS: PanelIds = {
  comments: 'modal-comments',
  extLinks: 'modal-ext-links',
  files: 'modal-files',
  links: 'modal-links',
  subtasks: 'modal-subtasks',
  history: 'modal-history',
}

type Props = {
  taskId: string
  layout: Layout
  onDelete: () => void
  onScheduleDelete?: (taskId: string) => void
  /** Навигация к другой задаче внутри модалки (стек истории). */
  onOpenTaskDetail?: (id: string) => void
  /** Кнопка «← Назад» в модалке при глубине стека > 1. */
  toolbarLeading?: ReactNode
}

/**
 * Общая раскладка панелей деталей задачи (страница и модалка).
 */
export function TaskDetailBody({
  taskId,
  layout,
  onDelete,
  onScheduleDelete,
  onOpenTaskDetail,
  toolbarLeading,
}: Props) {
  const location = useLocation()
  const taskNavState = buildTaskOpenNavState(location)
  const data = useTaskDetailData({ taskId })
  const viewers = useTaskPageViewers(taskId)
  const {
    isPortalAdmin,
    isManagerOrAdmin,
    currentUserSub,
    task,
    taskQuery,
    documentId,
    setHistoryOpen,
    historyLimit,
    setHistoryLimit,
    historyQuery,
    commentsCountQuery,
    extLinksCountQuery,
    filesCountQuery,
    subtasksCountQuery,
    portalUsers,
    resolveUserSub,
    resolveDocumentTitle,
    resolveChatTitle,
  } = data

  if (taskQuery.isPending) {
    return <p className="text-muted">Загрузка…</p>
  }
  if (taskQuery.isError || !task) {
    return <p className="text-danger">{userFacingMessageFromUnknown(taskQuery.error)}</p>
  }

  const shell = layout === 'modal' ? modalStyles : pageStyles
  const panelIds = layout === 'modal' ? MODAL_PANEL_IDS : PAGE_PANEL_IDS

  const parentLink =
    task.parent_task_id != null ? (
      layout === 'modal' && onOpenTaskDetail ? (
        <Link
          to={`/tasks/${task.parent_task_id}`}
          state={taskNavState}
          className={pageStyles.linkMuted}
          onClick={(e) => {
            e.preventDefault()
            onOpenTaskDetail(task.parent_task_id!)
          }}
        >
          ↑ Родительская задача
        </Link>
      ) : (
        <Link
          to={`/tasks/${task.parent_task_id}`}
          state={taskNavState}
          className={pageStyles.linkMuted}
        >
          ↑ Родительская задача
        </Link>
      )
    ) : null

  const editor = (
    <TaskDetailEditor
      key={task.id}
      task={task}
      taskId={taskId}
      canDelete={userCanDeleteTask(task, currentUserSub, isPortalAdmin, isManagerOrAdmin)}
      canEdit={userCanEditTask(task, currentUserSub, isPortalAdmin)}
      canEditAssignees={userCanChangeTaskAssignees(task, currentUserSub, isPortalAdmin)}
      onDelete={onDelete}
      onScheduleDelete={onScheduleDelete}
    />
  )

  const commentsPanel = (
    <TaskDetailPanel
      key={`${taskId}-${panelIds.comments}`}
      panelId={panelIds.comments}
      title="Комментарии"
      tourAnchor={layout === 'page' ? 'task-detail-comments' : undefined}
      contentCount={
        commentsCountQuery.isSuccess
          ? countCommentsPanelContent(commentsCountQuery.data)
          : undefined
      }
    >
      <TaskComments
        taskId={taskId}
        currentUserSub={currentUserSub}
        resolveUserSub={resolveUserSub}
      />
    </TaskDetailPanel>
  )

  const extLinksPanel = (
    <TaskDetailPanel
      key={`${taskId}-${panelIds.extLinks}`}
      panelId={panelIds.extLinks}
      title="Ссылки"
      tourAnchor={layout === 'page' ? 'task-detail-links' : undefined}
      contentCount={panelContentCountWhenLoaded(
        extLinksCountQuery.isSuccess,
        extLinksCountQuery.data?.length,
      )}
    >
      <TaskLinks
        taskId={taskId}
        currentUserSub={currentUserSub}
        isPortalAdmin={isPortalAdmin}
      />
    </TaskDetailPanel>
  )

  const filesPanel = (
    <TaskDetailPanel
      key={`${taskId}-${panelIds.files}`}
      panelId={panelIds.files}
      title="Файлы"
      tourAnchor={layout === 'page' ? 'task-detail-files' : undefined}
      contentCount={panelContentCountWhenLoaded(
        filesCountQuery.isSuccess,
        filesCountQuery.data?.length,
      )}
    >
      <TaskFiles
        taskId={taskId}
        currentUserSub={currentUserSub}
        isPortalAdmin={isPortalAdmin}
      />
    </TaskDetailPanel>
  )

  const linksPanel = (
    <TaskDetailPanel
      key={`${taskId}-${panelIds.links}`}
      panelId={panelIds.links}
      title="Связи"
      contentCount={countLinksPanelContent({
        hasDocument: documentId != null,
        hasParent: task.parent_task_id != null,
        subtasksLoaded: subtasksCountQuery.isSuccess,
        subtaskCount: subtasksCountQuery.data?.length ?? 0,
      })}
    >
      <TaskContextLinksEditor key={task.id} task={task} taskId={taskId} />
    </TaskDetailPanel>
  )

  const subtasksPanel = (
    <TaskDetailPanel
      key={`${taskId}-${panelIds.subtasks}`}
      panelId={panelIds.subtasks}
      title="Подзадачи"
      tourAnchor={layout === 'page' ? 'task-detail-subtasks' : undefined}
      contentCount={panelContentCountWhenLoaded(
        subtasksCountQuery.isSuccess,
        subtasksCountQuery.data?.length,
      )}
    >
      <SubtasksSection
        taskId={taskId}
        parentTask={task}
        portalUsers={portalUsers}
        onOpenTaskDetail={onOpenTaskDetail}
        taskNavState={taskNavState}
      />
    </TaskDetailPanel>
  )

  const historyPanel = (
    <TaskDetailPanel
      key={`${taskId}-${panelIds.history}`}
      panelId={panelIds.history}
      title="История изменений"
      contentCount={panelContentCountWhenLoaded(
        historyQuery.isSuccess,
        historyQuery.data?.length,
      )}
      onOpenChange={setHistoryOpen}
    >
      {historyQuery.isPending ? (
        <p className="text-muted">Загрузка…</p>
      ) : historyQuery.isError ? (
        <p className="text-danger">{userFacingMessageFromUnknown(historyQuery.error)}</p>
      ) : (
        <>
          <HistoryBlock
            entries={historyQuery.data ?? []}
            resolveUserSub={resolveUserSub}
            resolveDocumentTitle={resolveDocumentTitle}
            resolveChatTitle={resolveChatTitle}
          />
          {(historyQuery.data?.length ?? 0) >= historyLimit && (
            <button
              type="button"
              className={`btn-secondary ${pageStyles.historyLoadMore}`}
              onClick={() => setHistoryLimit((l) => l + 100)}
              disabled={historyQuery.isFetching}
            >
              {historyQuery.isFetching ? 'Загрузка…' : 'Загрузить ещё'}
            </button>
          )}
        </>
      )}
    </TaskDetailPanel>
  )

  return (
    <div>
      {(toolbarLeading || parentLink) && (
        <div className={pageStyles.toolbar}>
          {toolbarLeading}
          {parentLink}
        </div>
      )}

      {layout === 'page' ? (
        <div className={shell.split}>
          <div className={pageStyles.splitMain}>
            <PageViewersBanner viewers={viewers} currentUserSub={currentUserSub} />
            {editor}
            {commentsPanel}
            {extLinksPanel}
            {filesPanel}
          </div>
          <aside className={shell.splitSide}>
            {subtasksPanel}
            {linksPanel}
            {historyPanel}
          </aside>
        </div>
      ) : (
        <div className={shell.split}>
          <div className={modalStyles.splitMain}>
            <PageViewersBanner viewers={viewers} currentUserSub={currentUserSub} />
            {editor}
            {commentsPanel}
            {extLinksPanel}
            {filesPanel}
          </div>
          <aside className={shell.splitSide}>
            {subtasksPanel}
            {linksPanel}
            {historyPanel}
          </aside>
        </div>
      )}
    </div>
  )
}
