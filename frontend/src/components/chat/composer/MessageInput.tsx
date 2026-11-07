import {
  forwardRef,
  useState,
  useRef,
  useEffect,
  useCallback,
  useImperativeHandle,
} from 'react'

import { useMessageInputAttachments } from '../../../hooks/useMessageInputAttachments'
import { useMessageInputEphemeral } from '../../../hooks/useMessageInputEphemeral'

import { useThemeStore } from '../../../store/themeStore'
import { userFacingMessageFromUnknown } from '../../../utils/apiUserMessage'
import { handleComposerEnterSubmit } from '../../../utils/composerKeyboard'
import {
  releaseMessageSubmitLock,
  tryAcquireMessageSubmitLock,
} from '@/utils/chat/messageInputSubmit'
import { useVoiceRecording } from '../../../hooks/useVoiceRecording'
import { AttachmentChipList } from './AttachmentChipList'
import { MentionAwareTextarea } from './MentionAwareTextarea'
import { MessageReplyBanner, MessageVoiceBar } from './MessageInputBars'
import { IconMicrophone, IconPaperclip, IconSmiley } from '../../icons/portalIcons'
import styles from '@/styles/modules/chat/MessageInput.module.css'
import type { MessageInputHandle, MessageInputProps } from './messageInputTypes'
import { useMessageInputEmojiPicker } from './useMessageInputEmojiPicker'
import { MessageInputEmojiPicker } from './MessageInputEmojiPicker'

export type { MessageInputHandle }

