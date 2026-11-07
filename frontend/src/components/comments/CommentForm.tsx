import { useRef, useState, type ClipboardEvent } from 'react'
import { useMutation, useQueryClient, type QueryKey } from '@tanstack/react-query'

import type { PortalUser } from '../../types/chat'
import type {
  CommentThreadUploadResult,
  ThreadCommentCreate,
  ThreadCommentUpdate,
} from '../../types/commentThread'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { handleComposerEnterSubmit } from '../../utils/composerKeyboard'
import { mapWithConcurrency } from '../../utils/uploadConcurrency'
import { MediaLightbox } from '../ui/MediaLightbox'
import { MentionTextarea } from './MentionTextarea'
import { IconPaperclip } from '../icons/portalIcons'
import styles from '@/styles/modules/tasks/TaskComments.module.css'

export function CommentForm({
  queryKey,
  create,
  update,
  parentId,
  users,
  mentionsUnavailable = false,
  onSuccess,
  onCancel,
  placeholder,
  autoFocus,
  uploadImage,
  initialBody = '',
  initialMentions = [],
  submitLabel,
}: {
  queryKey: QueryKey
  create?: (b: ThreadCommentCreate) => Promise<unknown>
  /** Режим правки: PATCH body/mentions; expected_version добавляет вызывающий (CommentItem). */
  update?: (b: Omit<ThreadCommentUpdate, 'expected_version'>) => Promise<unknown>
  parentId?: string | null
  users: PortalUser[]
  mentionsUnavailable?: boolean
  onSuccess: () => void
  onCancel?: () => void
  placeholder?: string
  autoFocus?: boolean
  uploadImage?: (file: File) => Promise<CommentThreadUploadResult>
  initialBody?: string
  initialMentions?: string[]
  submitLabel?: string
}) {
  const queryClient = useQueryClient()
  const isEdit = Boolean(update)
  const [body, setBody] = useState(initialBody)
  const [mentionSubs, setMentionSubs] = useState<string[]>(initialMentions)
  const [error, setError] = useState('')
  const [attachments, setAttachments] = useState<CommentThreadUploadResult[]>([])
  const [uploading, setUploading] = useState(false)
  const [draftLightbox, setDraftLightbox] = useState<{ url: string; filename: string } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const allowAttachments = Boolean(uploadImage) && !isEdit

  async function handleFiles(files: FileList | null) {
    if (!files || !uploadImage || isEdit) return
    setUploading(true)
    setError('')
    const imageFiles = Array.from(files).filter((f) => f.type.startsWith('image/'))
    const failures: string[] = []
    const results = await mapWithConcurrency(imageFiles, 4, async (file) => {
      try {
        return await uploadImage(file)
      } catch (e: unknown) {
        failures.push(userFacingMessageFromUnknown(e))
        return null
      }
    })
    const uploaded: CommentThreadUploadResult[] = results.filter(
      (r): r is NonNullable<typeof r> => r !== null,
    )
    setAttachments((prev) => [...prev, ...uploaded])
    if (failures.length > 0) {
      setError(
        failures.length === 1
          ? failures[0]
          : `Не удалось загрузить ${failures.length} из ${imageFiles.length} файлов`,
      )
    }
    setUploading(false)
  }

  function removeAttachment(id: string) {
    setAttachments((prev) => prev.filter((a) => a.id !== id))
  }

  async function handlePaste(e: ClipboardEvent) {
    if (!allowAttachments || !uploadImage) return
    const items = Array.from(e.clipboardData.items)
    const imageFiles = items
      .filter((item) => item.kind === 'file' && item.type.startsWith('image/'))
      .map((item) => item.getAsFile())
      .filter((f): f is File => f !== null)
    if (imageFiles.length > 0) {
      e.preventDefault()
      await handleFiles(
        (() => {
          const dt = new DataTransfer()
          for (const f of imageFiles) dt.items.add(f)
          return dt.files
        })(),
      )
    }
  }

  const mutation = useMutation({
    mutationFn: () => {
      if (update) {
        return update({
          body: body.trim(),
          mentions: mentionSubs,
        })
      }
      if (!create) {
        return Promise.reject(new Error('Не задан обработчик отправки комментария'))
      }
      return create({
        body: body.trim(),
        parent_id: parentId ?? null,
        mentions: mentionSubs,
        media_ids: attachments.map((a) => a.id),
      })
    },
    onSuccess: () => {
      if (!isEdit) {
        setBody('')
        setMentionSubs([])
        setAttachments([])
      }
      setError('')
      void queryClient.invalidateQueries({ queryKey })
      onSuccess()
    },
    onError: (e: unknown) => setError(userFacingMessageFromUnknown(e)),
  })

  const canSubmit =
    !mutation.isPending &&
    !uploading &&
    (Boolean(body.trim()) || (!isEdit && attachments.length > 0))

  const resolvedSubmitLabel =
    submitLabel ?? (mutation.isPending ? (isEdit ? 'Сохранение…' : 'Отправка…') : isEdit ? 'Сохранить' : 'Отправить')

  return (
    <div className={styles.commentForm} onPaste={allowAttachments ? handlePaste : undefined}>
      {mentionsUnavailable ? (
        <p className="text-muted" role="status">
          Упоминания недоступны — не удалось загрузить список пользователей.
        </p>
      ) : null}
      <MentionTextarea
        value={body}
        onChange={setBody}
        onMentionsChange={setMentionSubs}
        users={users}
        placeholder={placeholder ?? 'Написать комментарий… (@ для упоминания)'}
        rows={2}
        autoFocus={autoFocus}
        onKeyDown={(e) => {
          handleComposerEnterSubmit(e, canSubmit, () => mutation.mutate())
        }}
      />
      {attachments.length > 0 && (
        <div className={styles.attachmentPreview}>
          {attachments.map((a) => (
            <div key={a.id} className={styles.attachmentThumb}>
              <button
                type="button"
                className={styles.attachmentThumbOpen}
                title={a.original_filename}
                aria-label={`Открыть вложение ${a.original_filename}`}
                onClick={() => setDraftLightbox({ url: a.download_url, filename: a.original_filename })}
              >
                <img src={a.download_url} alt={a.original_filename} className={styles.attachmentImg} />
              </button>
              <button
                type="button"
                className={styles.attachmentRemove}
                onClick={() => removeAttachment(a.id)}
                title="Удалить"
                aria-label="Удалить вложение"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
      {draftLightbox && (
        <MediaLightbox
          url={draftLightbox.url}
          filename={draftLightbox.filename}
          contentType="image/jpeg"
          onClose={() => setDraftLightbox(null)}
        />
      )}
      {error ? <p className="form-error">{error}</p> : null}
      <div className={styles.formActions}>
        {allowAttachments && (
          <>
            <button
              type="button"
              className={styles.attachBtn}
              title="Прикрепить изображение"
              aria-label="Прикрепить изображение"
              disabled={uploading}
              onClick={() => fileInputRef.current?.click()}
            >
              {uploading ? '…' : <IconPaperclip />}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              className={styles.hiddenFileInput}
              onChange={(e) => { void handleFiles(e.target.files); e.target.value = '' }}
            />
          </>
        )}
        {onCancel && (
          <button type="button" className={styles.cancelBtn} onClick={onCancel}>
            Отмена
          </button>
        )}
        <button
          type="button"
          className={`btn-primary ${styles.sendBtn}`}
          disabled={!canSubmit}
          onClick={() => mutation.mutate()}
        >
          {resolvedSubmitLabel}
        </button>
      </div>
    </div>
  )
}
