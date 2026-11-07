import { useCallback, useState } from 'react'

import { uploadAttachment } from '../api/chat/chatApi'
import { userFacingMessageFromUnknown } from '../utils/apiUserMessage'
import type { PendingAttachment } from '../components/chat/composer/AttachmentChipList'

const MAX_FILES_PER_DROP = 20

type VoiceMeta = { durationSeconds: number; waveform: number[] }

/** Pending-вложения композера: выбор файлов, upload, сброс при смене чата. */
export function useMessageInputAttachments(chatId: string) {
  const [pending, setPending] = useState<PendingAttachment[]>([])
  const [pendingChatId, setPendingChatId] = useState(chatId)
  if (chatId !== pendingChatId) {
    setPendingChatId(chatId)
    setPending([])
  }

  const handleFilesSelected = useCallback(
    async (files: FileList | null, voiceMeta?: VoiceMeta) => {
      if (!files || files.length === 0) return
      const newItems: PendingAttachment[] = Array.from(files).map((f) => ({
        id: crypto.randomUUID(),
        file: f,
        uploading: true,
        progress: 0,
        error: null,
        result: null,
      }))
      setPending((prev) => [...prev, ...newItems])

      await Promise.all(
        newItems.map(async (item) => {
          try {
            const isVoice = voiceMeta && newItems.length === 1
            const att = await uploadAttachment(
              chatId,
              item.file,
              isVoice ? voiceMeta : undefined,
              (fraction) =>
                setPending((prev) =>
                  prev.map((p) => (p.id === item.id ? { ...p, progress: fraction } : p)),
                ),
            )
            setPending((prev) =>
              prev.map((p) => (p.id === item.id ? { ...p, uploading: false, result: att } : p)),
            )
          } catch (err) {
            const msg = userFacingMessageFromUnknown(err)
            setPending((prev) =>
              prev.map((p) => (p.id === item.id ? { ...p, uploading: false, error: msg } : p)),
            )
          }
        }),
      )
    },
    [chatId],
  )

  const addFilesFromList = useCallback(
    (files: FileList | File[], voiceMeta?: VoiceMeta) => {
      const list = files instanceof FileList ? Array.from(files) : files
      if (list.length === 0) return
      const capped = list.slice(0, MAX_FILES_PER_DROP)
      const dt = new DataTransfer()
      capped.forEach((f) => dt.items.add(f))
      void handleFilesSelected(dt.files, voiceMeta)
    },
    [handleFilesSelected],
  )

  const removePending = useCallback((id: string) => {
    setPending((prev) => prev.filter((p) => p.id !== id))
  }, [])

  const clearPending = useCallback(() => {
    setPending([])
  }, [])

  const restorePending = useCallback((items: PendingAttachment[]) => {
    setPending(items)
  }, [])

  return {
    pending,
    setPending,
    handleFilesSelected,
    addFilesFromList,
    removePending,
    clearPending,
    restorePending,
  }
}