export const MessageInput = forwardRef<MessageInputHandle, MessageInputProps>(function MessageInput(
  {
    chatId,
    onSend,
    replyTarget = null,
    replyQuoteText = null,
    onClearReply,
    disabled,
    variant = 'default',
    mentionUsers = [],
    onEphemeralActivity,
  },
  ref,
) {
  const theme = useThemeStore((s) => s.theme)
  const [value, setValue] = useState('')
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState<string | null>(null)
  const [mentionSubs, setMentionSubs] = useState<string[]>([])
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const submitInFlightRef = useRef(false)
  const focusAfterSendRef = useRef(false)

  const {
    pending,
    handleFilesSelected,
    addFilesFromList,
    removePending,
    clearPending,
    restorePending,
  } = useMessageInputAttachments(chatId)

  const {
    voicePhase,
    recordSeconds,
    voiceError,
    voicePreview,
    startVoiceRecording,
    cancelVoiceRecording,
    stopVoiceRecording,
    confirmVoicePreview,
    discardVoicePreview,
    teardownRecorder,
  } = useVoiceRecording()

  const { typingActiveRef } = useMessageInputEphemeral({
    chatId,
    value,
    voicePhase,
    onEphemeralActivity,
  })

  const {
    emojiOpen,
    setEmojiOpen,
    emojiPickerPos,
    emojiInPortal,
    popoverRef,
    emojiPickerPortalRef,
    calcEmojiPickerPosition,
    insertAtCursor,
  } = useMessageInputEmojiPicker({ variant, textareaRef, setValue })

  const scheduleComposerFocus = useCallback(() => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        const el = textareaRef.current
        if (el && !el.disabled) {
          el.focus({ preventScroll: true })
        }
      })
    })
  }, [])

  useEffect(() => {
    scheduleComposerFocus()
  }, [chatId, scheduleComposerFocus])

  useEffect(() => {
    if (!replyTarget) return
    scheduleComposerFocus()
  }, [replyTarget, scheduleComposerFocus])

  useEffect(() => {
    if (sending || disabled) return
    if (!focusAfterSendRef.current) return
    focusAfterSendRef.current = false
    scheduleComposerFocus()
  }, [sending, disabled, scheduleComposerFocus])

  useEffect(() => {
    setMentionSubs([])
    setSendError(null)
  }, [chatId])

  useEffect(() => {
    return () => {
      teardownRecorder()
    }
  }, [teardownRecorder, chatId])

  function handlePaste(e: React.ClipboardEvent<HTMLTextAreaElement>) {
    const items = e.clipboardData?.items
    if (!items) return
    const imageFiles: File[] = []
    for (const item of Array.from(items)) {
      if (item.kind === 'file' && item.type.startsWith('image/')) {
        const file = item.getAsFile()
        if (!file) continue
        const ext = item.type.split('/')[1] ?? 'png'
        const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
        const named = new File([file], `screenshot-${ts}.${ext}`, { type: item.type })
        imageFiles.push(named)
      }
    }
    if (imageFiles.length > 0) {
      e.preventDefault()
      const dt = new DataTransfer()
      imageFiles.forEach((f) => dt.items.add(f))
      void handleFilesSelected(dt.files)
    }
  }

  useImperativeHandle(ref, () => ({
    addFiles: (files) => addFilesFromList(files),
  }))

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await runSubmit()
  }

  async function runSubmit() {
    const body = value.trim()
    const readyIds = pending.filter((p) => p.result !== null).map((p) => p.result!.id)
    if (!body && readyIds.length === 0) return
    if (sending || disabled) return
    if (!tryAcquireMessageSubmitLock(submitInFlightRef)) return

    setSending(true)
    setSendError(null)
    setEmojiOpen(false)
    const snapshot = {
      value,
      mentionSubs: [...mentionSubs],
      pending: [...pending],
      replyId: replyTarget?.id ?? null,
      replyQuote: replyQuoteText ?? null,
    }
    if (typingActiveRef.current) {
      typingActiveRef.current = false
      onEphemeralActivity?.('typing', false)
    }
    setValue('')
    setMentionSubs([])
    clearPending()
    try {
      await onSend(body, readyIds, snapshot.replyId, snapshot.mentionSubs, snapshot.replyQuote)
      onClearReply?.()
    } catch (err) {
      setValue(snapshot.value)
      setMentionSubs(snapshot.mentionSubs)
      restorePending(snapshot.pending)
      setSendError(userFacingMessageFromUnknown(err))
    } finally {
      releaseMessageSubmitLock(submitInFlightRef)
      setSending(false)
      focusAfterSendRef.current = true
    }
  }

  const hasUploading = pending.some((p) => p.uploading)
  const canSend =
    (value.trim().length > 0 || pending.some((p) => p.result !== null)) &&
    !hasUploading &&
    voicePhase === 'idle'

  async function trySubmitFromKeyboard() {
    if (!canSend || disabled || sending || submitInFlightRef.current) return
    await runSubmit()
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    handleComposerEnterSubmit(e, canSend && !disabled && !sending, () => {
      void trySubmitFromKeyboard()
    })
  }

  const onMicClick = useCallback(async () => {
    if (disabled || sending || hasUploading) return
    if (voicePhase === 'recording') {
      await stopVoiceRecording()
      return
    }
    if (voicePhase === 'processing' || voicePhase === 'preview') return
    setEmojiOpen(false)
    await startVoiceRecording()
  }, [disabled, sending, hasUploading, voicePhase, stopVoiceRecording, startVoiceRecording, setEmojiOpen])

  const onSendVoicePreview = useCallback(() => {
    const result = confirmVoicePreview()
    if (!result) return
    const dt = new DataTransfer()
    dt.items.add(result.file)
    addFilesFromList(dt.files, {
      durationSeconds: result.durationSeconds,
      waveform: result.waveform,
    })
    scheduleComposerFocus()
  }, [confirmVoicePreview, addFilesFromList, scheduleComposerFocus])

  return (
    <form
      data-chat-composer
      onSubmit={(e) => void handleSubmit(e)}
      className={`${styles.form}${variant === 'panel' ? ` ${styles.formPanel}` : ''}`}
    >
      {replyTarget && (
        <MessageReplyBanner
          replyTarget={replyTarget}
          replyQuoteText={replyQuoteText}
          onClearReply={onClearReply}
        />
      )}
      <AttachmentChipList items={pending} onRemove={removePending} />
      <MessageVoiceBar
        voicePhase={voicePhase}
        voicePreview={voicePreview}
        recordSeconds={recordSeconds}
        voiceError={voiceError}
        sendError={sendError}
        sending={sending}
        onSendVoicePreview={onSendVoicePreview}
        onDiscard={discardVoicePreview}
        onCancelRecording={cancelVoiceRecording}
      />
      <div className={styles.inputRow}>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className={styles.fileInput}
          aria-hidden
          tabIndex={-1}
          onChange={(e) => {
            void handleFilesSelected(e.target.files)
            e.target.value = ''
            scheduleComposerFocus()
          }}
        />
        <div className={styles.textareaWrap} ref={popoverRef}>
          {mentionUsers.length > 0 ? (
            <MentionAwareTextarea
              ref={textareaRef}
              value={value}
              onChange={setValue}
              users={mentionUsers}
              onPickMention={(sub) =>
                setMentionSubs((prev) => (prev.includes(sub) ? prev : [...prev, sub]))
              }
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              disabled={disabled || sending || voicePhase !== 'idle'}
              placeholder="Сообщение…"
              rows={1}
              textareaClassName={styles.textarea}
            />
          ) : (
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              disabled={disabled || sending || voicePhase !== 'idle'}
              placeholder="Сообщение…"
              rows={1}
              className={styles.textarea}
            />
          )}
          <button
            type="button"
            className={styles.emojiBtn}
            data-emoji-open
            title="Смайлы"
            aria-label="Смайлы"
            aria-expanded={emojiOpen}
            disabled={disabled || sending || voicePhase !== 'idle'}
            onClick={() => {
              if (!emojiOpen && emojiInPortal) calcEmojiPickerPosition()
              setEmojiOpen((v) => !v)
            }}
          >
            <IconSmiley className={styles.emojiBtnGlyph} />
          </button>
          <MessageInputEmojiPicker
            emojiOpen={emojiOpen}
            emojiInPortal={emojiInPortal}
            emojiPickerPos={emojiPickerPos}
            emojiPickerPortalRef={emojiPickerPortalRef}
            theme={theme === 'dark' ? 'dark' : 'light'}
            onEmojiSelect={(e) => insertAtCursor(e.native)}
          />
        </div>
        <div className={styles.composerActions}>
          <button
            type="button"
            className={styles.attachBtn}
            title="Прикрепить файл"
            aria-label="Прикрепить файл"
            disabled={disabled || sending || voicePhase !== 'idle'}
            onClick={() => fileInputRef.current?.click()}
          >
            <IconPaperclip />
          </button>
          <button
            type="button"
            className={`${styles.micBtn}${voicePhase === 'recording' ? ` ${styles.micRecording}` : ''}`}
            title={
              voicePhase === 'recording'
                ? 'Остановить запись'
                : voicePhase === 'processing'
                  ? 'Обработка записи…'
                  : voicePhase === 'preview'
                    ? 'Сначала отправьте или удалите текущую запись'
                    : 'Записать голосовое сообщение'
            }
            aria-label={
              voicePhase === 'recording'
                ? 'Остановить запись голосового сообщения'
                : 'Начать запись голосового сообщения'
            }
            aria-pressed={voicePhase === 'recording'}
            disabled={
              disabled || sending || hasUploading || voicePhase === 'processing' || voicePhase === 'preview'
            }
            onClick={() => void onMicClick()}
          >
            <IconMicrophone />
          </button>
        </div>
        <button type="submit" disabled={disabled || sending || !canSend} className={styles.sendBtn}>
          {sending ? 'Отправка…' : 'Отправить'}
        </button>
      </div>
    </form>
  )
})
