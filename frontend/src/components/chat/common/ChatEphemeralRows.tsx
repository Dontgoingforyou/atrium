import { UserAvatar } from '../../ui/UserAvatar'
import type { EphemeralPeer } from '@/utils/chat/chatEphemeral'
import { ephemeralPeerLabel } from '@/utils/chat/chatEphemeral'
import styles from '@/styles/modules/chat/ChatEphemeralRows.module.css'

type Props = {
  peers: EphemeralPeer[]
  userAvatarBySub?: Record<string, string | undefined>
}

/** Строки «печатает / записывает голос» в ленте (без даты — только текст). */
export function ChatEphemeralRows({ peers, userAvatarBySub = {} }: Props) {
  if (peers.length === 0) return null

  return (
    <div className={styles.wrap} aria-live="polite" aria-atomic="false">
      {peers.map((peer) => (
        <div key={`${peer.userSub}-${peer.kind}`} className={styles.row}>
          <UserAvatar
            size={32}
            label={peer.displayName}
            imageUrl={userAvatarBySub[peer.userSub]}
            className={styles.avatar}
          />
          <div className={styles.bubble}>
            {ephemeralPeerLabel(peer)}
            <span className={styles.dots} aria-hidden>
              …
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}
