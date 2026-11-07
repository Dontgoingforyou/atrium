import { useEffect, useRef, useState } from 'react'
import { useClickOutside } from '../../../hooks/useClickOutside'
import { useNotifyToast } from '../../../hooks/useNotifyToast'
import { userFacingMessageFromUnknown } from '../../../utils/apiUserMessage'
import styles from '@/styles/modules/tasks/TasksPageKanbanColumns.module.css'

export function KanbanColumnInlineCreate({
  status,
  onCreateTask,
  onOpenTask,
  onClose,
}: {
  status: string
  onCreateTask: (title: string, status: string) => Promise<string>
  onOpenTask: (taskId: string) => void
  onClose: () => void
}) {
  const [title, setTitle] = useState('')
  const [isPending, setIsPending] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const formRef = useRef<HTMLDivElement>(null)
  const notify = useNotifyToast()

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  function handleCancel() {
    setTitle('')
    onClose()
  }

  async function handleSubmit() {
    const t = title.trim()
    if (!t || isPending) return
    setIsPending(true)
    try {
      const taskId = await onCreateTask(t, status)
      setTitle('')
      onClose()
      onOpenTask(taskId)
    } catch (e: unknown) {
      notify(userFacingMessageFromUnknown(e))
    } finally {
      setIsPending(false)
    }
  }

  function handleClickAway() {
    if (!title.trim()) {
      handleCancel()
      return
    }
    void handleSubmit()
  }

  useClickOutside(true, [formRef], handleClickAway)

  return (
    <div ref={formRef} className={styles.kanbanColumnAddTaskForm}>
      <input
        ref={inputRef}
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        className={styles.kanbanColumnAddTaskInput}
        placeholder="Название задачи…"
        disabled={isPending}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault()
            void handleSubmit()
          }
          if (e.key === 'Escape') handleCancel()
        }}
      />
    </div>
  )
}
