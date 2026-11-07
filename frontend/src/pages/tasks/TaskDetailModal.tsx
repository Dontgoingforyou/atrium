import { useState } from 'react'

import { Modal } from '../../components/ui/Modal'
import { TaskDetailBody } from './TaskDetailBody'
import { useTaskDetailData } from './useTaskDetailData'
import pageStyles from '@/styles/modules/tasks/TaskDetailPage.module.css'

type Props = {
  taskId: string
  onClose: () => void
  onScheduleDelete?: (taskId: string) => void
}

export function TaskDetailModal({ taskId: initialTaskId, onClose, onScheduleDelete }: Props) {
  const [taskHistory, setTaskHistory] = useState<string[]>([initialTaskId])
  const taskId = taskHistory[taskHistory.length - 1]

  function openTaskInModal(id: string) {
    setTaskHistory((h) => [...h, id])
  }

  function goBack() {
    setTaskHistory((h) => (h.length > 1 ? h.slice(0, -1) : h))
  }

  const { task } = useTaskDetailData({ taskId })
  const modalTitle = task
    ? `Задача ${task.number != null ? '#' + task.number : ''}`
    : 'Задача'

  return (
    <Modal title={modalTitle} onClose={onClose} maxWidth={960}>
      <TaskDetailBody
        taskId={taskId}
        layout="modal"
        onDelete={onClose}
        onScheduleDelete={onScheduleDelete}
        onOpenTaskDetail={openTaskInModal}
        toolbarLeading={
          taskHistory.length > 1 ? (
            <button type="button" className={pageStyles.linkMuted} onClick={goBack}>
              ← Назад
            </button>
          ) : null
        }
      />
    </Modal>
  )
}
