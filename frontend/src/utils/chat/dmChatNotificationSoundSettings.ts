import { DM_NOTIFICATION_SOUND_BY_CHAT_KEY } from '../../constants/chatStorage'

function readMap(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(DM_NOTIFICATION_SOUND_BY_CHAT_KEY)
    if (raw == null) {
      return {}
    }
    const parsed: unknown = JSON.parse(raw)
    if (typeof parsed !== 'object' || parsed === null) {
      return {}
    }
    return parsed as Record<string, boolean>
  } catch {
    return {}
  }
}

function writeMap(m: Record<string, boolean>): void {
  try {
    if (Object.keys(m).length === 0) {
      localStorage.removeItem(DM_NOTIFICATION_SOUND_BY_CHAT_KEY)
    } else {
      localStorage.setItem(DM_NOTIFICATION_SOUND_BY_CHAT_KEY, JSON.stringify(m))
    }
  } catch {
    /* ignore */
  }
}

export function getDmChatNotificationSoundEnabled(chatId: string): boolean {
  return readMap()[chatId] !== false
}

export function setDmChatNotificationSoundEnabled(chatId: string, enabled: boolean): void {
  const m = readMap()
  if (enabled) {
    delete m[chatId]
  } else {
    m[chatId] = false
  }
  writeMap(m)
}
