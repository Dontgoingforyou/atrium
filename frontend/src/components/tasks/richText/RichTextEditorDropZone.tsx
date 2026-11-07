import { useCallback, useState, type ReactNode } from 'react'
import type { Editor } from '@tiptap/react'
import styles from '@/styles/modules/tasks/RichTextEditor.module.css'
import { userFacingMessageFromUnknown } from '@/utils/apiUserMessage'
import type { RichTextEntityType } from './RichTextEditor'

type Props = {
  editor: Editor | null
  entityType?: RichTextEntityType
  entityId?: string
  uploadImages?: (files: File[]) => void | Promise<void>
  children: ReactNode
}

export function RichTextEditorDropZone({
  editor,
  entityType,
  entityId,
  uploadImages,
  children,
}: Props) {
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState('')

  const canUpload = Boolean(entityType && entityId && editor)

  const uploadFiles = useCallback(
    async (files: FileList | File[]) => {
      if (!editor || !uploadImages) return
      const imageFiles = Array.from(files).filter((f) => f.type.startsWith('image/'))
      if (imageFiles.length === 0) {
        setError('Перетащите файл изображения (JPEG, PNG, GIF, WebP)')
        return
      }
      setError('')
      try {
        await uploadImages(imageFiles)
      } catch (err) {
        setError(userFacingMessageFromUnknown(err))
      }
    },
    [editor, uploadImages],
  )

  return (
    <div
      className={`${styles.dropZone} ${dragOver ? styles.dropZoneActive : ''}`}
      onDragEnter={(e) => {
        e.preventDefault()
        if (!canUpload) return
        setDragOver(true)
      }}
      onDragOver={(e) => {
        e.preventDefault()
        e.dataTransfer.dropEffect = canUpload ? 'copy' : 'none'
        if (canUpload) setDragOver(true)
      }}
      onDragLeave={(e) => {
        if (e.currentTarget.contains(e.relatedTarget as Node)) return
        setDragOver(false)
      }}
      onDrop={(e) => {
        e.preventDefault()
        setDragOver(false)
        if (!canUpload) {
          setError('Сначала сохраните задачу или документ, затем перетащите изображение')
          return
        }
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
          void uploadFiles(e.dataTransfer.files)
        }
      }}
    >
      {children}
      {dragOver && canUpload ? (
        <div className={styles.dropOverlay}>Отпустите, чтобы вставить изображение</div>
      ) : null}
      {error ? <p className={styles.dropError}>{error}</p> : null}
    </div>
  )
}
