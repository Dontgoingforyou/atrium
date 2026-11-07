import {
  DEFAULT_CHAT_DM_SOUND_ID,
  DEFAULT_NOTIFICATION_SOUND_ID,
  findPresetById,
  resolveStoredPresetId,
  urlForPresetId,
} from '../../domain/sound/soundPresets'

const STORAGE_NOTIFICATION = 'cosmolet:notification_sound_choice'
const STORAGE_CHAT_DM = 'cosmolet:chat_dm_sound_choice'
const STORAGE_NOTIFICATION_VOLUME_PCT = 'cosmolet:notification_sound_volume_pct'
const STORAGE_CHAT_DM_VOLUME_PCT = 'cosmolet:chat_dm_sound_volume_pct'

function readRaw(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function writeRaw(key: string, value: string): void {
  try {
    localStorage.setItem(key, value)
  } catch {
    /* ignore */
  }
}

export function getResolvedNotificationSoundId(): string {
  return resolveStoredPresetId(readRaw(STORAGE_NOTIFICATION), DEFAULT_NOTIFICATION_SOUND_ID)
}

export function getResolvedChatDmSoundId(): string {
  return resolveStoredPresetId(readRaw(STORAGE_CHAT_DM), DEFAULT_CHAT_DM_SOUND_ID)
}

export function setNotificationSoundPresetId(id: string): void {
  if (!findPresetById(id)) {
    return
  }
  writeRaw(STORAGE_NOTIFICATION, id)
}

export function setChatDmSoundPresetId(id: string): void {
  if (!findPresetById(id)) {
    return
  }
  writeRaw(STORAGE_CHAT_DM, id)
}

export function getNotificationSoundUrl(): string {
  const id = getResolvedNotificationSoundId()
  return urlForPresetId(id) ?? urlForPresetId(DEFAULT_NOTIFICATION_SOUND_ID)!
}

export function getChatDmSoundUrl(): string {
  const id = getResolvedChatDmSoundId()
  return urlForPresetId(id) ?? urlForPresetId(DEFAULT_CHAT_DM_SOUND_ID)!
}

/** Нормализация процента громкости для тестов и чтения из storage. */
export function normalizeSoundVolumePct(raw: string | null): number {
  if (raw === null || raw.trim() === '') {
    return 100
  }
  const n = Number(raw)
  if (!Number.isFinite(n)) {
    return 100
  }
  return Math.min(100, Math.max(0, Math.round(n)))
}

export function getNotificationSoundVolumePct(): number {
  return normalizeSoundVolumePct(readRaw(STORAGE_NOTIFICATION_VOLUME_PCT))
}

export function getChatDmSoundVolumePct(): number {
  return normalizeSoundVolumePct(readRaw(STORAGE_CHAT_DM_VOLUME_PCT))
}

function clampVolumePctInput(pct: number): number {
  if (!Number.isFinite(pct)) {
    return 100
  }
  return Math.min(100, Math.max(0, Math.round(pct)))
}

export function setNotificationSoundVolumePct(pct: number): void {
  writeRaw(STORAGE_NOTIFICATION_VOLUME_PCT, String(clampVolumePctInput(pct)))
}

export function setChatDmSoundVolumePct(pct: number): void {
  writeRaw(STORAGE_CHAT_DM_VOLUME_PCT, String(clampVolumePctInput(pct)))
}
