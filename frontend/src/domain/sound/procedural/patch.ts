/**
 * Типы патча procedural-sounds (MIT, Mick Cesanek).
 * https://github.com/m1ckc3s/procedural-sounds/blob/main/lib/audio/patch.ts
 */

export type Waveform = 'sine' | 'triangle' | 'square' | 'sawtooth'

export type Frequency = number | { start: number; end: number; time?: number }

export type FM = {
  ratio: number
  depth: number
}

export type OscillatorSource = {
  type: Waveform
  frequency: Frequency
  fm?: FM
  detune?: number
}

export type NoiseColor = 'white' | 'pink' | 'brown'

export type NoiseSource = {
  type: 'noise'
  color?: NoiseColor
}

export type Source = OscillatorSource | NoiseSource

export type Envelope = {
  attack?: number
  decay: number
  sustain?: number
  release?: number
  curve?: 'ramp'
}

export type FilterEnvelope = {
  attack?: number
  peak: number
  decay: number
}

export type Filter = {
  type: BiquadFilterType
  frequency: number
  Q?: number
  resonance?: number
  envelope?: FilterEnvelope
}

export type ReverbEffect = {
  type: 'reverb'
  decay?: number
  damping?: number
  mix?: number
  preDelay?: number
  roomSize?: number
}

export type DelayEffect = {
  type: 'delay'
  delay: number
  feedback: number
  wet: number
  lowpass?: number
}

export type Effect = ReverbEffect | DelayEffect

export type Layer = {
  source: Source
  envelope?: Envelope
  gain?: number
  delay?: number
  filter?: Filter | Filter[]
  effects?: Effect[]
}

export type Patch = Layer | { layers: Layer[] }

export function layersOf(patch: Patch): Layer[] {
  return 'layers' in patch ? patch.layers : [patch]
}
