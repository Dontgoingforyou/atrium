import { useEffect, useMemo, useState } from 'react'
import { Navigate } from 'react-router'

import { useAuthStore } from '../../store/authStore'
import { isUserManagerOrAdmin } from '@/domain/auth/authRoles'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { useSpecialistBoardUndo } from '../../hooks/useSpecialistBoardUndo'
import { AddSpecialistModal } from '../../components/specialists/AddSpecialistModal'
import { SpecialistDetailModal } from '../../components/specialists/SpecialistDetailModal'
import type { ManagerSpecialistEntry } from '../../types/specialist'
import { useSpecialistsBoardWebSocket } from './useSpecialistsBoardWebSocket'
import { SpecialistsAllScopeSection } from './SpecialistsAllScopeSection'
import { SpecialistsMyListSection } from './SpecialistsMyListSection'
import { SpecialistsFiltersPanel } from './SpecialistsFiltersPanel'
import { useSpecialistsPageFilters } from './useSpecialistsPageFilters'
import { useSpecialistsPageData, SPECIALISTS_PAGE_SIZE } from './useSpecialistsPageData'
import { SpecialistsKanbanView } from './SpecialistsKanbanView'
import taskShell from '@/styles/modules/tasks/TasksPageShell.module.css'
import styles from '@/styles/modules/specialists/SpecialistsPage.module.css'

function scrollSpecialistColumnIntoView(columnKey: string) {
  document
    .querySelector(`[data-kanban-status="${CSS.escape(columnKey)}"]`)
    ?.scrollIntoView({ inline: 'nearest', block: 'nearest' })
}

function findEntryBySpecialistSub(
  list: ManagerSpecialistEntry[],
  specialistSub: string,
  currentUserSub: string | undefined,
): ManagerSpecialistEntry | null {
  const own = currentUserSub
    ? list.find((e) => e.specialist_sub === specialistSub && e.manager_sub === currentUserSub)
    : undefined
  return own ?? list.find((e) => e.specialist_sub === specialistSub) ?? null
}

