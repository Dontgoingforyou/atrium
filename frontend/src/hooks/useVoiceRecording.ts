import { useCallback, useEffect, useRef, useState } from 'react'
import {
  buildVoiceRecordingFilename,
  captureWaveformFromBlob,
  pickVoiceRecordingMime,
} from '../utils/voiceRecording'

export type VoicePhase = 'idle' | 'recording' | 'processing' | 'preview'

export type VoicePreview = {
  file: File
  durationSeconds: number
  waveform: number[]
  url: string
}

type UseVoiceRecordingReturn = {
  voicePhase: VoicePhase
  recordSeconds: number
  voiceError: string | null
  /** Заполнен, когда voicePhase === 'preview': запись готова к прослушиванию перед отправкой. */
  voicePreview: VoicePreview | null
  startVoiceRecording: () => Promise<void>
  cancelVoiceRecording: () => void
  /** Останавливает запись и переводит в фазу preview (не отправляет). */
  stopVoiceRecording: () => Promise<void>
  /** Подтвердить отправку preview-записи: возвращает данные для загрузки и очищает preview. */
  confirmVoicePreview: () => { file: File; durationSeconds: number; waveform: number[] } | null
  /** Отменить preview-запись (не отправлять). */
  discardVoicePreview: () => void
  teardownRecorder: () => void
}

export function useVoiceRecording(): UseVoiceRecordingReturn {
  const [voicePhase, setVoicePhase] = useState<VoicePhase>('idle')
  const [recordSeconds, setRecordSeconds] = useState(0)
  const [voiceError, setVoiceError] = useState<string | null>(null)
  const [voicePreview, setVoicePreview] = useState<VoicePreview | null>(null)

  const mediaStreamRef = useRef<MediaStream | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const recordChunksRef = useRef<BlobPart[]>([])
  const recordMimeRef = useRef<string>('')
  const recordExtRef = useRef<string>('webm')
  const recordTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const previewUrlRef = useRef<string | null>(null)
  const teardownRef = useRef<() => void>(() => {})

  const stopRecordTimer = useCallback(() => {
    if (recordTimerRef.current) {
      clearInterval(recordTimerRef.current)
      recordTimerRef.current = null
    }
  }, [])

  const releasePreviewUrl = useCallback(() => {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current)
      previewUrlRef.current = null
    }
  }, [])

  const teardownRecorder = useCallback(() => {
    stopRecordTimer()
    try {
      mediaRecorderRef.current?.stop()
    } catch {
      /* ignore */
    }
    mediaRecorderRef.current = null
    recordChunksRef.current = []
    mediaStreamRef.current?.getTracks().forEach((t) => {
      try {
        t.stop()
      } catch {
        /* ignore */
      }
    })
    mediaStreamRef.current = null
    releasePreviewUrl()
    setVoicePreview(null)
  }, [stopRecordTimer, releasePreviewUrl])

  // Страхуем consumer: при unmount без явного teardown освобождаем
  // микрофон/таймер/object URL, чтобы не остался активным захват потока.
  useEffect(() => {
    teardownRef.current = teardownRecorder
    return () => {
      teardownRef.current()
    }
  }, [teardownRecorder])

  const startVoiceRecording = useCallback(async () => {
    setVoiceError(null)
    if (!navigator.mediaDevices?.getUserMedia) {
      setVoiceError('Запись голоса не поддерживается в этом браузере')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaStreamRef.current = stream
      recordChunksRef.current = []
      const { mimeType, extension } = pickVoiceRecordingMime()
      recordMimeRef.current = mimeType
      recordExtRef.current = extension
      const options = mimeType ? { mimeType } : undefined
      const rec = new MediaRecorder(stream, options)
      mediaRecorderRef.current = rec
      rec.ondataavailable = (ev: BlobEvent) => {
        if (ev.data && ev.data.size > 0) recordChunksRef.current.push(ev.data)
      }
      rec.start(250)
      setVoicePhase('recording')
      setRecordSeconds(0)
      stopRecordTimer()
      recordTimerRef.current = setInterval(() => {
        setRecordSeconds((s) => s + 1)
      }, 1000)
    } catch {
      setVoiceError('Не удалось получить доступ к микрофону')
      teardownRecorder()
      setVoicePhase('idle')
    }
  }, [stopRecordTimer, teardownRecorder])

  const cancelVoiceRecording = useCallback(() => {
    teardownRecorder()
    setVoicePhase('idle')
    setRecordSeconds(0)
  }, [teardownRecorder])

  const stopVoiceRecording = useCallback(async () => {
    const rec = mediaRecorderRef.current
    const stream = mediaStreamRef.current
    if (!rec || rec.state === 'inactive') return
    setVoicePhase('processing')
    stopRecordTimer()
    const durationSeconds = recordSeconds
    await new Promise<void>((resolve) => {
      rec.addEventListener('stop', () => resolve(), { once: true })
      try {
        if (rec.state !== 'inactive') {
          rec.stop()
        } else {
          resolve()
        }
      } catch {
        resolve()
      }
    })
    stream?.getTracks().forEach((t) => {
      try {
        t.stop()
      } catch {
        /* ignore */
      }
    })
    mediaStreamRef.current = null
    mediaRecorderRef.current = null
    setRecordSeconds(0)
    const mime = recordMimeRef.current || 'audio/webm'
    const ext = recordExtRef.current
    const blob = new Blob(recordChunksRef.current, { type: mime })
    recordChunksRef.current = []
    if (blob.size < 256) {
      setVoiceError('Запись слишком короткая')
      setVoicePhase('idle')
      return
    }
    const waveform = (await captureWaveformFromBlob(blob)) ?? []
    const name = buildVoiceRecordingFilename(ext)
    const file = new File([blob], name, { type: mime })
    releasePreviewUrl()
    const url = URL.createObjectURL(blob)
    previewUrlRef.current = url
    setVoicePreview({ file, durationSeconds, waveform, url })
    setVoicePhase('preview')
  }, [recordSeconds, stopRecordTimer, releasePreviewUrl])

  const confirmVoicePreview = useCallback(() => {
    const preview = voicePreview
    releasePreviewUrl()
    setVoicePreview(null)
    setVoicePhase('idle')
    if (!preview) return null
    return {
      file: preview.file,
      durationSeconds: preview.durationSeconds,
      waveform: preview.waveform,
    }
  }, [voicePreview, releasePreviewUrl])

  const discardVoicePreview = useCallback(() => {
    releasePreviewUrl()
    setVoicePreview(null)
    setVoicePhase('idle')
  }, [releasePreviewUrl])

  return {
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
  }
}
