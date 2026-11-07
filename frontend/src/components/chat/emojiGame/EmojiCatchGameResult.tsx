import styles from '@/styles/modules/chat/EmojiCatchGame.module.css'

type Props = {
  emoji: string
  score: number
  shareEnabled: boolean
  sharePending: boolean
  shareError: string | null
  onShare: () => void
  onPlayAgain: () => void
  onClose: () => void
}

export function EmojiCatchGameResult({
  emoji,
  score,
  shareEnabled,
  sharePending,
  shareError,
  onShare,
  onPlayAgain,
  onClose,
}: Props) {
  return (
    <div className={styles.result}>
      <p className={styles.resultEmoji} aria-hidden>
        {emoji}
      </p>
      <p className={styles.resultScore}>Счёт: {score}</p>
      {shareError ? <p className={`text-danger ${styles.resultError}`}>{shareError}</p> : null}
      <div className={styles.resultActions}>
        <button
          type="button"
          className="btn-primary"
          disabled={sharePending}
          onClick={onPlayAgain}
        >
          Начать заново
        </button>
        {shareEnabled ? (
          <button
            type="button"
            className={styles.secondaryBtn}
            disabled={sharePending}
            onClick={onShare}
          >
            {sharePending ? 'Отправка…' : 'Отправить в чат'}
          </button>
        ) : null}
        <button type="button" className={styles.secondaryBtn} disabled={sharePending} onClick={onClose}>
          Закрыть
        </button>
      </div>
    </div>
  )
}
