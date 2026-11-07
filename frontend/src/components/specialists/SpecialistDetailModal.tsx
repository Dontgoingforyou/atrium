import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  deleteSpecialistFromPortal,
  getSpecialistJira,
  listManagersForSpecialist,
  listSpecialistLinks,
  listSpecialistNotes,
} from '../../api/specialists/specialistsApi'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { Modal } from '../ui/Modal'
import { ConfirmDialog } from '../ui/ConfirmDialog'
import { TaskDetailPanel } from '../tasks/detail/TaskDetailPanel'
import { countSpecialistNotes } from '../../domain/specialists/countSpecialistNotes'
import { panelContentCountWhenLoaded } from '../../domain/tasks/taskDetailPanelContent'
import type { ManagerSpecialistEntry, SpecialistColumn } from '../../types/specialist'
import {
  SPECIALISTS_DETAIL_ROOT_QUERY_KEY,
  SPECIALISTS_LIST_QUERY_KEY,
  SPECIALISTS_STUDENTS_ROOT_QUERY_KEY,
  specialistJiraQueryKey,
  specialistLinksQueryKey,
  specialistManagersQueryKey,
  specialistNotesQueryKey,
} from '../../pages/specialists/specialistQueryKeys'
import { SpecialistProfileSection } from './SpecialistProfileSection'
import { SpecialistManagersSection } from './SpecialistManagersSection'
import { SpecialistLinksSection } from './SpecialistLinksSection'
import { SpecialistCommentsSection } from './SpecialistCommentsSection'
import { SpecialistJiraSection } from './SpecialistJiraSection'
import modalStyles from '@/styles/modules/tasks/TaskDetailModal.module.css'
import styles from '@/styles/modules/specialists/SpecialistDetailModal.module.css'

type Props = {
  entry: ManagerSpecialistEntry
  currentUserSub: string
  isAdmin: boolean
  isManager: boolean
  columns: SpecialistColumn[]
  onClose: () => void
}

export function SpecialistDetailModal({ entry, currentUserSub, isAdmin, isManager, columns, onClose }: Props) {
  const queryClient = useQueryClient()
  const notifyToast = useNotifyToast()
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const canWrite = isAdmin || isManager
  const columnTitles = useMemo(
    () => new Map(columns.map((c) => [c.key, c.title])),
    [columns],
  )
  const displayName = entry.display_name ?? entry.specialist_sub

  const linksCountQuery = useQuery({
    queryKey: specialistLinksQueryKey(entry.specialist_sub),
    queryFn: () => listSpecialistLinks(entry.specialist_sub),
  })
  const notesCountQuery = useQuery({
    queryKey: specialistNotesQueryKey(entry.specialist_sub),
    queryFn: () => listSpecialistNotes(entry.specialist_sub),
  })
  const jiraQuery = useQuery({
    queryKey: specialistJiraQueryKey(entry.specialist_sub),
    queryFn: () => getSpecialistJira(entry.specialist_sub),
    enabled: canWrite,
  })
  const managersCountQuery = useQuery({
    queryKey: specialistManagersQueryKey(entry.specialist_sub),
    queryFn: () => listManagersForSpecialist(entry.specialist_sub),
    enabled: isAdmin,
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteSpecialistFromPortal(entry.specialist_sub),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SPECIALISTS_LIST_QUERY_KEY })
      void queryClient.invalidateQueries({ queryKey: SPECIALISTS_DETAIL_ROOT_QUERY_KEY })
      void queryClient.invalidateQueries({ queryKey: SPECIALISTS_STUDENTS_ROOT_QUERY_KEY })
      onClose()
    },
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e), { silent: true }),
  })

  return (
    <Modal title={displayName} maxWidth={960} onClose={onClose}>
      <div className={modalStyles.split} data-tour="specialists-detail">
        <div className={modalStyles.splitMain}>
          <TaskDetailPanel key={`${entry.specialist_sub}-spec-profile`} panelId="spec-profile" title="Профиль">
            <SpecialistProfileSection specialistSub={entry.specialist_sub} canWrite={canWrite} />
          </TaskDetailPanel>

          <TaskDetailPanel
            key={`${entry.specialist_sub}-spec-links`}
            panelId="spec-links"
            title="Ссылки"
            contentCount={panelContentCountWhenLoaded(
              linksCountQuery.isSuccess,
              linksCountQuery.data?.length,
            )}
          >
            <SpecialistLinksSection
              specialistSub={entry.specialist_sub}
              currentUserSub={currentUserSub}
              isAdmin={isAdmin}
              canWrite={canWrite}
            />
          </TaskDetailPanel>

          {canWrite && (
            <TaskDetailPanel
              key={`${entry.specialist_sub}-spec-jira`}
              panelId="spec-jira"
              title="Jira"
              contentCount={panelContentCountWhenLoaded(
                jiraQuery.isSuccess,
                jiraQuery.data?.jira_issue_key ? 1 : 0,
              )}
            >
              <SpecialistJiraSection specialistSub={entry.specialist_sub} />
            </TaskDetailPanel>
          )}

          <TaskDetailPanel
            key={`${entry.specialist_sub}-spec-comments`}
            panelId="spec-comments"
            title="Комментарии"
            contentCount={panelContentCountWhenLoaded(
              notesCountQuery.isSuccess,
              notesCountQuery.data ? countSpecialistNotes(notesCountQuery.data) : undefined,
            )}
          >
            <SpecialistCommentsSection
              specialistSub={entry.specialist_sub}
              currentUserSub={currentUserSub}
              isAdmin={isAdmin}
              canWrite={canWrite}
            />
          </TaskDetailPanel>

          {isAdmin && (
            <div className={styles.specialistDangerZone}>
              <button
                type="button"
                className={`btn-secondary ${styles.deleteSpecialistBtn}`}
                onClick={() => setDeleteConfirmOpen(true)}
              >
                Удалить специалиста из портала
              </button>
            </div>
          )}
        </div>

        <aside className={modalStyles.splitSide}>
          <TaskDetailPanel
            key={`${entry.specialist_sub}-spec-managers`}
            panelId="spec-managers"
            title="Менеджеры"
            contentCount={
              isAdmin
                ? panelContentCountWhenLoaded(
                    managersCountQuery.isSuccess,
                    managersCountQuery.data?.length,
                  )
                : undefined
            }
          >
            <SpecialistManagersSection
              specialistSub={entry.specialist_sub}
              currentUserSub={currentUserSub}
              isAdmin={isAdmin}
              isManager={isManager}
              boardEntry={entry}
              columnTitles={columnTitles}
              onManagerReassigned={onClose}
            />
          </TaskDetailPanel>
        </aside>
      </div>
      <ConfirmDialog
        open={deleteConfirmOpen}
        title="Удалить специалиста из портала?"
        message={`Удалить «${displayName}» из портала? Действие необратимо.`}
        confirmLabel="Удалить"
        cancelLabel="Отмена"
        destructive
        confirmSound="error"
        disabled={deleteMutation.isPending}
        onConfirm={() => deleteMutation.mutate()}
        onCancel={() => {
          if (!deleteMutation.isPending) setDeleteConfirmOpen(false)
        }}
      />
    </Modal>
  )
}
