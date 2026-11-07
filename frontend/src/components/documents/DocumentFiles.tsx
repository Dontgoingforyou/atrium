import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  deleteDocumentFile,
  listDocumentFiles,
  uploadDocumentFile,
} from '../../api/documents/documentFilesApi'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { useScheduleDeleteWithUndo } from '../../hooks/useScheduleDeleteWithUndo'
import type { DocumentFile } from '../../types/document'
import { documentFilesQueryKey } from '../../utils/documents/documentNavigation'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { fileIcon, formatBytes } from '../../utils/fileUtils'
import { IconPaperclip, IconX } from '../icons/portalIcons'
import styles from '@/styles/modules/documents/DocumentFiles.module.css'

type Props = {
  documentId: string
  currentUserSub: string
  canEditDocuments: boolean
  isPortalAdmin: boolean
}

/** Файлы-вложения документа: просмотр, скачивание, загрузка и удаление. */
export function DocumentFiles({
  documentId,
  currentUserSub,
  canEditDocuments,
  isPortalAdmin,
}: Props) {
  const queryClient = useQueryClient()
  const scheduleDeleteWithUndo = useScheduleDeleteWithUndo()
  const notify = useNotifyToast()
  const filesQueryKey = documentFilesQueryKey(documentId)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const { data: files = [], isLoading, isError } = useQuery({
    queryKey: filesQueryKey,
    queryFn: () => listDocumentFiles(documentId),
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadDocumentFile(documentId, file),
    onSuccess: () => {
      setUploadError(null)
      void queryClient.invalidateQueries({ queryKey: filesQueryKey })
    },
    onError: (err) => setUploadError(userFacingMessageFromUnknown(err)),
  })

  const deleteMutation = useMutation({
    mutationFn: (fileId: string) => deleteDocumentFile(documentId, fileId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: filesQueryKey })
    },
    onError: (err) => {
      void queryClient.invalidateQueries({ queryKey: filesQueryKey })
      notify(userFacingMessageFromUnknown(err))
    },
  })

  function scheduleFileDelete(file: DocumentFile) {
    scheduleDeleteWithUndo({
      message: 'Файл удалён',
      optimistic: () => {
        queryClient.setQueryData<DocumentFile[]>(filesQueryKey, (prev) =>
          prev ? prev.filter((f) => f.id !== file.id) : [],
        )
      },
      revert: () => {
        queryClient.setQueryData<DocumentFile[]>(filesQueryKey, (prev) => {
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

  const canDelete = (file: DocumentFile) =>
    file.uploaded_by_sub === currentUserSub || canEditDocuments || isPortalAdmin

  const showBlock = canEditDocuments || files.length > 0 || isLoading || isError
  if (!showBlock) return null

  return (
    <section className={styles.section} data-tour="document-files" aria-label="Документы">
      <h2 className={styles.heading}>
        Документы{' '}
        <span className={styles.headingFormats}>
          (PDF, Word, Excel, PowerPoint, RTF, TXT, CSV, Markdown)
        </span>
      </h2>
      {isLoading ? (
        <span className={styles.emptyText}>Загрузка…</span>
      ) : isError ? (
        <span className={styles.emptyText}>Не удалось загрузить документы</span>
      ) : files.length === 0 ? (
        <span className={styles.emptyText}>Документы не добавлены</span>
      ) : (
        <ul className={styles.fileList}>
          {files.map((file) => (
            <li key={file.id} className={styles.fileItem}>
              <span className={styles.fileIcon} aria-hidden>
                {fileIcon(file.content_type)}
              </span>
              <a
                href={file.view_url}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.fileAnchor}
                title={file.original_filename}
              >
                {file.original_filename}
              </a>
              <span className={styles.fileMeta}>{formatBytes(file.file_size)}</span>
              <span className={styles.fileMeta}>
                {new Date(file.created_at).toLocaleDateString('ru-RU')}
              </span>
              <div className={styles.fileActions}>
                <a
                  href={file.download_url}
                  className={styles.downloadLink}
                  download={file.original_filename}
                  title="Скачать"
                >
                  Скачать
                </a>
                {canDelete(file) ? (
                  <button
                    type="button"
                    className={styles.deleteBtn}
                    title="Удалить документ"
                    aria-label="Удалить документ"
                    disabled={deleteMutation.isPending}
                    onClick={() => scheduleFileDelete(file)}
                  >
                    <IconX />
                  </button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}

      {canEditDocuments ? (
        <div className={styles.addForm}>
          <input
            ref={inputRef}
            type="file"
            accept={
              '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.rtf,.txt,.csv,.md,' +
              'application/pdf,' +
              'application/msword,' +
              'application/vnd.openxmlformats-officedocument.wordprocessingml.document,' +
              'application/vnd.ms-excel,' +
              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,' +
              'application/vnd.ms-powerpoint,' +
              'application/vnd.openxmlformats-officedocument.presentationml.presentation,' +
              'application/rtf,text/plain,text/csv,text/markdown'
            }
            className={styles.hiddenFileInput}
            onChange={handleFileChosen}
          />
          <button
            type="button"
            className="btn-secondary"
            disabled={uploadMutation.isPending}
            onClick={() => inputRef.current?.click()}
          >
            <IconPaperclip /> {uploadMutation.isPending ? 'Загрузка…' : 'Добавить документ'}
          </button>
          {uploadError ? <span className={styles.errorText}>{uploadError}</span> : null}
        </div>
      ) : null}
    </section>
  )
}
