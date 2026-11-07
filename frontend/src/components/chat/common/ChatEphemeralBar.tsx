import styles from '@/styles/modules/chat/ChatEphemeralBar.module.css'

type Props = {
  hint: string | null
}

/** Строка над полем ввода: «Alice печатает…» / «Bob записывает голосовое…». */
export function ChatEphemeralBar({ hint }: Props) {
  return (
    <div className={styles.wrap} aria-live="polite" aria-atomic="true">
      <span className={`${styles.text} ${hint ? styles.textVisible : ''}`}>{hint ?? '\u00a0'}</span>
    </div>
  )
}
