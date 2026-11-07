import { useLayoutEffect, useState, type ReactNode, type TransitionEvent } from 'react'
import type { AssigneeHomeDrilldown } from '../../types/home'
import styles from '@/styles/modules/home/HomeAssignee.module.css'

type Props = {
  open: boolean
  loading?: boolean
  isError?: boolean
  errorMessage?: string
  data: AssigneeHomeDrilldown | null | undefined
  children: (data: AssigneeHomeDrilldown) => ReactNode
}

/** Обёртка с плавным раскрытием/сворачиванием панели drill-down. */
export function HomeAssigneeDrilldownShell({
  open,
  loading,
  isError,
  errorMessage,
  data,
  children,
}: Props) {
  const [cached, setCached] = useState<AssigneeHomeDrilldown | null>(null)
  const [animOpen, setAnimOpen] = useState(false)

  if (data != null && data !== cached) {
    setCached(data)
  }

  const show = open || cached != null

  useLayoutEffect(() => {
    if (!show) return
    const raf = requestAnimationFrame(() => setAnimOpen(open))
    return () => cancelAnimationFrame(raf)
  }, [open, show])

  if (!show) return null

  const onTransitionEnd = (e: TransitionEvent<HTMLDivElement>) => {
    if (e.propertyName !== 'grid-template-rows' || open) return
    setCached(null)
  }

  let body: ReactNode
  if (cached) {
    body = children(cached)
  } else if (isError) {
    body = (
      <p className={`text-danger ${styles.assigneeDrilldownLoading}`}>
        {errorMessage ?? 'Не удалось загрузить данные'}
      </p>
    )
  } else {
    body = (
      <p className={`text-muted ${styles.assigneeDrilldownLoading}`}>
        {loading ? 'Загрузка задач…' : 'Нет данных'}
      </p>
    )
  }

  return (
    <div
      className={`${styles.assigneeDrilldownShell} ${animOpen ? styles.assigneeDrilldownShellOpen : ''}`}
      onTransitionEnd={onTransitionEnd}
    >
      <div className={styles.assigneeDrilldownInner}>{body}</div>
    </div>
  )
}
