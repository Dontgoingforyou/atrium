import styles from '@/styles/modules/chat/EmojiCatchGame.module.css'
import type { EmojiPongIncomingInvite } from '@/hooks/useEmojiPongOnline'

type Props = {
  invite: EmojiPongIncomingInvite
  onAccept: () => void
  onDecline: () => void
}

/** Баннер входящего приглашения в онлайн emoji-pong. */
export function EmojiPongInviteBanner({ invite, onAccept, onDecline }: Props) {
  return (
    <div className={styles.inviteBanner} role="status">
      <p className={styles.inviteText}>
        <span aria-hidden>{invite.emoji}</span>{' '}
        {invite.fromName} приглашает в Эмодзи-понг
      </p>
      <div className={styles.inviteActions}>
        <button type="button" className="btn-primary" onClick={onAccept}>
          Принять
        </button>
        <button type="button" className={styles.secondaryBtn} onClick={onDecline}>
          Отклонить
        </button>
      </div>
    </div>
  )
}
