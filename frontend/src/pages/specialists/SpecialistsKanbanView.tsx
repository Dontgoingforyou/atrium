import { useState } from 'react'
import type { UseMutationResult } from '@tanstack/react-query'

import { SpecialistKanbanBoard } from '../../components/specialists/SpecialistKanbanBoard'
import {
  findOwnBoardEntry,
  SPECIALIST_MOVE_NOT_ON_MY_BOARD,
} from '../../domain/specialists/specialistBoardPref'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import type { ManagerSpecialistEntry, SpecialistBoardPref, SpecialistColumn } from '../../types/specialist'
import type { SpecialistScope } from './specialistsPageUrl'
import type { KanbanInsertAnchor } from '../../domain/kanban/kanbanDisplayCommon'
import createFormStyles from '@/styles/modules/tasks/TasksPageCreateForm.module.css'

interface MoveMutationVars {
  specialistSub: string
  columnKey: string
  managerSub?: string
}

interface ReorderMutationVars {
  entryId: string
  columnKey: string
  anchor: KanbanInsertAnchor
  managerSub?: string
}

interface Props {
  scope: SpecialistScope
  columns: SpecialistColumn[]
  columnOrder: string[]
  boardPref: SpecialistBoardPref | null
  entries: ManagerSpecialistEntry[]
  boardEntriesMy: ManagerSpecialistEntry[]
  kanbanEntries: ManagerSpecialistEntry[]
  boardPending: boolean
  currentUserSub: string
  isAdmin: boolean
  isManager: boolean
  moveMutation: UseMutationResult<unknown, unknown, MoveMutationVars>
  reorderMutation: UseMutationResult<unknown, unknown, ReorderMutationVars>
  prefMutation: { isPending: boolean }
  addColumnMutation: UseMutationResult<unknown, unknown, { key: string; title: string; color: string; position: number }>
  updateColumnMutation: UseMutationResult<unknown, unknown, { id: string; data: { title?: string; color?: string } }>
  scheduleSpecialistColumnDelete: (columnId: string) => void
  onAddSpecialist?: (columnKey: string) => void
  onCardClick: ((entry: ManagerSpecialistEntry) => void) | undefined
  scheduleRemoveFromBoard: (args: { specialistSub: string; managerSub: string }) => void
  handlePersonalColumnReorder: (newOrder: string[]) => void
  toggleHiddenColumn: (columnKey: string) => void
  entryManagerSub: (entry: ManagerSpecialistEntry) => string | undefined
  resolveRemoveManagerSub: (entry: ManagerSpecialistEntry | undefined) => string | undefined
}

