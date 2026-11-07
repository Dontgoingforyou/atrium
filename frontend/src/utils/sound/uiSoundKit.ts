import { generateFromPool } from '@/domain/sound/procedural/mutate'
import { UI_SOUND_KINDS, UI_SOUND_POOLS } from '@/domain/sound/procedural/pools'
import { persistUiSoundKit, type UiSoundKit } from './uiSoundStorage'

export function rollUiSoundKit(rng: () => number = Math.random): UiSoundKit {
  const kit = {} as UiSoundKit
  for (const kind of UI_SOUND_KINDS) {
    const generated = generateFromPool(UI_SOUND_POOLS[kind], rng)
    const fallback = UI_SOUND_POOLS[kind][0]
    const patch = generated ?? (fallback ? structuredClone(fallback) : null)
    if (patch) {
      kit[kind] = patch
    }
  }
  if (UI_SOUND_KINDS.every((kind) => kit[kind])) {
    persistUiSoundKit(kit)
  }
  return kit
}