export function SpecialistsPage() {
  const user = useAuthStore((s) => s.user)
  const canAccess = user
    ? isUserManagerOrAdmin(user)
    : false
  const isAdmin = Boolean(user?.is_portal_admin)
  const isManager = Boolean(user && isUserManagerOrAdmin(user) && !user.is_portal_admin)

  useSpecialistsBoardWebSocket(canAccess)

  const filters = useSpecialistsPageFilters()
  const {
    scope,
    view,
    subFromUrl,
    filterManagerSubs,
    filterSpecialistSubs,
    boardFilters,
    hasActiveFilters,
    studentsOffset,
    setStudentsOffset,
    setFilterManagerSubs,
    setFilterSpecialistSubs,
    resetFilters,
    setScope,
    setView,
  } = filters

  const data = useSpecialistsPageData({
    canAccess,
    user,
    isAdmin,
    scope,
    view,
    boardFilters,
    studentsOffset,
  })
  const {
    columns,
    boardPref,
    columnOrder,
    entries,
    boardPending,
    colsErr,
    colsError,
    boardErr,
    boardError,
    boardEntriesMy,
    displayEntriesMy,
    boardEntriesAllKanban,
    columnTitleByKey,
    attachmentsBySpecialistSub,
    alreadyAddedSubs,
    onMyBoardSubs,
    filteredAllListStudents,
    studentsTotal,
    studentsFetching,
    studentsErr,
    studentsError,
    directoryErr,
    directoryError,
    moveMutation,
    reorderMutation,
    addColumnMutation,
    updateColumnMutation,
    scheduleSpecialistColumnDelete,
    handlePersonalColumnReorder,
    toggleHiddenColumn,
  } = data

  const [addModalColumnKey, setAddModalColumnKey] = useState<string | null>(null)
  const [selectedEntry, setSelectedEntry] = useState<ManagerSpecialistEntry | null>(null)

  const boardUndo = useSpecialistBoardUndo({ userSub: user?.sub, isAdmin })
  const { scheduleRemoveFromBoard, scheduleAddToBoard } = boardUndo

  function entryManagerSub(entry: ManagerSpecialistEntry): string | undefined {
    return isAdmin ? entry.manager_sub : undefined
  }

  function resolveRemoveManagerSub(entry: ManagerSpecialistEntry | undefined): string | undefined {
    if (!entry) return user?.sub
    return entry.manager_sub
  }

  function addStudentToMyBoard(student: { sub: string; display_name?: string | null; email?: string | null }) {
    const columnKey = columns[0]?.key
    if (!columnKey) return
    scheduleAddToBoard({
      specialistSub: student.sub,
      columnKey,
      managerSub: isAdmin ? user?.sub : undefined,
      specialist: { display_name: student.display_name, email: student.email },
    })
  }

  function openSpecialistEntry(entry: ManagerSpecialistEntry) {
    setSelectedEntry(entry)
    const p = new URLSearchParams(filters.searchParams)
    p.set('sub', entry.specialist_sub)
    filters.setSearchParams(p, { replace: true })
  }

  function closeSpecialistModal() {
    setSelectedEntry(null)
    if (subFromUrl) {
      const p = new URLSearchParams(filters.searchParams)
      p.delete('sub')
      filters.setSearchParams(p, { replace: true })
    }
  }

  useEffect(() => {
    if (!subFromUrl || scope !== 'my' || boardPending) return
    if (entries.some((e) => e.specialist_sub === subFromUrl)) return
    setScope('all')
  }, [subFromUrl, scope, boardPending, entries, setScope])

  const entryFromUrl = useMemo(() => {
    if (!subFromUrl) return null
    return findEntryBySpecialistSub(entries, subFromUrl, user?.sub)
  }, [subFromUrl, entries, user?.sub])

  const modalEntry = selectedEntry ?? entryFromUrl

  const canManageBoard = (isManager || isAdmin) && columns.length > 0
  const showKanban = view === 'kanban'
  const showList = view === 'list'
  const kanbanEntries = scope === 'my' ? displayEntriesMy : boardEntriesAllKanban

  if (!user) return null
  if (!canAccess) return <Navigate to="/" replace />

  const errorMessage =
    (colsErr ? userFacingMessageFromUnknown(colsError) : null) ??
    (boardErr ? userFacingMessageFromUnknown(boardError) : null) ??
    (directoryErr ? userFacingMessageFromUnknown(directoryError) : null)

  const scopeLabel = scope === 'my' ? 'Мои специалисты' : 'Все специалисты'

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Специалисты</h1>
      </div>

      <p className={taskShell.lead}>
        {scope === 'my'
          ? showKanban
            ? 'Воронка — перетащите карточку в нужный этап или нажмите «+» в колонке.'
            : 'Список закреплённых на вашей доске специалистов.'
          : showKanban
            ? 'Канбан по всем закреплениям на досках менеджеров. Свои карточки можно перемещать.'
            : 'Справочник специалистов: менеджер, этап воронки и направление. Пагинация по 50 записей.'}
      </p>

      <SpecialistsFiltersPanel
        scope={scope}
        setScope={setScope}
        view={view}
        setView={setView}
        hasActiveFilters={hasActiveFilters}
        resetFilters={resetFilters}
        filterManagerSubs={filterManagerSubs}
        setFilterManagerSubs={setFilterManagerSubs}
        filterSpecialistSubs={filterSpecialistSubs}
        setFilterSpecialistSubs={setFilterSpecialistSubs}
      />

      <p className={`text-muted ${styles.scopeLabel}`}>{scopeLabel}</p>

      {errorMessage && <p className="text-danger">{errorMessage}</p>}

      {showKanban && (
        <SpecialistsKanbanView
          scope={scope}
          columns={columns}
          columnOrder={columnOrder}
          boardPref={boardPref}
          entries={entries}
          boardEntriesMy={boardEntriesMy}
          kanbanEntries={kanbanEntries}
          boardPending={boardPending}
          currentUserSub={user.sub}
          isAdmin={isAdmin}
          isManager={isManager}
          moveMutation={moveMutation}
          reorderMutation={reorderMutation}
          prefMutation={data.prefMutation}
          addColumnMutation={addColumnMutation}
          updateColumnMutation={updateColumnMutation}
          scheduleSpecialistColumnDelete={scheduleSpecialistColumnDelete}
          onAddSpecialist={(columnKey) => setAddModalColumnKey(columnKey)}
          onCardClick={isAdmin || isManager ? openSpecialistEntry : undefined}
          scheduleRemoveFromBoard={scheduleRemoveFromBoard}
          handlePersonalColumnReorder={handlePersonalColumnReorder}
          toggleHiddenColumn={toggleHiddenColumn}
          entryManagerSub={entryManagerSub}
          resolveRemoveManagerSub={resolveRemoveManagerSub}
        />
      )}

      {scope === 'my' && showList && (
        <SpecialistsMyListSection
          entries={displayEntriesMy}
          columns={columns}
          loading={boardPending}
          onSelectEntry={isAdmin || isManager ? openSpecialistEntry : undefined}
        />
      )}

      {scope === 'all' && showList && (
        <SpecialistsAllScopeSection
          allSpecialists={filteredAllListStudents}
          studentsTotal={studentsTotal}
          studentsOffset={studentsOffset}
          pageSize={SPECIALISTS_PAGE_SIZE}
          loading={studentsFetching || boardPending}
          isError={studentsErr}
          errorMessage={studentsErr ? userFacingMessageFromUnknown(studentsError) : null}
          attachmentsBySpecialistSub={attachmentsBySpecialistSub}
          columnTitleByKey={columnTitleByKey}
          currentUserSub={user.sub}
          canManageBoard={canManageBoard}
          onMyBoardSubs={onMyBoardSubs}
          onSelectEntry={openSpecialistEntry}
          onAddToBoard={addStudentToMyBoard}
          onPrevPage={() => setStudentsOffset((o) => Math.max(0, o - SPECIALISTS_PAGE_SIZE))}
          onNextPage={() => setStudentsOffset((o) => o + SPECIALISTS_PAGE_SIZE)}
        />
      )}

      {addModalColumnKey && (
        <AddSpecialistModal
          targetColumnKey={addModalColumnKey}
          columns={columns}
          alreadyAddedSubs={alreadyAddedSubs}
          onAdd={(student, columnKey) => {
            scheduleAddToBoard({
              specialistSub: student.sub,
              columnKey,
              managerSub: isAdmin ? user.sub : undefined,
              specialist: student,
            })
            scrollSpecialistColumnIntoView(columnKey)
          }}
          onMove={(student, columnKey) => {
            moveMutation.mutate({
              specialistSub: student.sub,
              columnKey,
              managerSub: isAdmin ? user.sub : undefined,
            })
            scrollSpecialistColumnIntoView(columnKey)
          }}
          onClose={() => setAddModalColumnKey(null)}
        />
      )}

      {modalEntry && (
        <SpecialistDetailModal
          entry={modalEntry}
          currentUserSub={user.sub}
          isAdmin={isAdmin}
          isManager={isManager}
          columns={columns}
          onClose={closeSpecialistModal}
        />
      )}
    </div>
  )
}
