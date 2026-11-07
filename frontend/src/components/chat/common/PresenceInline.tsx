import { useEffect, useState } from 'react'
import type { UserPresence } from '../../../types/chat'
import { formatLastSeenBrief } from '../../../utils/time/formatLastSeenBrief'
import styles from '@/styles/modules/ui/PresenceInline.module.css'

const RELATIVE_TIME_TICK_MS = 30_000

function presenceDotClass(p?: UserPresence): string {
  if (p === 'online') return styles.presenceOnline
  if (p === 'away') return styles.presenceAway
  return styles.presenceOffline
}

function presenceStatusText(p: UserPresence | undefined, lastSeenAt: string | null | undefined): string {
  const pr = p ?? 'offline'
  if (pr === 'online') return 'Онлайн'
  if (pr === 'away') return 'Отошёл'
  if (lastSeenAt) return formatLastSeenBrief(lastSeenAt)
  return 'Не в сети'
}

export type PresenceInlineProps = {
  presence?: UserPresence
  /** ISO-время из API (для подписи «был в сети» при offline) */
  lastSeenAt?: string | null
}

export function PresenceInline({ presence, lastSeenAt }: PresenceInlineProps) {
  const p = presence ?? 'offline'

  const [, forceTick] = useState(0)
  useEffect(() => {
    if (p !== 'offline' || !lastSeenAt) return
    const id = setInterval(() => forceTick((n) => n + 1), RELATIVE_TIME_TICK_MS)
    return () => clearInterval(id)
  }, [p, lastSeenAt])

  const label = presenceStatusText(p, lastSeenAt)
  return (
    <span className={styles.presenceBadge} title={label}>
      <span className={`${styles.presenceDot} ${presenceDotClass(p)}`} aria-hidden />
      <span className={styles.presenceLabel}>{label}</span>
    </span>
  )
}
