/**
 * При взаимном «Вместе» канонический хост — меньший session_id.
 * Кто ждёт свой инвайт и видит чужой с меньшим id — принимает и становится guest.
 */
export function shouldAcceptPeerInviteWhileWaiting(
  ownSessionId: string,
  peerSessionId: string,
): boolean {
  return peerSessionId < ownSessionId
}
