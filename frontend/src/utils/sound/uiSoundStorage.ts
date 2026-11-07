import { UI_SOUNDS_ENABLED_KEY, UI_SOUNDS_KIT_KEY } from '@/constants/uiSounds'
import { UI_SOUND_KINDS, type UiSoundKind } from '@/domain/sound/procedural/kinds'
import type { Patch } from '@/domain/sound/procedural/patch'

export type UiSoundKit = Record<UiSoundKind, Patch>

let kitCache: UiSoundKit | null = null

export function getUiSoundsEnabled(): boolean {
  try {
    return localStorage.getItem(UI_SOUNDS_ENABLED_KEY) === '1'
  } catch {
    return false
  }
}

export function persistUiSoundsEnabled(enabled: boolean): void {
  try {
    localStorage.setItem(UI_SOUNDS_ENABLED_KEY, enabled ? '1' : '0')
  } catch {
    /* quota / private mode */
  }
}

export function persistUiSoundKit(kit: UiSoundKit): void {
  kitCache = kit
  try {
    localStorage.setItem(UI_SOUNDS_KIT_KEY, JSON.stringify(kit))
  } catch {
    /* quota / private mode */
  }
}

export function clearUiSoundKitCache(): void {
  kitCache = null
}

export function getUiSoundKit(): UiSoundKit | null {
  if (kitCache) {
    return kitCache
  }
  try {
    const raw = localStorage.getItem(UI_SOUNDS_KIT_KEY)
    if (!raw) {
      return null
    }
    const parsed = JSON.parse(raw) as Partial<UiSoundKit>
    for (const kind of UI_SOUND_KINDS) {
      if (!parsed[kind]) {
        return null
      }
    }
    kitCache = parsed as UiSoundKit
    return kitCache
  } catch {
    return null
  }
}
