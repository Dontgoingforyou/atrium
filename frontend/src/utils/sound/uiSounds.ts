import { UI_SOUND_SKIP_SELECTOR } from '@/constants/uiSounds'
import { playSound } from '@/domain/sound/procedural/player'
import type { UiSoundKind } from '@/domain/sound/procedural/kinds'
import { getNotificationSoundEnabled } from '@/utils/notifications/notificationSound'
import {
  clearUiSoundKitCache,
  getUiSoundKit,
  getUiSoundsEnabled,
  persistUiSoundsEnabled,
} from './uiSoundStorage'

export type { UiSoundKind }
export { getUiSoundKit, getUiSoundsEnabled }

const TAP_THROTTLE_MS = 80
const HOVER_THROTTLE_MS = 250
const SEMANTIC_KINDS: ReadonlySet<UiSoundKind> = new Set(['success', 'error'])

const lastPlayedAt: Partial<Record<UiSoundKind, number>> = {}

let pointerListenersInstalled = false
/**
 * Capture на document срабатывает раньше React onClick: tap ждём в микротаске
 * и отменяем, если в том же ходе уже сыграл error/success.
 */
let suppressDeferredTap = false

export function setUiSoundsEnabled(enabled: boolean): void {
  persistUiSoundsEnabled(enabled)
  if (!enabled) {
    clearUiSoundKitCache()
    return
  }
  void import('./uiSoundKit').then((mod) => {
    mod.rollUiSoundKit()
  })
}

function hasAudioContext(): boolean {
  if (typeof window === 'undefined') {
    return false
  }
  return Boolean(
    window.AudioContext
    ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext,
  )
}

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false
  }
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function passThrottle(kind: UiSoundKind): boolean {
  const now = Date.now()
  const gap = kind === 'hover' ? HOVER_THROTTLE_MS : TAP_THROTTLE_MS
  const prev = lastPlayedAt[kind] ?? 0
  if (now - prev < gap) {
    return false
  }
  lastPlayedAt[kind] = now
  return true
}

function canUseAudio(): boolean {
  return typeof window !== 'undefined' && getNotificationSoundEnabled() && hasAudioContext()
}

function playKind(kind: UiSoundKind): void {
  const patch = getUiSoundKit()?.[kind]
  if (!patch) {
    return
  }
  playSound(patch)
}

export function playUiSound(kind: UiSoundKind): void {
  try {
    if (!canUseAudio() || !getUiSoundsEnabled()) {
      return
    }
    if (kind === 'hover' && prefersReducedMotion()) {
      return
    }
    if (SEMANTIC_KINDS.has(kind)) {
      suppressDeferredTap = true
    }
    if (!passThrottle(kind)) {
      return
    }
    playKind(kind)
  } catch {
    /* Web Audio / автовоспроизведение */
  }
}

export function previewUiSound(kind: UiSoundKind): void {
  try {
    if (!canUseAudio()) {
      return
    }
    const existing = getUiSoundKit()?.[kind]
    if (existing) {
      playSound(existing)
      return
    }
    void import('./uiSoundKit').then((mod) => {
      const patch = mod.rollUiSoundKit()[kind]
      if (patch) {
        playSound(patch)
      }
    })
  } catch {
    /* Web Audio / автовоспроизведение */
  }
}

function isUiSoundControl(el: EventTarget | null): HTMLElement | null {
  if (!(el instanceof Element)) {
    return null
  }
  if (el.closest(UI_SOUND_SKIP_SELECTOR)) {
    return null
  }
  const target = el.closest('button, [role="button"], input[type="submit"], input[type="reset"]')
  if (!(target instanceof HTMLElement)) {
    return null
  }
  if (target.hasAttribute('disabled') || target.getAttribute('aria-disabled') === 'true') {
    return null
  }
  return target
}

function onPointerClick(ev: Event): void {
  if (!isUiSoundControl(ev.target)) {
    return
  }
  suppressDeferredTap = false
  queueMicrotask(() => {
    if (suppressDeferredTap) {
      suppressDeferredTap = false
      return
    }
    playUiSound('tap')
  })
}

/** Один capture-listener на документ; вызывать из корня layout. Только клик, не hover. */
export function installUiSoundPointerListeners(): void {
  if (typeof document === 'undefined' || pointerListenersInstalled) {
    return
  }
  pointerListenersInstalled = true
  document.addEventListener('click', onPointerClick, true)
}
