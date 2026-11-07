// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { UI_SOUND_SKIP_VALUE, UI_SOUNDS_ENABLED_KEY } from '@/constants/uiSounds'
import { UI_SOUND_KINDS } from '@/domain/sound/procedural/kinds'
import { layersOf, type Patch } from '@/domain/sound/procedural/patch'
import { clearUiSoundKitCache } from '@/utils/sound/uiSoundStorage'

const playSound = vi.fn()
const getNotificationSoundEnabled = vi.fn(() => true)

vi.mock('@/domain/sound/procedural/player', () => ({
  playSound: (...args: unknown[]) => playSound(...args),
}))

vi.mock('@/utils/notifications/notificationSound', () => ({
  getNotificationSoundEnabled: () => getNotificationSoundEnabled(),
}))

function assertPlayablePatch(value: unknown): asserts value is Patch {
  expect(value).toEqual(expect.any(Object))
  const layers = layersOf(value as Patch)
  expect(layers.length).toBeGreaterThan(0)
  expect(layers[0]?.source).toEqual(expect.objectContaining({ type: expect.any(String) }))
}

describe('playUiSound / storage', () => {
  let clockMs = 1_700_000_000_000

  beforeEach(() => {
    clockMs += 10_000
    vi.useFakeTimers()
    vi.setSystemTime(clockMs)
    localStorage.clear()
    clearUiSoundKitCache()
    playSound.mockReset()
    getNotificationSoundEnabled.mockReset()
    getNotificationSoundEnabled.mockReturnValue(true)
    vi.stubGlobal(
      'AudioContext',
      class {
        state = 'running'
        currentTime = 0
        destination = {}
        createGain() {
          return { gain: { setValueAtTime() {}, exponentialRampToValueAtTime() {} }, connect() {} }
        }
        createOscillator() {
          return {
            type: 'sine',
            frequency: { setValueAtTime() {}, exponentialRampToValueAtTime() {} },
            connect() {},
            start() {},
            stop() {},
          }
        }
        resume() {
          return Promise.resolve()
        }
      },
    )
  })

  afterEach(() => {
    document.body.replaceChildren()
    localStorage.clear()
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('по умолчанию выключен', async () => {
    const { getUiSoundsEnabled } = await import('@/utils/sound/uiSounds')
    expect(getUiSoundsEnabled()).toBe(false)
  })

  it('при выкл. не вызывает плеер', async () => {
    const { playUiSound } = await import('@/utils/sound/uiSounds')
    expect(() => playUiSound('tap')).not.toThrow()
    expect(playSound).not.toHaveBeenCalled()
  })

  it('при глобальном mute колокольчика не вызывает плеер', async () => {
    localStorage.setItem(UI_SOUNDS_ENABLED_KEY, '1')
    getNotificationSoundEnabled.mockReturnValue(false)
    const { playUiSound } = await import('@/utils/sound/uiSounds')
    playUiSound('success')
    expect(playSound).not.toHaveBeenCalled()
  })

  it('без AudioContext не вызывает плеер и не бросает', async () => {
    localStorage.setItem(UI_SOUNDS_ENABLED_KEY, '1')
    vi.stubGlobal('AudioContext', undefined)
    vi.stubGlobal('webkitAudioContext', undefined)
    const { playUiSound } = await import('@/utils/sound/uiSounds')
    expect(() => playUiSound('tap')).not.toThrow()
    expect(playSound).not.toHaveBeenCalled()
  })

  it('оба гейта открыты — плеер с патчем kind', async () => {
    const { rollUiSoundKit } = await import('@/utils/sound/uiSoundKit')
    const { playUiSound } = await import('@/utils/sound/uiSounds')
    localStorage.setItem(UI_SOUNDS_ENABLED_KEY, '1')
    rollUiSoundKit(() => 0)
    playUiSound('success')
    expect(playSound).toHaveBeenCalledTimes(1)
    assertPlayablePatch(playSound.mock.calls[0]?.[0])
  })

  it('preview играет при выкл. тумблере, playUiSound — нет', async () => {
    const { rollUiSoundKit } = await import('@/utils/sound/uiSoundKit')
    const { playUiSound, previewUiSound } = await import('@/utils/sound/uiSounds')
    rollUiSoundKit(() => 0)
    previewUiSound('success')
    expect(playSound).toHaveBeenCalledTimes(1)
    assertPlayablePatch(playSound.mock.calls[0]?.[0])
    playSound.mockClear()
    playUiSound('success')
    expect(playSound).not.toHaveBeenCalled()
  })

  it('каждое включение собирает другой набор из пула', async () => {
    const { rollUiSoundKit } = await import('@/utils/sound/uiSoundKit')
    const kitA = rollUiSoundKit(() => 0)
    const kitB = rollUiSoundKit(() => 0.99)
    for (const kind of UI_SOUND_KINDS) {
      assertPlayablePatch(kitA[kind])
      assertPlayablePatch(kitB[kind])
    }
    expect(kitA.tap).not.toEqual(kitB.tap)
    expect(kitA.success).not.toEqual(kitB.success)
  })

  it('клик на кнопке играет tap, pointerover и skip — нет', async () => {
    const { rollUiSoundKit } = await import('@/utils/sound/uiSoundKit')
    const { installUiSoundPointerListeners } = await import('@/utils/sound/uiSounds')
    localStorage.setItem(UI_SOUNDS_ENABLED_KEY, '1')
    rollUiSoundKit(() => 0)
    installUiSoundPointerListeners()

    const button = document.createElement('button')
    const inner = document.createElement('span')
    button.appendChild(inner)
    document.body.appendChild(button)

    inner.dispatchEvent(new MouseEvent('pointerover', { bubbles: true, relatedTarget: null }))
    expect(playSound).not.toHaveBeenCalled()

    const skipped = document.createElement('div')
    skipped.dataset.uiSound = UI_SOUND_SKIP_VALUE
    const skippedBtn = document.createElement('button')
    skipped.appendChild(skippedBtn)
    document.body.appendChild(skipped)
    skippedBtn.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    expect(playSound).not.toHaveBeenCalled()

    button.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await Promise.resolve()
    expect(playSound).toHaveBeenCalledTimes(1)
    assertPlayablePatch(playSound.mock.calls[0]?.[0])
  })

  it('клик + error/success в том же ходе — один смысловой патч, не tap', async () => {
    const { rollUiSoundKit } = await import('@/utils/sound/uiSoundKit')
    const { installUiSoundPointerListeners, playUiSound } = await import('@/utils/sound/uiSounds')
    localStorage.setItem(UI_SOUNDS_ENABLED_KEY, '1')
    const kit = rollUiSoundKit(() => 0)
    installUiSoundPointerListeners()

    const button = document.createElement('button')
    button.addEventListener('click', () => playUiSound('error'))
    document.body.appendChild(button)
    button.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await Promise.resolve()

    expect(playSound).toHaveBeenCalledTimes(1)
    expect(playSound.mock.calls[0]?.[0]).toEqual(kit.error)

    playSound.mockClear()
    const other = document.createElement('button')
    other.addEventListener('click', () => playUiSound('success'))
    document.body.appendChild(other)
    other.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await Promise.resolve()
    expect(playSound).toHaveBeenCalledTimes(1)
    expect(playSound.mock.calls[0]?.[0]).toEqual(kit.success)
  })
})
