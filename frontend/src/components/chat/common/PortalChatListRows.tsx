import { useMemo, useRef } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'

import type { Chat, UserPresence } from '../../../types/chat'
import { canDeleteEntireChat } from '@/utils/chat/canDeleteEntireChat'
import { chatDisplayName } from '@/utils/chat/chatDisplay'
import { getDmChatNotificationSoundEnabled } from '@/utils/chat/dmChatNotificationSoundSettings'
import { dmPeerSub } from '@/utils/chat/dmPeerSub'
import { resolveChatAvatarImageUrl } from '@/utils/chat/resolveChatAvatarImageUrl'
import { TOUR_DEMO_CHAT_TITLE } from '../../../onboarding/ensureTourDemoChat'
import { IconVolumeOff, IconVolumeOn } from '../../icons/VolumeNotificationIcons'
import { UserAvatar } from '../../ui/UserAvatar'
import { PresenceInline } from './PresenceInline'

export type PortalChatListRowsClasses = {
  list: string
  listEmpty: string
  rowOuter: string
  rowOuterActive: string
  rowButton: string
  avatar: string
  chatNameBlock: string
  chatName: string
  chatPresenceLine: string
  chatMeta: string
  unreadPill: string
  soundCell?: string
  soundBtn: string
}

type Props = {
  sortedChats: Chat[]
  currentUserSub: string | null
  userMap: Record<string, string>
  userAvatarBySub: Record<string, string | undefined>
  presenceBySub: Record<string, UserPresence>
  lastSeenBySub: Record<string, string | null>
  avatarFocalBySub: Record<string, { x: number; y: number } | undefined>
  dmNotifTick: number
  activeChatId?: string | null
  classes: PortalChatListRowsClasses
  onChatOpen: (chatId: string) => void
  onDmSoundClick: (e: React.MouseEvent, chatId: string) => void
  onChatRowContextMenu?: (e: React.MouseEvent, chat: Chat) => void
}

export function PortalChatListRows({
  sortedChats,
  currentUserSub,
  userMap,
  userAvatarBySub,
  presenceBySub,
  lastSeenBySub,
  avatarFocalBySub,
  dmNotifTick,
  activeChatId = null,
  classes: c,
  onChatOpen,
  onDmSoundClick,
  onChatRowContextMenu,
}: Props) {
  const soundTitleOn = 'Выключить звук уведомлений для этого чата'
  const soundTitleOff = 'Включить звук уведомлений для этого чата'
  const soundAriaOn = 'Звук уведомлений для чата включён'
  const soundAriaOff = 'Звук уведомлений для чата выключен'

  // Читаем все настройки звука один раз за рендер
  const soundSettingsMap = useMemo(() => {
    const m = new Map<string, boolean>()
    for (const chat of sortedChats) {
      m.set(chat.id, getDmChatNotificationSoundEnabled(chat.id))
    }
    return m
    // dmNotifTick — внешний счётчик, сигнализирующий об изменении настроек звука.
    // getDmChatNotificationSoundEnabled — стабильный модульный импорт, в deps намеренно не включён.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortedChats, dmNotifTick])

  /** Якорь онбординга — учебный чат (если есть), иначе первая строка. */
  const tourRowChatId = useMemo(() => {
    const demo = sortedChats.find((ch) => !ch.is_direct && ch.title === TOUR_DEMO_CHAT_TITLE)
    return demo?.id ?? sortedChats[0]?.id ?? null
  }, [sortedChats])

  const scrollRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: sortedChats.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 58,
    overscan: 5,
  })

  const virtualItems = virtualizer.getVirtualItems()
  const totalSize = virtualizer.getTotalSize()

  return (
    <div className={c.list} data-dm-sound-tick={dmNotifTick} ref={scrollRef}>
      {sortedChats.length === 0 ? (
        <p className={c.listEmpty}>Нет чатов</p>
      ) : (
        <div style={{ height: totalSize, position: 'relative' }}>
          {virtualItems.map((vItem) => {
            const chat = sortedChats[vItem.index]!
            const name = chatDisplayName(chat, currentUserSub, userMap)
            const peer = dmPeerSub(chat, currentUserSub)
            const peerPresence = peer ? presenceBySub[peer] : undefined
            const peerLastSeen = peer ? lastSeenBySub[peer] : null
            const peerFocal = peer ? avatarFocalBySub[peer] : undefined
            const unread = chat.unread_count ?? 0
            const isActive = activeChatId != null && chat.id === activeChatId
            const soundOn = soundSettingsMap.get(chat.id) ?? false
            const rowClass = [c.rowOuter, isActive && c.rowOuterActive ? c.rowOuterActive : '']
              .filter(Boolean)
              .join(' ')

            const soundBtn = (
              <button
                type="button"
                className={c.soundBtn}
                onClick={(e) => onDmSoundClick(e, chat.id)}
                title={soundOn ? soundTitleOn : soundTitleOff}
                aria-pressed={soundOn}
                aria-label={soundOn ? soundAriaOn : soundAriaOff}
              >
                {soundOn ? <IconVolumeOn /> : <IconVolumeOff />}
              </button>
            )

            return (
              <div
                key={chat.id}
                data-index={vItem.index}
                ref={virtualizer.measureElement}
                style={{ position: 'absolute', top: vItem.start, left: 0, right: 0 }}
                className={rowClass}
                {...(chat.id === tourRowChatId
                  ? {
                      'data-tour': 'chats-row',
                      'data-tour-route': `/chats?chat=${encodeURIComponent(chat.id)}`,
                    }
                  : {})}
                onContextMenu={(ev) => {
                  if (!canDeleteEntireChat(chat, currentUserSub)) return
                  ev.preventDefault()
                  onChatRowContextMenu?.(ev, chat)
                }}
              >
                <button type="button" className={c.rowButton} onClick={() => onChatOpen(chat.id)}>
                  <UserAvatar
                    size={34}
                    label={name}
                    imageUrl={resolveChatAvatarImageUrl({
                      isDirect: chat.is_direct,
                      peerSub: peer,
                      userAvatarBySub,
                      chatAvatarUrl: chat.avatar_url,
                    })}
                    focalX={
                      chat.is_direct && peer ? peerFocal?.x : (chat.avatar_focal_x ?? undefined)
                    }
                    focalY={
                      chat.is_direct && peer ? peerFocal?.y : (chat.avatar_focal_y ?? undefined)
                    }
                    className={c.avatar}
                  />
                  <span className={c.chatNameBlock}>
                    {chat.is_direct && peer ? (
                      <>
                        <span className={c.chatName}>{name}</span>
                        <span className={c.chatPresenceLine}>
                          <PresenceInline presence={peerPresence} lastSeenAt={peerLastSeen} />
                        </span>
                      </>
                    ) : (
                      <>
                        <span className={c.chatName}>{name}</span>
                        {!chat.is_direct ? <span className={c.chatMeta}>группа</span> : null}
                      </>
                    )}
                  </span>
                  {unread > 0 && (
                    <span className={c.unreadPill}>{unread > 99 ? '99+' : unread}</span>
                  )}
                </button>
                {c.soundCell ? <div className={c.soundCell}>{soundBtn}</div> : soundBtn}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
