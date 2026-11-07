import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listPortalStudentSpecialists } from '../../api/usersApi'
import {
  listAddSpecialistModalRows,
  type AddSpecialistModalCandidate,
} from '../../domain/specialists/addSpecialistModal'
import type { SpecialistColumn } from '../../types/specialist'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { getUserDisplayLabel } from '../../utils/userLabel'
import { specialistStudentsModalQueryKey } from '../../pages/specialists/specialistQueryKeys'
import { Modal } from '../ui/Modal'
import { UserAvatar } from '../ui/UserAvatar'
import styles from '@/styles/modules/specialists/AddSpecialistModal.module.css'

/** Совпадает с le=200 в GET /portal/users/specialists */
const STUDENTS_MODAL_LIMIT = 200

interface Props {
  targetColumnKey: string
  columns: SpecialistColumn[]
  alreadyAddedSubs: Set<string>
  onAdd: (student: AddSpecialistModalCandidate, columnKey: string) => void
  onMove: (student: AddSpecialistModalCandidate, columnKey: string) => void
  onClose: () => void
}

export function AddSpecialistModal({
  targetColumnKey,
  columns,
  alreadyAddedSubs,
  onAdd,
  onMove,
  onClose,
}: Props) {
  const [search, setSearch] = useState('')

  const { data: studentsPage, isPending, isFetching, isError, error } = useQuery({
    queryKey: specialistStudentsModalQueryKey(),
    queryFn: () => listPortalStudentSpecialists({ limit: STUDENTS_MODAL_LIMIT, skip: 0 }),
    staleTime: 0,
    refetchOnMount: 'always',
  })

  const allSpecialists = useMemo(() => studentsPage?.items ?? [], [studentsPage])
  const colTitle = columns.find((c) => c.key === targetColumnKey)?.title ?? targetColumnKey

  const available = useMemo(
    () => listAddSpecialistModalRows(allSpecialists, alreadyAddedSubs, search),
    [allSpecialists, alreadyAddedSubs, search],
  )

  const emptyHint = (() => {
    if (isError) return userFacingMessageFromUnknown(error)
    if (isPending || (isFetching && allSpecialists.length === 0)) return 'Загрузка…'
    if (search.trim()) return 'Ничего не найдено'
    if (allSpecialists.length === 0) return 'Нет доступных студентов'
    return 'Нет специалистов для этой колонки'
  })()

  return (
    <Modal title={`Добавить специалиста в «${colTitle}»`} maxWidth={440} onClose={onClose}>
      <input
        type="search"
        className={`form-input ${styles.modalSearchInput}`}
        placeholder="Поиск по имени или email…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        autoFocus
      />
      <ul className={styles.modalList}>
        {available.length === 0 && <li className={styles.modalEmpty}>{emptyHint}</li>}
        {available.map(({ student, action }) => (
          <li key={student.sub}>
            <button
              type="button"
              className={styles.modalListItem}
              onClick={() => {
                if (action === 'move') onMove(student, targetColumnKey)
                else onAdd(student, targetColumnKey)
                onClose()
              }}
            >
              <UserAvatar
                label={getUserDisplayLabel(student)}
                imageUrl={student.avatar_url}
                size="md"
              />
              <div className={styles.modalItemInfo}>
                <span className={styles.modalItemName}>{getUserDisplayLabel(student)}</span>
                {student.email && <span className={styles.modalItemEmail}>{student.email}</span>}
                {action === 'move' ? (
                  <span className={styles.modalItemAction}>На доске · перенести</span>
                ) : null}
              </div>
            </button>
          </li>
        ))}
      </ul>
    </Modal>
  )
}
