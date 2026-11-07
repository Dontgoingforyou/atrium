/** Выбор MIME для MediaRecorder (голосовые сообщения). */

export type VoiceRecordingPick = { mimeType: string; extension: string }

const MIME_CANDIDATES: readonly string[] = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/ogg',
  'audio/mp4',
]

function extensionForMime(mime: string): string {
  const m = mime.toLowerCase()
  if (m.includes('webm')) return 'webm'
  if (m.includes('ogg')) return 'ogg'
  if (m.includes('mp4') || m.includes('mpeg')) return 'm4a'
  return 'webm'
}

export function pickVoiceRecordingMime(): VoiceRecordingPick {
  if (typeof MediaRecorder === 'undefined') {
    return { mimeType: '', extension: 'webm' }
  }
  for (const mime of MIME_CANDIDATES) {
    if (MediaRecorder.isTypeSupported(mime)) {
      return { mimeType: mime, extension: extensionForMime(mime) }
    }
  }
  return { mimeType: '', extension: 'webm' }
}

export function buildVoiceRecordingFilename(extension: string): string {
  const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
  return `voice-${ts}.${extension}`
}

/** Имена вида ``voice-2026-05-07T18-48-12.webm`` — запись из портала, показываем компактный плеер. */
export function isPortalVoiceRecordingFilename(filename: string): boolean {
  return /^voice-\d{4}-\d{2}-\d{2}T/i.test(filename.trim())
}

const WAVEFORM_BARS = 28

/**
 * Анализирует Blob аудиозаписи и возвращает нормализованный массив пиков амплитуды
 * длиной WAVEFORM_BARS (каждое значение 0.0–1.0).
 *
 * Использует OfflineAudioContext для декодирования без воспроизведения.
 * При недоступном API или ошибке возвращает null.
 */
export async function captureWaveformFromBlob(blob: Blob): Promise<number[] | null> {
  if (typeof OfflineAudioContext === 'undefined' && typeof AudioContext === 'undefined') {
    return null
  }
  try {
    const arrayBuffer = await blob.arrayBuffer()
    const ctx = new OfflineAudioContext(1, 1, 44100)
    let decoded: AudioBuffer
    try {
      decoded = await ctx.decodeAudioData(arrayBuffer)
    } catch {
      return null
    }
    const data = decoded.getChannelData(0)
    const blockSize = Math.floor(data.length / WAVEFORM_BARS)
    if (blockSize === 0) return null

    const peaks: number[] = []
    for (let i = 0; i < WAVEFORM_BARS; i++) {
      let max = 0
      const start = i * blockSize
      const end = Math.min(start + blockSize, data.length)
      for (let j = start; j < end; j++) {
        const abs = Math.abs(data[j])
        if (abs > max) max = abs
      }
      peaks.push(max)
    }

    const globalMax = Math.max(...peaks, 1e-6)
    return peaks.map((v) => Math.round((v / globalMax) * 1000) / 1000)
  } catch {
    return null
  }
}
