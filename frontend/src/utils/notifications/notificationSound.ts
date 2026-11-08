import { getDmChatNotificationSoundEnabled } from '../chat/dmChatNotificationSoundSettings'
import {
  getChatDmSoundUrl,
  getChatDmSoundVolumePct,
  getNotificationSoundUrl,
  getNotificationSoundVolumePct,
} from './soundChoiceStorage'

const STORAGE_KEY = 'atrium:notification_sound_enabled'

export function getNotificationSoundEnabled(): boolean {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v === null) {
      return true
    }
    return v === '1'
  } catch {
    return true
  }
}

export function setNotificationSoundEnabled(enabled: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEY, enabled ? '1' : '0')
  } catch {
    /* ignore */
  }
}

let audioCtx: AudioContext | null = null
let _browserAudioUnlockInstalled = false

/**
 * Снимает блокировку автовоспроизведения (браузер требует жеста пользователя).
 * Вызвать из корня приложения; достаточно одного клика/клавиши в области страницы.
 */
export function installNotificationAudioBrowserUnlock(): void {
  if (typeof document === 'undefined' || _browserAudioUnlockInstalled) {
    return
  }
  _browserAudioUnlockInstalled = true

  const opts = { capture: true } as const

  const run = (): void => {
    document.removeEventListener('pointerdown', run, opts)
    document.removeEventListener('keydown', run, opts)
    try {
      const url = getNotificationSoundUrl()
      if (url) {
        const a = new Audio(url)
        a.volume = 0.0001
        void a.play().then(() => {
          a.pause()
          a.currentTime = 0
        })
      } else {
        const ctx = getAudioContext()
        if (ctx.state === 'suspended') {
          void ctx.resume()
        }
      }
    } catch {
      /* ignore */
    }
  }

  document.addEventListener('pointerdown', run, opts)
  document.addEventListener('keydown', run, opts)
}

function getAudioContext(): AudioContext {
  if (typeof window === 'undefined') {
    throw new Error('AudioContext unavailable')
  }
  const Ctx =
    window.AudioContext
    ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
  if (!Ctx) {
    throw new Error('AudioContext unavailable')
  }
  if (!audioCtx) {
    audioCtx = new Ctx()
  }
  return audioCtx
}

async function tryPlayFile(url: string, volume01: number): Promise<boolean> {
  try {
    const a = new Audio(url)
    const v = Math.min(1, Math.max(0, volume01))
    a.volume = Number.isFinite(v) ? v : 1
    await a.play()
    return true
  } catch {
    return false
  }
}

export async function previewSoundSample(url: string, volume01: number): Promise<void> {
  try {
    await tryPlayFile(url, volume01)
  } catch {
    /* автовоспроизведение */
  }
}

function playSyntheticNotification(): void {
  const ctx = getAudioContext()
  if (ctx.state === 'suspended') {
    void ctx.resume()
  }
  const t0 = ctx.currentTime
  const master = ctx.createGain()
  master.gain.setValueAtTime(0.0001, t0)
  master.gain.exponentialRampToValueAtTime(0.1, t0 + 0.02)
  master.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.24)
  master.connect(ctx.destination)

  const osc1 = ctx.createOscillator()
  osc1.type = 'sine'
  osc1.frequency.setValueAtTime(880, t0)
  osc1.frequency.setValueAtTime(660, t0 + 0.08)
  osc1.connect(master)
  osc1.start(t0)
  osc1.stop(t0 + 0.2)

  const osc2 = ctx.createOscillator()
  osc2.type = 'sine'
  osc2.frequency.setValueAtTime(1320, t0)
  osc2.frequency.setValueAtTime(990, t0 + 0.1)
  osc2.connect(master)
  osc2.start(t0)
  osc2.stop(t0 + 0.18)
}

/**
 * Сигнал для упоминаний/колокольчика (и сопутствующие уведомления, не личные чаты).
 * ЛС — `playDirectMessageNotificationSound`. Сначала выбранный файл, иначе синтетика.
 */
export async function playNotificationSound(): Promise<void> {
  if (!getNotificationSoundEnabled()) {
    return
  }
  try {
    const url = getNotificationSoundUrl()
    if (url) {
      const vol01 = getNotificationSoundVolumePct() / 100
      const ok = await tryPlayFile(url, vol01)
      if (ok) {
        return
      }
    }
    playSyntheticNotification()
  } catch {
    /* Web Audio / автовоспроизведение */
  }
}

export type DirectMessageSoundOptions = {
  /** Обход mute конкретного чата (например @упоминание в ЛС); глобальный тумблер звука учитывается. */
  bypassPerChatMute?: boolean
}

/**
 * Звук при новом сообщении в личном чате: учитывает глобальный тумблер и per-chat.
 * Без fallback на синтетику — только файл (как продуктовый сигнал для ЛС).
 */
export async function playDirectMessageNotificationSound(
  chatId: string,
  options?: DirectMessageSoundOptions,
): Promise<void> {
  if (!getNotificationSoundEnabled()) {
    return
  }
  if (!options?.bypassPerChatMute && !getDmChatNotificationSoundEnabled(chatId)) {
    return
  }
  const url = getChatDmSoundUrl()
  if (!url) {
    return
  }
  try {
    const vol01 = getChatDmSoundVolumePct() / 100
    await tryPlayFile(url, vol01)
  } catch {
    /* автовоспроизведение */
  }
}
