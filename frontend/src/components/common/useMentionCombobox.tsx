import { createPortal } from 'react-dom'
import { useLayoutEffect, useMemo, useRef, useState, type ChangeEvent, type RefObject } from 'react'

import type { PortalUser } from '../../types/chat'
import { UserAvatar } from '../ui/UserAvatar'
import { computeMentionDropdownCoords } from '@/utils/chat/mentionDropdownLayout'
import { filterMentionUsers } from '@/utils/chat/filterMentionUsers'
import { getUserDisplayLabel } from '@/utils/userLabel'
import mentionStyles from '@/styles/modules/tasks/TaskComments.module.css'

const MENTION_BEFORE_CURSOR = /@([^\n@]*)$/

/**
 * Общая логика @упоминаний для текстовых полей: поиск по курсору, портальный
 * dropdown с позиционированием и подстановкой выбранного пользователя.
 *
 * Единый источник правды для layout/portal/scroll-слушателей.
 * Используется `MentionTextarea` (комментарии) и `MentionAwareTextarea` (чат).
 *
 * @param textareaRef  реф поля ввода — для чтения позиции курсора и фокуса
 * @param value        текущий текст поля
 * @param onChange     установка нового текста (с подставленным @упоминанием)
 * @param users        список доступных пользователей
 * @param onPick       callback с sub выбранного пользователя
 * @param withAvatar   рендерить ли аватар в опциях (чат-вариант)
 */
export function useMentionCombobox({
  textareaRef,
  value,
  onChange,
  users,
  onPick,
  withAvatar = false,
}: {
  textareaRef: RefObject<HTMLTextAreaElement | null>
  value: string
  onChange: (next: string) => void
  users: PortalUser[]
  onPick: (sub: string) => void
  withAvatar?: boolean
}) {
  const [mentionSearch, setMentionSearch] = useState<string | null>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const [dropdownPos, setDropdownPos] = useState<{
    top: number
    left: number
    minWidth: number
  } | null>(null)

  function handleChange(e: ChangeEvent<HTMLTextAreaElement>) {
    const val = e.target.value
    onChange(val)
    const cursor = e.target.selectionStart ?? val.length
    const textBefore = val.slice(0, cursor)
    const m = textBefore.match(MENTION_BEFORE_CURSOR)
    setMentionSearch(m ? m[1] : null)
  }

  function handleSelectUser(user: PortalUser) {
    const cursor = textareaRef.current?.selectionStart ?? value.length
    const textBefore = value.slice(0, cursor)
    const textAfter = value.slice(cursor)
    const match = textBefore.match(MENTION_BEFORE_CURSOR)
    const displayName = getUserDisplayLabel(user)
    const replaced = match
      ? textBefore.slice(0, -match[0].length) + `@${displayName} `
      : textBefore + `@${displayName} `
    onChange(replaced + textAfter)
    onPick(user.sub)
    setMentionSearch(null)
    textareaRef.current?.focus({ preventScroll: true })
  }

  const filteredUsers = useMemo(
    () => (mentionSearch !== null ? filterMentionUsers(users, mentionSearch) : []),
    [users, mentionSearch],
  )

  const showMentionList = filteredUsers.length > 0

  useLayoutEffect(() => {
    if (!showMentionList) return
    function measureFromTextarea() {
      const el = textareaRef.current
      const listEl = listRef.current
      if (!el || !listEl) return
      setDropdownPos(computeMentionDropdownCoords(el, listEl))
    }
    measureFromTextarea()
    const scrollTargets: (EventTarget | Window)[] = [window]
    if (window.visualViewport) scrollTargets.push(window.visualViewport)
    for (let el: Element | null = textareaRef.current?.parentElement ?? null; el; el = el.parentElement) {
      scrollTargets.push(el)
    }
    for (const t of scrollTargets) t.addEventListener('scroll', measureFromTextarea, true)
    window.addEventListener('resize', measureFromTextarea)
    return () => {
      for (const t of scrollTargets) t.removeEventListener('scroll', measureFromTextarea, true)
      window.removeEventListener('resize', measureFromTextarea)
    }
  }, [showMentionList, value, mentionSearch, textareaRef])

  const mentionList =
    filteredUsers.length > 0 && typeof document !== 'undefined'
      ? createPortal(
          <ul
            ref={listRef}
            className={mentionStyles.mentionDropdownPortal}
            style={{
              top: dropdownPos ? `${dropdownPos.top}px` : '0px',
              left: dropdownPos ? `${dropdownPos.left}px` : '0px',
              minWidth: dropdownPos ? `${dropdownPos.minWidth}px` : '200px',
              visibility: dropdownPos ? 'visible' : 'hidden',
              pointerEvents: dropdownPos ? 'auto' : 'none',
            }}
          >
            {filteredUsers.map((u) => (
              <li key={u.sub}>
                <button
                  type="button"
                  className={mentionStyles.mentionOption}
                  onMouseDown={(e) => {
                    e.preventDefault()
                    handleSelectUser(u)
                  }}
                >
                  {withAvatar ? (
                    <>
                      <UserAvatar
                        label={getUserDisplayLabel(u)}
                        imageUrl={u.avatar_url}
                        focalX={u.avatar_focal_x}
                        focalY={u.avatar_focal_y}
                        size="sm"
                      />
                      {getUserDisplayLabel(u)}
                    </>
                  ) : (
                    getUserDisplayLabel(u)
                  )}
                </button>
              </li>
            ))}
          </ul>,
          document.body,
        )
      : null

  return { handleChange, mentionList, mentionWrapClass: mentionStyles.mentionWrap }
}
