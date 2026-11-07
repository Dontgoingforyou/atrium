/**
 * Product-time variation (MIT, Mick Cesanek).
 * https://github.com/m1ckc3s/procedural-sounds/blob/main/lib/audio/randomize.ts
 */

import { layersOf, type Frequency, type Layer, type Patch } from './patch'

const ABSOLUTE_CEILING_HZ = 20000
const ORIGINAL_DRAW_CHANCE = 0.25

const clamp = (x: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, x))
const vary = (rng: () => number, pct: number) => 1 + (rng() * 2 - 1) * pct

function scaleFrequency(freq: Frequency, ratio: number): Frequency {
  if (typeof freq === 'number') {
    return clamp(freq * ratio, 150, 5200)
  }
  return {
    start: clamp(freq.start * ratio, 150, 5200),
    end: clamp(freq.end * ratio, 60, 5200),
  }
}

function capUpwardDrift(patch: Patch, seed: Patch): void {
  const ceiling = ABSOLUTE_CEILING_HZ
  const seeds = layersOf(seed)
  layersOf(patch).forEach((layer, i) => {
    const src = layer.source
    const from = seeds[i]?.source
    if (src.type === 'noise' || !from || from.type === 'noise') {
      return
    }
    const cap = (mutated: number, original: number) => Math.min(mutated, Math.max(original, ceiling))
    if (typeof src.frequency === 'number') {
      if (typeof from.frequency === 'number') {
        src.frequency = cap(src.frequency, from.frequency)
      }
      return
    }
    const base =
      typeof from.frequency === 'number'
        ? { start: from.frequency, end: from.frequency }
        : from.frequency
    src.frequency = {
      ...src.frequency,
      start: cap(src.frequency.start, base.start),
      end: cap(src.frequency.end, base.end),
    }
  })
}

export function mutatePatch(source: Patch, rng: () => number = Math.random): Patch {
  const patch = structuredClone(source)
  const pitchRatio = 2 ** (((rng() * 2 - 1) * 3) / 12)
  const delayFactor = vary(rng, 0.2)

  const mutateLayer = (layer: Layer) => {
    const src = layer.source
    if (src.type !== 'noise') {
      src.frequency = scaleFrequency(src.frequency, pitchRatio)
      if (src.fm) {
        src.fm.depth = clamp(src.fm.depth * vary(rng, 0.25), 20, 450)
        src.fm.ratio = clamp(src.fm.ratio * vary(rng, 0.1), 0.4, 4)
      }
    }
    if (layer.envelope) {
      layer.envelope.decay = clamp(layer.envelope.decay * vary(rng, 0.2), 0.01, 0.7)
      if (layer.envelope.release !== undefined) {
        layer.envelope.release = clamp(layer.envelope.release * vary(rng, 0.2), 0.004, 0.3)
      }
    }
    if (layer.gain !== undefined) {
      layer.gain = clamp(layer.gain * vary(rng, 0.15), 0.03, 0.3)
    }
    if (layer.delay !== undefined) {
      layer.delay = clamp(layer.delay * delayFactor, 0, 0.25)
    }
    const filters = layer.filter ? (Array.isArray(layer.filter) ? layer.filter : [layer.filter]) : []
    for (const f of filters) {
      f.frequency = clamp(f.frequency * vary(rng, 0.15), 200, 3500)
      if (f.envelope) {
        f.envelope.peak = clamp(f.envelope.peak * vary(rng, 0.15), 1000, 8000)
      }
    }
    for (const effect of layer.effects ?? []) {
      if (effect.type !== 'reverb') {
        continue
      }
      effect.decay = clamp((effect.decay ?? 0.5) * vary(rng, 0.15), 0.3, 1)
      effect.mix = clamp((effect.mix ?? 0.3) * vary(rng, 0.2), 0.05, 0.2)
    }
  }

  for (const layer of layersOf(patch)) {
    mutateLayer(layer)
  }
  capUpwardDrift(patch, source)
  return patch
}

export function generateFromPool(
  pool: Patch[],
  rng: () => number = Math.random,
  variationRate = 1 - ORIGINAL_DRAW_CHANCE,
): Patch | null {
  if (pool.length === 0) {
    return null
  }
  const seed = pool[Math.floor(rng() * pool.length)] ?? pool[0]
  if (rng() >= variationRate) {
    return structuredClone(seed)
  }
  return mutatePatch(seed, rng)
}
