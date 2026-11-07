import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import type { ChatAttachment } from '../../../types/chat'
import { formatBytes } from '../../../utils/fileUtils'
import styles from '@/styles/modules/chat/ChatMessageListOverlays.module.css'

const WAVE_BARS = 28

function hashToUnit(s: string): number {
  let h = 2166136261
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return ((h >>> 0) % 10000) / 10000
}

/** Запасной бар: детерминированный псевдослучай от id — используется если waveform не сохранена. */
function fallbackBarHeight(id: string, i: number): number {
  const t = hashToUnit(`${id}|wave|${i}`)
  return 0.28 + t * 0.72
}

function formatVoiceTime(sec: number): string {
  if (!Number.isFinite(sec) || sec < 0) return '0:00'
  const s = Math.floor(sec)
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${m}:${r.toString().padStart(2, '0')}`
}

type Tone = 'mine' | 'other'

function VoiceMessageAttachmentInner({
  att,
  tone,
  onTranscribe,
  transcribing = false,
}: {
  att: ChatAttachment
  tone: Tone
  onTranscribe?: () => void
  transcribing?: boolean
}) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const durationResolvedRef = useRef(false)
  const [playing, setPlaying] = useState(false)
  /**
   * null — длительность ещё не известна (часто для webm/opus до подгрузки метаданных).
   * Инициализируется сохранённым значением если доступно.
   */
  const [duration, setDuration] = useState<number | null>(att.voice_duration_seconds ?? null)
  const [current, setCurrent] = useState(0)

  const bars = useMemo(() => {
    const stored = att.voice_waveform
    if (stored && stored.length === WAVE_BARS) {
      return stored.map((v) => 0.28 + v * 0.72)
    }
    return Array.from({ length: WAVE_BARS }, (_, i) => fallbackBarHeight(att.id, i))
  }, [att.id, att.voice_waveform])

  const dur = duration ?? 0
  const progress = dur > 0 ? Math.min(1, current / dur) : 0

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

  useEffect(() => {
    const el = audioRef.current
    if (!el) return

    durationResolvedRef.current = att.voice_duration_seconds != null

    const syncDuration = () => {
      const t = el.duration
      if (Number.isFinite(t) && t > 0 && !Number.isNaN(t)) {
        durationResolvedRef.current = true
        setDuration(t)
      }
    }

    const onPlay = () => setPlaying(true)
    const onPause = () => setPlaying(false)
    const onEnded = () => {
      setPlaying(false)
      setCurrent(0)
    }
    const onTime = () => setCurrent(el.currentTime)

    const durEvents = ['loadedmetadata', 'durationchange', 'loadeddata', 'canplay', 'canplaythrough'] as const
    durEvents.forEach((ev) => el.addEventListener(ev, syncDuration))

    el.addEventListener('play', onPlay)
    el.addEventListener('pause', onPause)
    el.addEventListener('ended', onEnded)
    el.addEventListener('timeupdate', onTime)

    el.preload = 'auto'
    el.load()

    const poll = window.setInterval(() => {
      if (durationResolvedRef.current) {
        window.clearInterval(poll)
        return
      }
      syncDuration()
    }, 150)
    const stopPoll = window.setTimeout(() => window.clearInterval(poll), 4000)

    return () => {
      window.clearInterval(poll)
      window.clearTimeout(stopPoll)
      durEvents.forEach((ev) => el.removeEventListener(ev, syncDuration))
      el.removeEventListener('play', onPlay)
      el.removeEventListener('pause', onPause)
      el.removeEventListener('ended', onEnded)
      el.removeEventListener('timeupdate', onTime)
    }
  }, [att.download_url, att.voice_duration_seconds])

  const rootClass =
    tone === 'mine' ? `${styles.voiceAttach} ${styles.voiceAttachMine}` : `${styles.voiceAttach} ${styles.voiceAttachOther}`

  return (
    <div className={rootClass}>
      <audio ref={audioRef} preload="auto" src={att.download_url} className={styles.voiceAttachAudioHidden}>
        <a href={att.download_url} download={att.original_filename}>
          Скачать
        </a>
      </audio>
      <div className={styles.voiceAttachMain}>
        <button
          type="button"
          className={tone === 'mine' ? styles.voicePlayMine : styles.voicePlayOther}
          onClick={toggle}
          aria-label={playing ? 'Пауза' : 'Воспроизвести'}
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
        <div className={styles.voiceWave} aria-hidden>
          {bars.map((h, i) => {
            const lit = (i + 1) / WAVE_BARS <= progress
            return (
              <span
                key={i}
                className={lit ? styles.voiceBarLit : styles.voiceBarDim}
                style={{ height: `${Math.round(h * 28)}px` }}
              />
            )
          })}
        </div>
      </div>
      <div className={tone === 'mine' ? styles.voiceMetaMine : styles.voiceMetaOther}>
        <span>
          {formatVoiceTime(current)} /{' '}
          {duration === null ? '…' : formatVoiceTime(duration)}
          {att.file_size > 0 ? `, ${formatBytes(att.file_size)}` : ''}
        </span>
      </div>
      {att.transcript ? (
        <div className={styles.voiceTranscript}>{att.transcript}</div>
      ) : onTranscribe ? (
        <button
          type="button"
          className={styles.voiceTranscribeBtn}
          onClick={onTranscribe}
          disabled={transcribing}
        >
          {transcribing && <span className={styles.voiceTranscribeSpinner} aria-hidden />}
          {transcribing ? 'Транскрибирую…' : 'Транскрибировать'}
        </button>
      ) : null}
    </div>
  )
}

/** При смене URL новый инстанс — состояние плеера сбрасывается без setState в эффекте. */
export function VoiceMessageAttachment({
  att,
  tone,
  onTranscribe,
  transcribing = false,
}: {
  att: ChatAttachment
  tone: Tone
  onTranscribe?: () => void
  transcribing?: boolean
}) {
  return (
    <VoiceMessageAttachmentInner
      key={att.download_url}
      att={att}
      tone={tone}
      onTranscribe={onTranscribe}
      transcribing={transcribing}
    />
  )
}
