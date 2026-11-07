import { useEffect, useRef } from 'react'

import type { VoicePhase } from './useVoiceRecording'

type EphemeralEvent = 'typing' | 'voice_recording'

type Options = {
  chatId: string
  value: string
  voicePhase: VoicePhase
  onEphemeralActivity?: (event: EphemeralEvent, active: boolean) => void
}

/**
 * Эфемерные WS-события композера: typing / voice_recording.
 * Возвращает ref «печатает сейчас» для сброса при отправке.
 */
export function useMessageInputEphemeral({
  chatId,
  value,
  voicePhase,
  onEphemeralActivity,
}: Options) {
  const typingActiveRef = useRef(false)

  useEffect(() => {
    if (!onEphemeralActivity) return
    if (voicePhase !== 'recording') {
      onEphemeralActivity('voice_recording', false)
      return
    }
    onEphemeralActivity('voice_recording', true)
    const interval = window.setInterval(() => onEphemeralActivity('voice_recording', true), 2500)
    return () => window.clearInterval(interval)
  }, [voicePhase, onEphemeralActivity])

  useEffect(() => {
    if (!onEphemeralActivity) return
    const hasText = value.trim().length > 0
    if (!hasText) {
      if (typingActiveRef.current) {
        typingActiveRef.current = false
        onEphemeralActivity('typing', false)
      }
      return
    }
    typingActiveRef.current = true
    onEphemeralActivity('typing', true)
    const interval = window.setInterval(() => onEphemeralActivity('typing', true), 2500)
    return () => window.clearInterval(interval)
  }, [value, onEphemeralActivity])

  useEffect(() => {
    if (typingActiveRef.current && onEphemeralActivity) {
      onEphemeralActivity('typing', false)
    }
    typingActiveRef.current = false
  }, [chatId, onEphemeralActivity])

  return { typingActiveRef }
}
