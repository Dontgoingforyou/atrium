import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { listManagersForSpecialist, reassignBoardManager } from '../../api/specialists/specialistsApi'
import { UserMultiPicker } from '../common/UserMultiPicker'
import { UserPicker } from '../common/UserPicker'
import { UserAvatar } from '../ui/UserAvatar'
import { useSpecialistBoardUndo } from '../../hooks/useSpecialistBoardUndo'
import type { ManagerSpecialistEntry, SpecialistManagerRef } from '../../types/specialist'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { specialistManagersQueryKey } from '../../pages/specialists/specialistQueryKeys'
import styles from '@/styles/modules/specialists/SpecialistDetailModal.module.css'
import managerStyles from '@/styles/modules/specialists/SpecialistManagers.module.css'

type Props = {
  specialistSub: string
  currentUserSub: string
  isAdmin: boolean
  isManager: boolean
  boardEntry: ManagerSpecialistEntry
  columnTitles: Map<string, string>
  /** После смены менеджера у текущей записи доски — закрыть карточку. */
  onManagerReassigned?: () => void
}

export function SpecialistManagersSection({
  specialistSub, currentUserSub, isAdmin, isManager, boardEntry, columnTitles, onManagerReassigned,
}: Props) {
  const managersQk = specialistManagersQueryKey(specialistSub)

  const [actionError, setActionError] = useState('')
  const [reassignFromSub, setReassignFromSub] = useState<string | null>(null)
  const [addManagerSubs, setAddManagerSubs] = useState<string[]>([])
  /** Локально: менеджер добавил/убрал себя (карточка могла быть открыта с чужой доски). */
  const [myBoardOverride, setMyBoardOverride] = useState<boolean | null>(null)

  const { invalidateBoard, scheduleRemoveFromBoard, scheduleAddToBoard, scheduleAddManagersToBoard } =
    useSpecialistBoardUndo({ userSub: currentUserSub, isAdmin, specialistSub })

  const placeholder: SpecialistManagerRef[] = boardEntry.manager_sub
    ? [{
        manager_sub: boardEntry.manager_sub,
        manager_display_name: boardEntry.manager_display_name,
        column_key: boardEntry.column_key,
        status_id: boardEntry.status_id,
        status_title: boardEntry.status_title,
        status_color: boardEntry.status_color,
        created_at: boardEntry.created_at,
      }]
    : []

  const { data, isFetching, isError, error } = useQuery({
    queryKey: managersQk,
    queryFn: () => listManagersForSpecialist(specialistSub),
    enabled: isAdmin,
    gcTime: 0,
    placeholderData: placeholder,
  })
  const managers = data ?? placeholder

  const isOnMyBoardFromData = useMemo(
    () => managers.some((m) => m.manager_sub === currentUserSub),
    [managers, currentUserSub],
  )

  const isOnMyBoard = myBoardOverride ?? isOnMyBoardFromData

  function handleAddManagers() {
    setActionError('')
    const existingManagerSubs = new Set(managers.map((m) => m.manager_sub))
    scheduleAddManagersToBoard({
      specialistSub,
      columnKey: boardEntry.column_key,
      managerSubs: addManagerSubs,
      existingManagerSubs,
    })
    setAddManagerSubs([])
  }

  const reassignMutation = useMutation({
    mutationFn: ({ from, to }: { from: string; to: string }) =>
      reassignBoardManager(specialistSub, { from_manager_sub: from, to_manager_sub: to }),
    onSuccess: (_data, { from }) => {
      setActionError('')
      setReassignFromSub(null)
      invalidateBoard()
      if (from === boardEntry.manager_sub) {
        onManagerReassigned?.()
      }
    },
    onError: (e: unknown) => setActionError(userFacingMessageFromUnknown(e)),
  })

  const busy = reassignMutation.isPending

  function handleToggleMyBoard() {
    if (!currentUserSub) return
    if (isOnMyBoard) {
      setMyBoardOverride(false)
      scheduleRemoveFromBoard({
        specialistSub,
        managerSub: currentUserSub,
        message: 'Специалист отвязан от вашей доски',
        onUndoClick: () => setMyBoardOverride(true),
      })
      return
    }
    setMyBoardOverride(true)
    scheduleAddToBoard({
      specialistSub,
      columnKey: boardEntry.column_key,
      managerSub: currentUserSub,
      specialist: { display_name: boardEntry.display_name, email: boardEntry.email, avatar_url: boardEntry.avatar_url },
      message: 'Специалист добавлен на вашу доску',
      onUndoClick: () => setMyBoardOverride(false),
    })
  }

  return (
    <div>
      {isManager && !isAdmin && (
        <div className={managerStyles.managerToggleRow}>
          <button
            type="button"
            className={isOnMyBoard ? managerStyles.dangerBtn : 'btn-primary'}
            disabled={busy}
            onClick={handleToggleMyBoard}
          >
            {isOnMyBoard ? 'Убрать с доски' : 'Добавить к себе'}
          </button>
        </div>
      )}

      {isAdmin && (
        <div className={managerStyles.managerAddBlock}>
          <span className={managerStyles.managerReassignLabel}>Добавить менеджеров</span>
          <UserMultiPicker
            value={addManagerSubs}
            onChange={setAddManagerSubs}
            placeholder="Выберите менеджеров…"
          />
          <button
            type="button"
            className="btn-primary"
            disabled={busy || addManagerSubs.length === 0}
            onClick={handleAddManagers}
          >
            Добавить на доску
          </button>
        </div>
      )}

      {actionError && <p className="form-error">{actionError}</p>}
      {isError && isAdmin ? (
        <p className="text-danger" role="alert">
          {userFacingMessageFromUnknown(error)}
        </p>
      ) : (
        <>
          {isFetching && isAdmin && <p className={styles.fetchingHint}>Обновление…</p>}

          {managers.length === 0 ? (
            <p className={styles.emptyHint}>Специалист не закреплён ни за одним менеджером</p>
          ) : (
            <ul className={managerStyles.managerList}>
              {managers.map((m) => (
                <li key={m.manager_sub} className={managerStyles.managerRow}>
                  <div className={managerStyles.managerTop}>
                    <div className={managerStyles.managerInfo}>
                      <span className={managerStyles.managerNameRow}>
                        <UserAvatar
                      label={m.manager_display_name ?? m.manager_sub}
                      imageUrl={m.manager_avatar_url}
                      focalX={m.manager_avatar_focal_x}
                      focalY={m.manager_avatar_focal_y}
                      size="sm"
                    />
                    <span className={managerStyles.managerName}>{m.manager_display_name ?? m.manager_sub}</span>
                  </span>
                  {m.status_title && (
                    <span className={managerStyles.managerStatus}>
                      {m.status_color && <span style={{ color: m.status_color }}>● </span>}
                      {m.status_title}
                    </span>
                  )}
                  <span className={managerStyles.managerMeta}>{columnTitles.get(m.column_key) ?? m.column_key}</span>
                </div>
              </div>
              {isAdmin && (
                <div className={managerStyles.managerActions}>
                  <button
                    type="button"
                    className={managerStyles.managerActionBtn}
                    disabled={busy}
                    onClick={() =>
                      setReassignFromSub(reassignFromSub === m.manager_sub ? null : m.manager_sub)
                    }
                  >
                    {reassignFromSub === m.manager_sub ? 'Отмена' : 'Сменить менеджера'}
                  </button>
                  <button
                    type="button"
                    className={managerStyles.unlinkBtn}
                    disabled={busy}
                    onClick={() => {
                      scheduleRemoveFromBoard({
                        specialistSub,
                        managerSub: m.manager_sub,
                        message: 'Менеджер отвязан от специалиста',
                      })
                    }}
                  >
                    Отвязать
                  </button>
                </div>
              )}
              {isAdmin && reassignFromSub === m.manager_sub && (
                <div className={managerStyles.managerReassignPanel}>
                  <span className={managerStyles.managerReassignLabel}>Новый менеджер</span>
                  <UserPicker
                    value=""
                    placeholder="Выберите менеджера…"
                    onChange={(sub) => {
                      if (sub && sub !== m.manager_sub) {
                        reassignMutation.mutate({ from: m.manager_sub, to: sub })
                      }
                    }}
                  />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
        </>
      )}
    </div>
  )
}
