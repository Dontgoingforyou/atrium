import type { ManagerSpecialistEntry } from '../../types/specialist'
import styles from '@/styles/modules/specialists/SpecialistsPage.module.css'

type StudentRow = {
  sub: string
  display_name?: string | null
  email?: string | null
  username?: string | null
}

type Props = {
  allSpecialists: StudentRow[]
  studentsTotal: number
  studentsOffset: number
  pageSize: number
  loading: boolean
  isError: boolean
  errorMessage: string | null
  attachmentsBySpecialistSub: Map<string, ManagerSpecialistEntry[]>
  columnTitleByKey: Map<string, string>
  currentUserSub: string | undefined
  canManageBoard: boolean
  onMyBoardSubs: Set<string>
  onSelectEntry: (entry: ManagerSpecialistEntry) => void
  onAddToBoard: (student: StudentRow) => void
  onPrevPage: () => void
  onNextPage: () => void
}

export function SpecialistsAllScopeSection({
  allSpecialists,
  studentsTotal,
  studentsOffset,
  pageSize,
  loading,
  isError,
  errorMessage,
  attachmentsBySpecialistSub,
  columnTitleByKey,
  currentUserSub,
  canManageBoard,
  onMyBoardSubs,
  onSelectEntry,
  onAddToBoard,
  onPrevPage,
  onNextPage,
}: Props) {
  function formatAttachmentLine(entry: ManagerSpecialistEntry): string {
    const stage = columnTitleByKey.get(entry.column_key) ?? entry.column_key
    const mgr = entry.manager_display_name ?? entry.manager_sub
    const dir = entry.status_title ? ` · ${entry.status_title}` : ''
    return `${mgr} — ${stage}${dir}`
  }

  const hasPrev = studentsOffset > 0
  const hasNext = studentsOffset + pageSize < studentsTotal

  return (
    <section>
      <h2 className={styles.sectionTitle}>
        Специалисты
        {studentsTotal > 0
          ? ` (${studentsOffset + 1}–${Math.min(studentsOffset + pageSize, studentsTotal)} из ${studentsTotal})`
          : ''}
      </h2>
      {loading && <p className="text-muted">Загрузка…</p>}
      {isError && <p className="text-danger">{errorMessage ?? 'Не удалось загрузить список'}</p>}
      <ul className={styles.allList}>
        {allSpecialists.map((s) => {
          const attachments = attachmentsBySpecialistSub.get(s.sub) ?? []
          const onMyBoard = onMyBoardSubs.has(s.sub)
          const label = s.display_name ?? s.email ?? s.sub
          const primaryEntry =
            attachments.find((e) => e.manager_sub === currentUserSub) ?? attachments[0]

          return (
            <li key={s.sub} className={styles.allListRow}>
              {primaryEntry ? (
                <button
                  type="button"
                  className={styles.allListBtn}
                  onClick={() => onSelectEntry(primaryEntry)}
                >
                  <span className={styles.allListNamePrimary}>{label}</span>
                  <span className={styles.allListMeta}>
                    {attachments.map((e) => formatAttachmentLine(e)).join(' · ')}
                  </span>
                </button>
              ) : (
                <div className={styles.allListNameBlock}>
                  <span className={styles.allListName}>{label}</span>
                  <span className={styles.allListMetaMuted}>Не на доске</span>
                </div>
              )}
              {canManageBoard && !onMyBoard && (
                <button type="button" className="btn-secondary" onClick={() => onAddToBoard(s)}>
                  На доску
                </button>
              )}
            </li>
          )
        })}
      </ul>
      {allSpecialists.length === 0 && !loading && !isError && (
        <p className="text-muted">Нет студентов в справочнике</p>
      )}
      {(hasPrev || hasNext) && (
        <div className={styles.pager}>
          <button
            type="button"
            className="btn-secondary"
            disabled={loading || !hasPrev}
            onClick={onPrevPage}
          >
            Назад
          </button>
          <button
            type="button"
            className="btn-secondary"
            disabled={loading || !hasNext}
            onClick={onNextPage}
          >
            Далее
          </button>
        </div>
      )}
    </section>
  )
}
