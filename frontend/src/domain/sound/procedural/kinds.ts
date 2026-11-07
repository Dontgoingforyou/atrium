export const UI_SOUND_KINDS = ['tap', 'hover', 'success', 'error', 'warning', 'notification'] as const

export type UiSoundKind = (typeof UI_SOUND_KINDS)[number]
