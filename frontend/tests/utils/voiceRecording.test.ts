import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'

import {
  buildVoiceRecordingFilename,
  captureWaveformFromBlob,
  isPortalVoiceRecordingFilename,
} from '../../src/utils/voiceRecording'

describe('isPortalVoiceRecordingFilename', () => {
  it('распознаёт имя файла записи портала', () => {
    expect(isPortalVoiceRecordingFilename(buildVoiceRecordingFilename('webm'))).toBe(true)
  })

  it('отклоняет произвольные имена', () => {
    expect(isPortalVoiceRecordingFilename('lecture-notes.webm')).toBe(false)
    expect(isPortalVoiceRecordingFilename('voice-not-a-date.m4a')).toBe(false)
  })
})

describe('captureWaveformFromBlob', () => {
  const BARS = 28

  function makeFakeChannelData(length: number): Float32Array {
    const data = new Float32Array(length)
    for (let i = 0; i < length; i++) {
      data[i] = Math.sin(i * 0.1) * 0.8
    }
    return data
  }

  beforeEach(() => {
    const fakeBuffer = {
      getChannelData: () => makeFakeChannelData(44100),
    }
    const mockCtx = {
      decodeAudioData: vi.fn().mockResolvedValue(fakeBuffer),
    }
    vi.stubGlobal(
      'OfflineAudioContext',
      vi.fn(function () {
        return mockCtx
      }),
    )
    // Убеждаемся что AudioContext не определён, чтобы OfflineAudioContext был единственным путём
    vi.stubGlobal('AudioContext', undefined)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('возвращает массив из 28 нормализованных значений', async () => {
    const blob = new Blob([new Uint8Array(256)], { type: 'audio/webm' })
    const result = await captureWaveformFromBlob(blob)

    expect(result).not.toBeNull()
    expect(result!.length).toBe(BARS)
    result!.forEach((v) => {
      expect(v).toBeGreaterThanOrEqual(0)
      expect(v).toBeLessThanOrEqual(1)
    })
  })

  it('максимум нормализован к 1.0', async () => {
    const blob = new Blob([new Uint8Array(256)], { type: 'audio/webm' })
    const result = await captureWaveformFromBlob(blob)

    expect(result).not.toBeNull()
    expect(Math.max(...result!)).toBeCloseTo(1.0, 2)
  })

  it('возвращает null при ошибке декодирования', async () => {
    const failCtx = {
      decodeAudioData: vi.fn().mockRejectedValue(new Error('decode error')),
    }
    vi.stubGlobal(
      'OfflineAudioContext',
      vi.fn(function () {
        return failCtx
      }),
    )

    const blob = new Blob([new Uint8Array(4)], { type: 'audio/webm' })
    const result = await captureWaveformFromBlob(blob)

    expect(result).toBeNull()
  })

  it('возвращает null если OfflineAudioContext недоступен', async () => {
    vi.stubGlobal('OfflineAudioContext', undefined)
    vi.stubGlobal('AudioContext', undefined)

    const blob = new Blob([new Uint8Array(256)], { type: 'audio/webm' })
    const result = await captureWaveformFromBlob(blob)

    expect(result).toBeNull()
  })
})
