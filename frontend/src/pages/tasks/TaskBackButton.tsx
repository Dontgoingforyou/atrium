import { useNavigate } from 'react-router'
import styles from '@/styles/modules/tasks/TaskBackButton.module.css'
import type { TaskBackNavState } from './taskBackNav'

export type TaskBackButtonProps = {
  label: string
  to: string
  state?: TaskBackNavState
}

export function TaskBackButton({ label, to, state }: TaskBackButtonProps) {
  const navigate = useNavigate()
  return (
    <button type="button" className={styles.backBtn} onClick={() => navigate(to, { state })}>
      {label}
    </button>
  )
}
