import { useState } from 'react'

import type { ChatAttachment } from '../../../types/chat'
import { useStableImageUrl } from '../../../hooks/useStableImageUrl'
import { fileIcon, formatBytes } from '../../../utils/fileUtils'
import { isPortalVoiceRecordingFilename } from '../../../utils/voiceRecording'
import { VoiceMessageAttachment } from './VoiceMessageAttachment'
import { MediaLightbox } from '../../ui/MediaLightbox'
import layout from '@/styles/modules/chat/ChatMessageListLayout.module.css'
import overlay from '@/styles/modules/chat/ChatMessageListOverlays.module.css'

export function AttachmentItem({
  att,
  tone = 'other',
  onTranscribe,
  transcribing = false,
}: {
  att: ChatAttachment
  tone?: 'mine' | 'other'
  /** Запросить транскрибацию голосового сообщения. */
  onTranscribe?: () => void
  transcribing?: boolean
}) {
  const isImage = att.content_type.startsWith('image/')
  const isAudio = att.content_type.startsWith('audio/')
  const isPdf = att.content_type === 'application/pdf'
  const [lightboxOpen, setLightboxOpen] = useState(false)
  const stableUrl = useStableImageUrl(isImage ? att.download_url : undefined)

  if (isImage) {
    return (
      <>
        <button
          type="button"
          className={layout.attachmentImageWrap}
          onClick={() => setLightboxOpen(true)}
          title={att.original_filename}
          aria-label={`Открыть вложение ${att.original_filename}`}
        >
          {stableUrl && (
            <img
              src={stableUrl}
              alt={att.original_filename}
              className={layout.attachmentImage}
              loading="eager"
            />
          )}
        </button>
        {lightboxOpen ? (
          <MediaLightbox
            url={att.download_url}
            filename={att.original_filename}
            contentType={att.content_type}
            onClose={() => setLightboxOpen(false)}
          />
        ) : null}
      </>
    )
  }
  if (isAudio) {
    if (isPortalVoiceRecordingFilename(att.original_filename)) {
      return (
        <VoiceMessageAttachment
          att={att}
          tone={tone}
          onTranscribe={onTranscribe}
          transcribing={transcribing}
        />
      )
    }
    return (
      <div className={overlay.attachmentAudio}>
        <span className={overlay.attachmentAudioLabel} title={att.original_filename}>
          {att.original_filename}
        </span>
        <audio
          className={overlay.attachmentAudioPlayer}
          controls
          preload="metadata"
          src={att.download_url}
          aria-label={`Аудио: ${att.original_filename}`}
        >
          <a href={att.download_url} download={att.original_filename}>
            Скачать аудио
          </a>
        </audio>
      </div>
    )
  }
  return (
    <a
      className={overlay.attachmentFile}
      href={att.download_url}
      target="_blank"
      rel="noopener noreferrer"
      {...(!isPdf && { download: att.original_filename })}
    >
      <span className={overlay.attachmentFileIcon} aria-hidden>{fileIcon(att.content_type)}</span>
      <span className={overlay.attachmentFileName}>{att.original_filename}</span>
      <span className={overlay.attachmentFileSize}>{formatBytes(att.file_size)}</span>
    </a>
  )
}