export function SpecialistsKanbanView({
  scope,
  columns,
  columnOrder,
  boardPref,
  entries,
  boardEntriesMy,
  kanbanEntries,
  boardPending,
  currentUserSub,
  isAdmin,
  isManager,
  moveMutation,
  reorderMutation,
  prefMutation,
  addColumnMutation,
  updateColumnMutation,
  scheduleSpecialistColumnDelete,
  onAddSpecialist,
  onCardClick,
  scheduleRemoveFromBoard,
  handlePersonalColumnReorder,
  toggleHiddenColumn,
  entryManagerSub,
  resolveRemoveManagerSub,
}: Props) {
  const notifyToast = useNotifyToast()
  const [showAllHiddenColumns, setShowAllHiddenColumns] = useState(false)
  const [personalBoardPanelOpen, setPersonalBoardPanelOpen] = useState(false)
  const [movingEntryId, setMovingEntryId] = useState<string | null>(null)

  function revealColumnIfHidden(columnKey: string) {
    if ((boardPref?.hidden_column_keys ?? []).includes(columnKey)) {
      toggleHiddenColumn(columnKey)
    }
  }

  if (boardPending) {
    return <p className="text-muted">Загрузка доски…</p>
  }

  function renderPersonalBar() {
    return (
      <>
        <div className={createFormStyles.kanbanPersonalBar}>
          <button
            type="button"
            className={createFormStyles.kanbanPersonalToggle}
            aria-expanded={personalBoardPanelOpen}
            onClick={() => setPersonalBoardPanelOpen((v) => !v)}
          >
            <span
              className={[
                createFormStyles.kanbanPersonalToggleChevron,
                personalBoardPanelOpen ? createFormStyles.kanbanPersonalToggleChevronOpen : '',
              ]
                .filter(Boolean)
                .join(' ')}
              aria-hidden
            />
            Моя доска
          </button>
          <label className={createFormStyles.kanbanPersonalCheckbox}>
            <input
              type="checkbox"
              checked={showAllHiddenColumns}
              onChange={(e) => setShowAllHiddenColumns(e.target.checked)}
            />
            Показать скрытые колонки
          </label>
          <span className={createFormStyles.kanbanPersonalHint}>
            Порядок колонок: перетащите шапку (значок «⋮⋮» и название), сохраняется только для вас.
          </span>
        </div>
        <div
          className={[
            createFormStyles.kanbanPersonalPanelShell,
            personalBoardPanelOpen ? createFormStyles.kanbanPersonalPanelShellOpen : '',
          ]
            .filter(Boolean)
            .join(' ')}
        >
          <div className={createFormStyles.kanbanPersonalPanelShellInner}>
            <div className={createFormStyles.kanbanPersonalPanel}>
              <p className={createFormStyles.kanbanPersonalPanelTitle}>Скрыть колонки на канбане</p>
              <div className={createFormStyles.kanbanPersonalChecks}>
                {columns.map((col) => (
                  <label key={col.id} className={createFormStyles.kanbanPersonalCheckRow}>
                    <input
                      type="checkbox"
                      checked={(boardPref?.hidden_column_keys ?? []).includes(col.key)}
                      onChange={() => toggleHiddenColumn(col.key)}
                      disabled={prefMutation.isPending}
                    />
                    <span>Скрыть «{col.title}»</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        </div>
      </>
    )
  }

  if (scope === 'my') {
    return (
      <>
        {renderPersonalBar()}
        <SpecialistKanbanBoard
          columns={columns}
          columnOrder={columnOrder}
          boardPref={boardPref}
          showAllHiddenColumns={showAllHiddenColumns}
          kanbanScrollStorageKey={`specialists-kanban-${scope}`}
          entries={kanbanEntries}
          onReorderEntry={(entryId, columnKey, anchor) => {
            reorderMutation.mutate({
              entryId,
              columnKey,
              anchor,
              managerSub: isAdmin ? currentUserSub : undefined,
            })
          }}
          onReorderColumns={handlePersonalColumnReorder}
          onMoveSpecialist={(specialistSub, columnKey) => {
            revealColumnIfHidden(columnKey)
            const entry = boardEntriesMy.find((e) => e.specialist_sub === specialistSub)
            if (entry) setMovingEntryId(entry.id)
            moveMutation.mutate(
              {
                specialistSub,
                columnKey,
                managerSub: entry ? entryManagerSub(entry) : undefined,
              },
              { onSettled: () => setMovingEntryId(null) },
            )
          }}
          movingEntryId={movingEntryId}
          onAddSpecialist={onAddSpecialist}
          onRemoveSpecialist={(specialistSub) => {
            const entry = boardEntriesMy.find((e) => e.specialist_sub === specialistSub)
            const managerSub = resolveRemoveManagerSub(entry)
            if (!managerSub) return
            scheduleRemoveFromBoard({ specialistSub, managerSub })
          }}
          canAddColumn={isAdmin}
          onAddColumn={isAdmin ? (data) => addColumnMutation.mutate(data) : undefined}
          canEditColumns={isAdmin}
          onUpdateColumn={(id, data) => updateColumnMutation.mutate({ id, data })}
          onDeleteColumn={(id) => scheduleSpecialistColumnDelete(id)}
          onCardClick={onCardClick}
        />
      </>
    )
  }

  return (
    <>
      {renderPersonalBar()}
      <SpecialistKanbanBoard
        columns={columns}
        columnOrder={columnOrder}
        boardPref={boardPref}
        showAllHiddenColumns={showAllHiddenColumns}
        kanbanScrollStorageKey={`specialists-kanban-${scope}`}
        entries={kanbanEntries}
        currentUserSub={currentUserSub}
        groupCardsBySpecialist
        showColumnAddButton={false}
        onReorderEntry={(entryId, columnKey, anchor) => {
          const moving = entries.find((entry) => entry.id === entryId)
          if (!moving || moving.manager_sub !== currentUserSub) {
            notifyToast(SPECIALIST_MOVE_NOT_ON_MY_BOARD)
            return
          }
          reorderMutation.mutate({
            entryId,
            columnKey,
            anchor,
            managerSub: isAdmin ? currentUserSub : undefined,
          })
        }}
        onReorderColumns={handlePersonalColumnReorder}
        onMoveSpecialist={(specialistSub, columnKey) => {
          revealColumnIfHidden(columnKey)
          const entry = findOwnBoardEntry(entries, specialistSub, currentUserSub)
          if (!entry) {
            notifyToast(SPECIALIST_MOVE_NOT_ON_MY_BOARD)
            return
          }
          setMovingEntryId(entry.id)
          moveMutation.mutate(
            {
              specialistSub,
              columnKey,
              managerSub: entryManagerSub(entry),
            },
            { onSettled: () => setMovingEntryId(null) },
          )
        }}
        movingEntryId={movingEntryId}
        onRemoveSpecialist={(specialistSub) => {
          const entry = entries.find(
            (e) => e.specialist_sub === specialistSub && e.manager_sub === currentUserSub,
          )
          if (!entry) return
          scheduleRemoveFromBoard({ specialistSub, managerSub: entry.manager_sub })
        }}
        canAddColumn={isAdmin}
        onAddColumn={isAdmin ? (data) => addColumnMutation.mutate(data) : undefined}
        canEditColumns={isAdmin}
        onUpdateColumn={(id, data) => updateColumnMutation.mutate({ id, data })}
        onDeleteColumn={(id) => scheduleSpecialistColumnDelete(id)}
        onCardClick={isAdmin || isManager ? onCardClick : undefined}
      />
    </>
  )
}
