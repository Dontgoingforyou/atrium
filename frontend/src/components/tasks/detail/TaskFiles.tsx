import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { deleteFile, listFiles, uploadFile } from '../../../api/tasks/tasksApi'
import { useNotifyToast } from '../../../hooks/useNotifyToast'
import { useScheduleDeleteWithUndo } from '../../../hooks/useScheduleDeleteWithUndo'
import { taskFilesQueryKey } from '@/pages/tasks/tasksQueryKeys'
import type { TaskFile } from '../../../types/task'
import { userFacingMessageFromUnknown } from '../../../utils/apiUserMessage'
import { fileIcon, formatBytes } from '../../../utils/fileUtils'
import { IconPaperclip, IconX } from '../../icons/portalIcons'
import { MediaLightbox } from '../../ui/MediaLightbox'
import detailStyles from '@/styles/modules/tasks/TaskDetailPage.module.css'
import styles from '@/styles/modules/tasks/TaskFiles.module.css'

function isPreviewableInLightbox(contentType: string): boolean {
  return contentType.startsWith('image/') || contentType.startsWith('video/')
}

export function TaskFiles({ taskId, currentUserSub, isPortalAdmin }: {
  taskId: string
  currentUserSub: string
  isPortalAdmin: boolean
}) {
  const queryClient = useQueryClient()
  const scheduleDeleteWithUndo = useScheduleDeleteWithUndo()
  const notify = useNotifyToast()
  const filesQueryKey = taskFilesQueryKey(taskId)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [previewFile, setPreviewFile] = useState<TaskFile | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const { data: files = [], isLoading, isError } = useQuery({
    queryKey: filesQueryKey,
    queryFn: () => listFiles(taskId),
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadFile(taskId, file),
    onSuccess: () => {
      setUploadError(null)
      void queryClient.invalidateQueries({ queryKey: filesQueryKey })
    },
    onError: (err) => setUploadError(userFacingMessageFromUnknown(err)),
  })

  const deleteMutation = useMutation({
    mutationFn: (fileId: string) => deleteFile(taskId, fileId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: filesQueryKey })
    },
    onError: (err) => {
      void queryClient.invalidateQueries({ queryKey: filesQueryKey })
      notify(userFacingMessageFromUnknown(err))
    },
  })

  function scheduleFileDelete(file: TaskFile) {
    scheduleDeleteWithUndo({
      message: 'Файл удалён',
      optimistic: () => {
        queryClient.setQueryData<TaskFile[]>(filesQueryKey, (prev) =>
          prev ? prev.filter((f) => f.id !== file.id) : [],
        )
      },
      revert: () => {
        queryClient.setQueryData<TaskFile[]>(filesQueryKey, (prev) => {
          const list = prev ?? []
          if (list.some((f) => f.id === file.id)) return list
          return [...list, file].sort(
            (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
          )
        })
      },
      commit: () => deleteMutation.mutate(file.id),
    })
  }

  function handleFileChosen(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    uploadMutation.mutate(file)
  }

  return (
    <div className={styles.section}>
      {isLoading ? (
        <span className={styles.emptyText}>Загрузка...</span>
      ) : isError ? (
        <span className={detailStyles.panelEmptyState}>Не удалось загрузить файлы</span>
      ) : files.length === 0 ? (
        <span className={detailStyles.panelEmptyState}>Файлы не добавлены</span>
      ) : (
        <ul className={styles.fileList}>
          {files.map((file) => (
            <li key={file.id} className={styles.fileItem}>
              <span className={styles.fileIcon}>{fileIcon(file.content_type)}</span>
              {isPreviewableInLightbox(file.content_type) ? (
                <button
                  type="button"
                  className={styles.fileAnchor}
                  title={file.original_filename}
                  onClick={() => setPreviewFile(file)}
                >
                  {file.original_filename}
                </button>
              ) : (
                <a
                  href={file.view_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.fileAnchor}
                  title={file.original_filename}
                >
                  {file.original_filename}
                </a>
              )}
              <span className={styles.fileMeta}>{formatBytes(file.file_size)}</span>
              <span className={styles.fileMeta}>
                {new Date(file.created_at).toLocaleDateString('ru-RU')}
              </span>
              {(file.uploaded_by_sub === currentUserSub || isPortalAdmin) && (
                <button
                  type="button"
                  className={styles.deleteBtn}
                  title="Удалить файл"
                  aria-label="Удалить файл"
                  disabled={deleteMutation.isPending}
                  onClick={() => scheduleFileDelete(file)}
                >
                  <IconX />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className={styles.addForm}>
        <input
          ref={inputRef}
          type="file"
          className={styles.hiddenFileInput}
          onChange={handleFileChosen}
        />
        <button
          type="button"
          className="btn-secondary"
          disabled={uploadMutation.isPending}
          onClick={() => inputRef.current?.click()}
        >
          <IconPaperclip /> {uploadMutation.isPending ? 'Загрузка...' : 'Добавить файл'}
        </button>
        {uploadError && <span className={styles.errorText}>{uploadError}</span>}
      </div>

      {previewFile && (
        <MediaLightbox
          url={previewFile.view_url}
          filename={previewFile.original_filename}
          contentType={previewFile.content_type}
          onClose={() => setPreviewFile(null)}
        />
      )}
    </div>
  )
}
