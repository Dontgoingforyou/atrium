import { BUILDIN_TOGGLE_BODY_EASE, buildinToggleBodyAnimMs } from './buildinToggle'

const animGen = new WeakMap<HTMLElement, number>()

export function resolveToggleSlotAnimHeights(
  fromPx: number,
  naturalPx: number,
  isOpen: boolean,
): { from: number; to: number } {
  return { from: fromPx, to: isOpen ? naturalPx : 0 }
}

export function shouldSkipToggleSlotAnim(fromPx: number, toPx: number, durationMs: number): boolean {
  return durationMs <= 0 || Math.abs(fromPx - toPx) < 0.5
}

export function applyToggleSlotHeightSettled(slot: HTMLElement, isOpen: boolean): void {
  slot.style.transition = ''
  slot.style.height = isOpen ? '' : '0px'
  slot.style.overflow = isOpen ? '' : 'hidden'
}

export function measureToggleSlotNaturalHeight(slot: HTMLElement): number {
  const inner = slot.firstElementChild as HTMLElement | null
  const innerNative = inner ? Math.max(inner.scrollHeight, inner.offsetHeight) : 0
  const prevHeight = slot.style.height
  const prevOverflow = slot.style.overflow
  const prevTransition = slot.style.transition
  slot.style.transition = 'none'
  slot.style.overflow = 'visible'
  slot.style.height = 'auto'
  const slotNative = Math.max(slot.scrollHeight, slot.offsetHeight)
  slot.style.height = prevHeight
  slot.style.overflow = prevOverflow
  slot.style.transition = prevTransition
  return Math.max(slotNative, innerNative)
}

function bumpToggleSlotAnimGen(slot: HTMLElement): number {
  const gen = (animGen.get(slot) ?? 0) + 1
  animGen.set(slot, gen)
  if (typeof slot.getAnimations === 'function') {
    slot.getAnimations().forEach((anim) => anim.cancel())
  }
  return gen
}

export function settleBuildinToggleSlotHeight(slot: HTMLElement, isOpen: boolean): void {
  bumpToggleSlotAnimGen(slot)
  applyToggleSlotHeightSettled(slot, isOpen)
}

export function playBuildinToggleSlotHeight(slot: HTMLElement, isOpen: boolean): void {
  const gen = bumpToggleSlotAnimGen(slot)
  const duration = buildinToggleBodyAnimMs()
  const from = slot.getBoundingClientRect().height
  const natural = measureToggleSlotNaturalHeight(slot)
  const { to } = resolveToggleSlotAnimHeights(from, natural, isOpen)
  slot.style.overflow = 'hidden'
  if (shouldSkipToggleSlotAnim(from, to, duration) || typeof slot.animate !== 'function') {
    applyToggleSlotHeightSettled(slot, isOpen)
    return
  }
  slot.style.height = `${from}px`
  const anim = slot.animate([{ height: `${from}px` }, { height: `${to}px` }], {
    duration,
    easing: BUILDIN_TOGGLE_BODY_EASE,
    fill: 'forwards',
  })
  void anim.finished
    .then(() => {
      if (animGen.get(slot) !== gen) return
      applyToggleSlotHeightSettled(slot, isOpen)
      anim.cancel()
    })
    .catch(() => {
      if (animGen.get(slot) !== gen) return
      applyToggleSlotHeightSettled(slot, isOpen)
    })
}
