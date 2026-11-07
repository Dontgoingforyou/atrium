export type EphemeralPeer = {
  userSub: string
  displayName: string
  kind: 'typing' | 'voice_recording'
}

/** Короткая фраза для группы: «Alice печатает…», «Alice и Bob записывают голосовое…». */
export function formatEphemeralHint(peers: EphemeralPeer[]): string | null {
  if (peers.length === 0) return null

  const typing = peers.filter((p) => p.kind === 'typing')
  const voice = peers.filter((p) => p.kind === 'voice_recording')

  const parts: string[] = []
  if (typing.length > 0) {
    parts.push(formatGroup(typing, 'печатает', 'печатают'))
  }
  if (voice.length > 0) {
    parts.push(formatGroup(voice, 'записывает голосовое', 'записывают голосовое'))
  }
  return parts.join(' · ')
}

function formatGroup(peers: EphemeralPeer[], oneVerb: string, manyVerb: string): string {
  const names = peers.map((p) => p.displayName || p.userSub.slice(0, 8))
  if (names.length === 1) return `${names[0]} ${oneVerb}…`
  if (names.length === 2) return `${names[0]} и ${names[1]} ${manyVerb}…`
  return `${names[0]}, ${names[1]} и ещё ${names.length - 2} ${manyVerb}…`
}

/** Подпись для одной строки в ленте (без многоточия — его рисует UI). */
export function ephemeralPeerLabel(peer: EphemeralPeer): string {
  const name = peer.displayName || peer.userSub.slice(0, 8)
  if (peer.kind === 'typing') return `${name} печатает`
  return `${name} записывает голосовое`
}

export function peersToEphemeralList(
  map: Map<string, { displayName: string; typing: boolean; voice: boolean }>,
): EphemeralPeer[] {
  const out: EphemeralPeer[] = []
  for (const [userSub, p] of map) {
    if (p.typing) out.push({ userSub, displayName: p.displayName, kind: 'typing' })
    if (p.voice) out.push({ userSub, displayName: p.displayName, kind: 'voice_recording' })
  }
  return out
}
