import type { ChatMessageReaction } from '../../../types/chat'
import styles from '@/styles/modules/chat/ChatMessageListOverlays.module.css'

type Props = {
  reactions: ChatMessageReaction[]
  busy: boolean
  onOpenReactors: (emoji: string, anchorRect: DOMRect) => void
}

export function ReactionBar({ reactions, busy, onOpenReactors }: Props) {
  if (reactions.length === 0) return null
  return (
    <div className={styles.reactionsRow}>
      {reactions.map((r) => (
        <button
          key={r.emoji}
          type="button"
          className={`${styles.reactionChip} ${r.reacted_by_me ? styles.reactionChipMine : ''}`}
          title="Кто поставил"
          aria-label={`Реакция ${r.emoji}: ${r.count}`}
          disabled={busy}
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect()
            onOpenReactors(r.emoji, rect)
          }}
        >
          <span>{r.emoji}</span>
          <span className={styles.reactionCount}>{r.count}</span>
        </button>
      ))}
    </div>
  )
}
