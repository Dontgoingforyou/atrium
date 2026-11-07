import type { PortalTaskColumn, TaskBoardPref } from '../../types/task'
import createFormStyles from '@/styles/modules/tasks/TasksPageCreateForm.module.css'

type Props = {
  open: boolean
  setOpen: (updater: (v: boolean) => boolean) => void
  showAllHiddenColumns: boolean
  setShowAllHiddenColumns: (value: boolean) => void
  sortedColumns: PortalTaskColumn[]
  boardPref: TaskBoardPref | null | undefined
  boardPrefPending: boolean
  toggleHiddenColumn: (statusKey: string) => void
  toggleSubtasksFlat: () => void
  toggleHideSubtasks: () => void
}

export function TasksPersonalBoardPanel({
  open,
  setOpen,
  showAllHiddenColumns,
  setShowAllHiddenColumns,
  sortedColumns,
  boardPref,
  boardPrefPending,
  toggleHiddenColumn,
  toggleSubtasksFlat,
  toggleHideSubtasks,
}: Props) {
  const hideSubtasks = boardPref?.hide_subtasks ?? false
  return (
    <>
      <div className={createFormStyles.kanbanPersonalBar}>
        <button
          type="button"
          className={createFormStyles.kanbanPersonalToggle}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          <span
            className={[
              createFormStyles.kanbanPersonalToggleChevron,
              open ? createFormStyles.kanbanPersonalToggleChevronOpen : '',
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
        <label className={createFormStyles.kanbanPersonalCheckbox}>
          <input
            type="checkbox"
            checked={hideSubtasks}
            onChange={toggleHideSubtasks}
            disabled={boardPrefPending}
          />
          Скрыть подзадачи
        </label>
        <span className={createFormStyles.kanbanPersonalHint}>
          Порядок колонок: перетащите шапку (значок «⋮⋮» и название), сохраняется только для вас.
        </span>
      </div>
      <div
        className={[
          createFormStyles.kanbanPersonalPanelShell,
          open ? createFormStyles.kanbanPersonalPanelShellOpen : '',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        <div className={createFormStyles.kanbanPersonalPanelShellInner}>
          <div className={createFormStyles.kanbanPersonalPanel}>
            <p className={createFormStyles.kanbanPersonalPanelTitle}>Скрыть колонки на канбане</p>
            <div className={createFormStyles.kanbanPersonalChecks}>
              {sortedColumns.map((col) => (
                <label key={col.id} className={createFormStyles.kanbanPersonalCheckRow}>
                  <input
                    type="checkbox"
                    checked={(boardPref?.hidden_status_keys ?? []).includes(col.status_key)}
                    onChange={() => toggleHiddenColumn(col.status_key)}
                    disabled={boardPrefPending}
                  />
                  <span>Скрыть «{col.title}»</span>
                </label>
              ))}
            </div>
            <p
              className={`${createFormStyles.kanbanPersonalPanelTitle} ${createFormStyles.kanbanPersonalPanelTitleSpaced}`}
            >
              Отображение подзадач
            </p>
            <label className={createFormStyles.kanbanPersonalCheckRow}>
              <input
                type="checkbox"
                checked={hideSubtasks}
                onChange={toggleHideSubtasks}
                disabled={boardPrefPending}
              />
              <span>Скрывать подзадачи на канбане</span>
            </label>
            <label className={createFormStyles.kanbanPersonalCheckRow}>
              <input
                type="checkbox"
                checked={boardPref?.subtasks_flat ?? false}
                onChange={toggleSubtasksFlat}
                disabled={boardPrefPending || hideSubtasks}
              />
              <span>Показывать подзадачи отдельными карточками (плоский режим)</span>
            </label>
          </div>
        </div>
      </div>
    </>
  )
}
