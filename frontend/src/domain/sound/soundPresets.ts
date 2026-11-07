/**
 * Пресеты звуков портала (файлы в `frontend/public/sounds/`).
 * Новый файл: добавить в `public/sounds/` и строку в `SOUND_PRESETS` (`.wav` или `.mp3`).
 */

export type SoundPreset = {
  id: string
  label: string
  /** Путь относительно origin, Vite public */
  url: string
}

/** Дефолт для колокольчика / упоминаний — прежний `notification.wav`. */
export const DEFAULT_NOTIFICATION_SOUND_ID = 'notification'

/** Дефолт для новых ЛС — прежний `new-message-for-you-man.wav`. */
export const DEFAULT_CHAT_DM_SOUND_ID = 'new-message-for-you-man'

export const SOUND_PRESETS: readonly SoundPreset[] = [
  { id: 'notification', label: 'Стандарт портала', url: '/sounds/notification.wav' },
  { id: 'new-message-for-you-man', label: 'Сообщение для вас (классика ЛС)', url: '/sounds/new-message-for-you-man.wav' },
  { id: 'bright-clear-ring', label: 'Ясный короткий звонок', url: '/sounds/bright-clear-ring.wav' },
  { id: 'calm-appearance', label: 'Спокойное появление', url: '/sounds/calm-appearance.wav' },
  { id: 'cybernetic', label: 'Кибернетический', url: '/sounds/cybernetic.wav' },
  { id: 'error-notification', label: 'Сигнал «ошибка»', url: '/sounds/error-notification.wav' },
  { id: 'fine-light-squeak', label: 'Лёгкий писк', url: '/sounds/fine-light-squeak.wav' },
  { id: 'iphone-message', label: 'Стиль уведомления (iPhone)', url: '/sounds/iphone-message.wav' },
  { id: 'message-received', label: 'Сообщение получено', url: '/sounds/message-received.wav' },
  { id: 'message-tone', label: 'Сигнал сообщения', url: '/sounds/message-tone.wav' },
  { id: 'music-reminder', label: 'Музыкальное напоминание', url: '/sounds/music-reminder.wav' },
  { id: 'new-message-alt', label: 'Новое сообщение', url: '/sounds/new-message-alt.wav' },
  { id: 'nice-melodic', label: 'Приятная мелодия', url: '/sounds/nice-melodic.wav' },
  { id: 'oh-oh-icq', label: 'Oh-oh (ретро)', url: '/sounds/oh-oh-icq.wav' },
  { id: 'pyk-toon', label: 'Pyk-toon', url: '/sounds/pyk-toon.wav' },
  {
    id: 'sms-posmotri-vdrug',
    label: 'SMS — посмотри, вдруг важное',
    url: '/sounds/sms-posmotri-vdrug.mp3',
  },
]

const byId = new Map(SOUND_PRESETS.map((p) => [p.id, p] as const))

export function findPresetById(id: string): SoundPreset | undefined {
  return byId.get(id)
}

/** Нормализует значение из storage: неизвестный id → дефолт. */
export function resolveStoredPresetId(stored: string | null, defaultId: string): string {
  if (stored && findPresetById(stored)) {
    return stored
  }
  return defaultId
}

export function urlForPresetId(id: string): string | null {
  return findPresetById(id)?.url ?? null
}
