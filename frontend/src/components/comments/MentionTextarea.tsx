import { useEffect, useRef, useState, type KeyboardEvent } from 'react'

import type { PortalUser } from '../../types/chat'
import { useMentionCombobox } from '../common/useMentionCombobox'
import styles from '@/styles/modules/tasks/TaskComments.module.css'

export function MentionTextarea({
  value,
  onChange,
  onMentionsChange,
  users,
  placeholder,
  rows = 3,
  autoFocus = false,
  onKeyDown,
}: {
  value: string
  onChange: (v: string) => void
  onMentionsChange: (subs: string[]) => void
  users: PortalUser[]
  placeholder?: string
  rows?: number
  autoFocus?: boolean
  onKeyDown?: (e: KeyboardEvent<HTMLTextAreaElement>) => void
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [, setMentions] = useState<string[]>([])

  useEffect(() => {
    if (!autoFocus) return
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        textareaRef.current?.focus({ preventScroll: true })
      })
    })
  }, [autoFocus])

  const { handleChange, mentionList, mentionWrapClass } = useMentionCombobox({
    textareaRef,
    value,
    onChange,
    users,
    onPick: (sub) => {
      setMentions((prev) => {
        const updated = [...new Set([...prev, sub])]
        onMentionsChange(updated)
        return updated
      })
    },
  })

  return (
    <div className={mentionWrapClass}>
      <textarea
        ref={textareaRef}
        className={`${styles.commentField} ${styles.commentTextarea}`}
        rows={rows}
        value={value}
        placeholder={placeholder}
        onChange={handleChange}
        onKeyDown={onKeyDown}
      />
      {mentionList}
    </div>
  )
}
