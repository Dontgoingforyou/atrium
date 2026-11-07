import { useCallback, useEffect, useRef, useState } from 'react'
import type { VoicePreview } from '../../../hooks/useVoiceRecording'
import styles from '@/styles/modules/chat/MessageInput.module.css'

function formatVoiceTime(sec: number): string {
  if (!Number.isFinite(sec) || sec < 0) return '0:00'
  const s = Math.floor(sec)
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${m}:${r.toString().padStart(2, '0')}`
}

type Props = {
  preview: VoicePreview
  onSend: () => void
  onDiscard: () => void
  disabled?: boolean
}

/** Прослушивание записанного голосового сообщения перед отправкой в чат. */
export function VoiceRecordPreview({ preview, onSend, onDiscard, disabled }: Props) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [playing, setPlaying] = useState(false)
  const [current, setCurrent] = useState(0)

  useEffect(() => {
    const el = audioRef.current
    if (!el) return
    const onPlay = () => setPlaying(true)
    const onPause = () => setPlaying(false)
    const onEnded = () => {
      setPlaying(false)
      setCurrent(0)
    }
    const onTime = () => setCurrent(el.currentTime)
    el.addEventListener('play', onPlay)
    el.addEventListener('pause', onPause)
    el.addEventListener('ended', onEnded)
    el.addEventListener('timeupdate', onTime)
    return () => {
      el.removeEventListener('play', onPlay)
      el.removeEventListener('pause', onPause)
      el.removeEventListener('ended', onEnded)
      el.removeEventListener('timeupdate', onTime)
    }
  }, [])

  const toggle = useCallback(() => {
    const el = audioRef.current
    if (!el) return
    if (playing) {
      el.pause()
    } else {
      void el.play().catch(() => {
        /* автозапуск / политика браузера */
      })
    }
  }, [playing])

  return (
    <div className={styles.voicePreviewRow}>
      <audio ref={audioRef} preload="auto" src={preview.url} className={styles.voicePreviewAudioHidden} />
      <button
        type="button"
        className={styles.voicePreviewPlayBtn}
        onClick={toggle}
        aria-label={playing ? 'Пауза' : 'Прослушать голосовое сообщение'}
        disabled={disabled}
      >
        {playing ? (
          <span className={styles.voicePauseBars} aria-hidden>
            <span className={styles.voicePauseBar} />
            <span className={styles.voicePauseBar} />
          </span>
        ) : (
          <span className={styles.voicePlayTri} aria-hidden />
        )}
      </button>
      <span className={styles.voicePreviewTime} aria-live="polite">
        {formatVoiceTime(current)} / {formatVoiceTime(preview.durationSeconds)}
      </span>
      <button
        type="button"
        className={styles.voicePreviewDiscardBtn}
        onClick={onDiscard}
        disabled={disabled}
        aria-label="Удалить запись"
      >
        Удалить
      </button>
      <button
        type="button"
        className={styles.voicePreviewSendBtn}
        onClick={onSend}
        disabled={disabled}
        aria-label="Прикрепить голосовое сообщение"
      >
        Прикрепить
      </button>
    </div>
  )
}
