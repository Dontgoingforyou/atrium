import type { MessageReceipt } from '../../../types/chat'
import styles from '@/styles/modules/chat/ChatMessageListLayout.module.css'

type Props = {
  receipt: MessageReceipt
  onClick?: (e: React.MouseEvent) => void
}

export function ChatMessageReceiptIcon({ receipt, onClick }: Props) {
  const label = 'Нажмите чтобы посмотреть кто прочитал'
  return (
    <button
      type="button"
      className={[
        styles.receiptBtn,
        styles.receipt,
        receipt === 'read' ? styles.receiptReadMark : '',
      ].filter(Boolean).join(' ')}
      title={label}
      aria-label={label}
      onClick={onClick}
    >
      {receipt === 'read' ? '✓✓' : '✓'}
    </button>
  )
}
