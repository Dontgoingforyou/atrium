import { UserAvatar } from '../../ui/UserAvatar'
import { formatEmojiGameScoreDigits } from '@/utils/chat/emojiOnlyMessage'
import styles from '@/styles/modules/chat/EmojiCatchGame.module.css'

export type EmojiPongPlayer = {
  label: string
  imageUrl?: string | null
  /** Лучший счёт из истории чата. */
  bestScore: number
}

type Props = {
  /** Собеседник (слева). */
  peer: EmojiPongPlayer
  /** Текущий пользователь (справа). */
  me: EmojiPongPlayer
  /** Счёт текущего раунда (отображается справа вместе с best). */
  sessionScore: number
}

export function EmojiCatchScoreboard({ peer, me, sessionScore }: Props) {
  const peerScore = peer.bestScore
  const myScore = Math.max(me.bestScore, sessionScore)
  const peerLeads = peerScore > myScore
  const iLead = myScore > peerScore

  return (
    <div className={styles.scoreboard} aria-label="Счёт игроков">
      <span className={styles.scoreboardNum}>{formatEmojiGameScoreDigits(peerScore)}</span>
      <div className={styles.scoreboardAvatars}>
        <div className={`${styles.scoreboardAvatarWrap} ${styles.scoreboardAvatarPeer}`}>
          {peerLeads ? (
            <span className={styles.scoreboardCrown} aria-hidden>
              👑
            </span>
          ) : null}
          <UserAvatar
            className={styles.scoreboardAvatar}
            label={peer.label}
            imageUrl={peer.imageUrl}
            size={36}
            loading="eager"
          />
        </div>
        <div className={`${styles.scoreboardAvatarWrap} ${styles.scoreboardAvatarMe}`}>
          {iLead ? (
            <span className={styles.scoreboardCrown} aria-hidden>
              👑
            </span>
          ) : null}
          <UserAvatar
            className={styles.scoreboardAvatar}
            label={me.label}
            imageUrl={me.imageUrl}
            size={36}
            loading="eager"
          />
        </div>
      </div>
      <span className={styles.scoreboardNum}>{formatEmojiGameScoreDigits(myScore)}</span>
    </div>
  )
}
