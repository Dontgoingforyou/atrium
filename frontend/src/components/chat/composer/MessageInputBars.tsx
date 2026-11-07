import type { ChatMessage } from '../../../types/chat'
import type { VoicePreview } from '../../../hooks/useVoiceRecording'
import { VoiceRecordPreview } from './VoiceRecordPreview'
import styles from '@/styles/modules/chat/MessageInput.module.css'
import bannerStyles from '@/styles/modules/chat/MessageInputBanners.module.css'

export function MessageReplyBanner({
  replyTarget,
  replyQuoteText,
  onClearReply,
}: {
  replyTarget: ChatMessage
  replyQuoteText: string | null
  onClearReply?: () => void
}) {
  const snippet = (replyQuoteText || replyTarget.body || '').trim()
  return (
    <div className={bannerStyles.replyBanner}>
      <div className={bannerStyles.replyBannerText}>
        <span className={bannerStyles.replyBannerLabel}>
          {replyQuoteText ? 'Ответ с цитатой' : 'Ответ на сообщение'}
        </span>
        <span
          className={bannerStyles.replyBannerSnippet}
          title={replyQuoteText || replyTarget.body || ''}
        >
          {snippet.slice(0, 140)}
          {snippet.length > 140 ? '…' : ''}
        </span>
      </div>
      <button
        type="button"
        className={bannerStyles.replyBannerClose}
        aria-label="Отменить ответ"
        onClick={() => onClearReply?.()}
      >
        ×
      </button>
    </div>
  )
}

export function MessageVoiceBar({
  voicePhase,
  voicePreview,
  recordSeconds,
  voiceError,
  sendError,
  sending,
  onSendVoicePreview,
  onDiscard,
  onCancelRecording,
}: {
  voicePhase: string
  voicePreview: VoicePreview | null
  recordSeconds: number
  voiceError: string | null
  sendError: string | null
  sending: boolean
  onSendVoicePreview: () => void
  onDiscard: () => void
  onCancelRecording: () => void
}) {
  return (
    <>
      {(voiceError || sendError) && (
        <p className={`${bannerStyles.composerError} text-muted`} role="alert">
          {voiceError ?? sendError}
        </p>
      )}
      {voicePhase === 'recording' && (
        <div className={styles.recordingMeta}>
          <span className={styles.recordingTimer} aria-live="polite">
            Запись {recordSeconds} с
          </span>
          <button
            type="button"
            className={styles.cancelRecordBtn}
            onClick={onCancelRecording}
            aria-label="Отменить запись голоса"
          >
            Отменить
          </button>
        </div>
      )}
      {voicePhase === 'preview' && voicePreview && (
        <VoiceRecordPreview
          preview={voicePreview}
          onSend={onSendVoicePreview}
          onDiscard={onDiscard}
          disabled={sending}
        />
      )}
    </>
  )
}
