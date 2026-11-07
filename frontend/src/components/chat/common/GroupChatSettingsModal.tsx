import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'

import { isApiConflictError } from '../../../api/apiConflict'
import { PORTAL_CHATS_ALL_QUERY_KEY } from '../../../api/queryKeys'
import {
  deleteGroupChatAvatar,
  inviteChatMember,
  patchChatTitle,
  postGroupChatAvatar,
  removeChatMember,
} from '../../../api/chat/chatApi'
import type { Chat, PortalUser, UserPresence } from '../../../types/chat'
import { userFacingMessageFromUnknown } from '../../../utils/apiUserMessage'
import { useNotifyToast } from '../../../hooks/useNotifyToast'
import { useBodyScrollLock } from '../../../hooks/useBodyScrollLock'
import { useFocusTrap } from '../../../hooks/useFocusTrap'
import { AvatarFocalPickModal } from '../../layout/AvatarFocalPickModal'
import { ConfirmDialog } from '../../ui/ConfirmDialog'
import { UserAvatar } from '../../ui/UserAvatar'
import { PresenceInline } from './PresenceInline'
import styles from '@/styles/modules/chat/GroupChatSettingsModal.module.css'

type Props = {
  open: boolean
  onClose: () => void
  chat: Chat
  currentUserSub: string
  portalUsers: PortalUser[]
  userMap: Record<string, string>
  presenceBySub: Record<string, UserPresence>
  /** После «Покинуть чат» текущим пользователем */
  onAfterSelfLeave?: () => void
}

export function GroupChatSettingsModal({
  open,
  onClose,
  chat,
  currentUserSub,
  portalUsers,
  userMap,
  presenceBySub,
  onAfterSelfLeave,
}: Props) {
  const qc = useQueryClient()
  const notify = useNotifyToast()
  const [inviteSearch, setInviteSearch] = useState('')
  const [settingsTitleDraft, setSettingsTitleDraft] = useState(() => chat.title ?? '')
  const [confirmDialog, setConfirmDialog] = useState<{
    title: string
    message: string
    destructive?: boolean
    onConfirm: () => void
  } | null>(null)
  const avatarFileRef = useRef<HTMLInputElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)
  const titleId = useId()
  const [avatarPickFile, setAvatarPickFile] = useState<File | null>(null)
  const nestedOpen = confirmDialog !== null || avatarPickFile !== null

  useFocusTrap(dialogRef, open && !nestedOpen)
  useBodyScrollLock(open)

  useEffect(() => {
    if (!open || nestedOpen) return
    closeRef.current?.focus()
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, nestedOpen, onClose])

  const lastSeenBySub = useMemo(() => {
    const m: Record<string, string | null> = {}
    for (const u of portalUsers) {
      m[u.sub] = u.last_seen_at ?? null
    }
    return m
  }, [portalUsers])

  const filteredInviteUsers = useMemo(() => {
    const memberSet = new Set(chat.member_subs)
    const q = inviteSearch.trim().toLowerCase()
    return portalUsers.filter(
      (u) =>
        !memberSet.has(u.sub) &&
        u.sub !== currentUserSub &&
        (!q ||
          (u.display_name ?? '').toLowerCase().includes(q) ||
          (u.email ?? '').toLowerCase().includes(q) ||
          (u.username ?? '').toLowerCase().includes(q)),
    )
  }, [portalUsers, chat.member_subs, currentUserSub, inviteSearch])

  const patchTitleMutation = useMutation({
    mutationFn: (title: string) => patchChatTitle(chat.id, title, chat.version),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: PORTAL_CHATS_ALL_QUERY_KEY })
      onClose()
    },
    onError: (e: unknown) => {
      notify(userFacingMessageFromUnknown(e))
      if (isApiConflictError(e)) {
        void qc.invalidateQueries({ queryKey: PORTAL_CHATS_ALL_QUERY_KEY })
      }
    },
  })

  const inviteMutation = useMutation({
    mutationFn: (userSub: string) => inviteChatMember(chat.id, userSub),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: PORTAL_CHATS_ALL_QUERY_KEY })
      setInviteSearch('')
    },
    onError: (e: unknown) => notify(userFacingMessageFromUnknown(e)),
  })

  const removeMemberMutation = useMutation({
    mutationFn: (userSub: string) => removeChatMember(chat.id, userSub),
    onSuccess: (_, userSub) => {
      void qc.invalidateQueries({ queryKey: PORTAL_CHATS_ALL_QUERY_KEY })
      if (userSub === currentUserSub) {
        onClose()
        onAfterSelfLeave?.()
      }
    },
    onError: (e: unknown) => notify(userFacingMessageFromUnknown(e), { silent: true }),
  })

  const uploadAvatarMutation = useMutation({
    mutationFn: ({ file, focal }: { file: File; focal?: { x: number; y: number } }) =>
      postGroupChatAvatar(chat.id, file, focal),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: PORTAL_CHATS_ALL_QUERY_KEY })
    },
    onError: (e: unknown) => notify(userFacingMessageFromUnknown(e)),
  })

  const deleteAvatarMutation = useMutation({
    mutationFn: () => deleteGroupChatAvatar(chat.id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: PORTAL_CHATS_ALL_QUERY_KEY })
    },
    onError: (e: unknown) => notify(userFacingMessageFromUnknown(e)),
  })

  if (!open) return null

  const groupLabel = chat.title?.trim() || 'Группа'

  return (
    <>
      <div
        className={styles.modalOverlay}
        role="presentation"
        onClick={() => onClose()}
      >
        <div
          ref={dialogRef}
          className={styles.modal}
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          onClick={(e) => e.stopPropagation()}
        >
          <h2 id={titleId} className={styles.modalTitle}>
            Настройки чата
          </h2>
          {chat.created_by_sub === currentUserSub ? (
            <label className={styles.groupLabel}>
              Название
              <input
                className={styles.groupTitleInput}
                value={settingsTitleDraft}
                onChange={(e) => setSettingsTitleDraft(e.target.value)}
              />
              <button
                type="button"
                className={styles.modalPrimaryBtn}
                disabled={patchTitleMutation.isPending || settingsTitleDraft.trim().length === 0}
                onClick={() => patchTitleMutation.mutate(settingsTitleDraft.trim())}
              >
                Сохранить название
              </button>
            </label>
          ) : null}

          {chat.created_by_sub === currentUserSub ? (
            <div className={styles.avatarSection}>
              <h3 className={styles.modalSection}>Аватар чата</h3>
              <input
                ref={avatarFileRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif"
                className={styles.avatarFileInput}
                aria-hidden
                tabIndex={-1}
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  e.target.value = ''
                  if (f) setAvatarPickFile(f)
                }}
              />
              <div className={styles.avatarRow}>
                <UserAvatar
                  size="lg"
                  label={groupLabel}
                  imageUrl={chat.avatar_url ?? undefined}
                  focalX={chat.avatar_focal_x ?? undefined}
                  focalY={chat.avatar_focal_y ?? undefined}
                  onClick={() => avatarFileRef.current?.click()}
                  title="Нажмите, чтобы сменить аватар"
                />
                <div className={styles.avatarActions}>
                  <button
                    type="button"
                    className={styles.modalSecondaryBtn}
                    disabled={uploadAvatarMutation.isPending}
                    onClick={() => avatarFileRef.current?.click()}
                  >
                    Выбрать файл…
                  </button>
                  {chat.avatar_url ? (
                    <button
                      type="button"
                      className={styles.modalDangerBtn}
                      disabled={deleteAvatarMutation.isPending}
                      onClick={() => deleteAvatarMutation.mutate()}
                    >
                      Удалить аватар
                    </button>
                  ) : null}
                </div>
              </div>
            </div>
          ) : null}

          <h3 className={styles.modalSection}>Участники</h3>
          <ul className={styles.memberList}>
            {chat.member_subs.map((sub) => (
              <li key={sub} className={styles.memberRow}>
                <span className={styles.memberNameCell}>
                  <span>{userMap[sub] ?? sub}</span>
                  <PresenceInline presence={presenceBySub[sub]} lastSeenAt={lastSeenBySub[sub]} />
                </span>
                {sub === chat.created_by_sub ? (
                  <span className={styles.badgeCreator}>создатель</span>
                ) : null}
                {chat.created_by_sub === currentUserSub && sub !== chat.created_by_sub ? (
                  <button
                    type="button"
                    className={styles.modalDangerBtn}
                    disabled={removeMemberMutation.isPending}
                    onClick={() =>
                      setConfirmDialog({
                        title: 'Исключить участника',
                        message: `Исключить ${userMap[sub] ?? sub} из чата?`,
                        destructive: true,
                        onConfirm: () => {
                          setConfirmDialog(null)
                          removeMemberMutation.mutate(sub)
                        },
                      })
                    }
                  >
                    Исключить
                  </button>
                ) : null}
                {sub === currentUserSub && sub !== chat.created_by_sub ? (
                  <button
                    type="button"
                    className={styles.modalDangerBtn}
                    disabled={removeMemberMutation.isPending}
                    onClick={() =>
                      setConfirmDialog({
                        title: 'Покинуть чат',
                        message: 'Вы уверены, что хотите покинуть этот чат?',
                        destructive: true,
                        onConfirm: () => {
                          setConfirmDialog(null)
                          removeMemberMutation.mutate(sub)
                        },
                      })
                    }
                  >
                    Покинуть чат
                  </button>
                ) : null}
              </li>
            ))}
          </ul>

          {chat.member_subs.includes(currentUserSub) ? (
            <>
              <h3 className={styles.modalSection}>Пригласить</h3>
              <input
                type="search"
                className={styles.groupTitleInput}
                placeholder="Поиск пользователя…"
                aria-label="Поиск пользователя для приглашения"
                value={inviteSearch}
                onChange={(e) => setInviteSearch(e.target.value)}
              />
              <ul className={styles.inviteList}>
                {filteredInviteUsers.map((u) => (
                  <li key={u.sub}>
                    <button
                      type="button"
                      className={styles.inviteBtn}
                      disabled={inviteMutation.isPending}
                      onClick={() => inviteMutation.mutate(u.sub)}
                    >
                      <span className={styles.inviteBtnLine}>
                        <span>+ {userMap[u.sub] ?? u.sub}</span>
                        <PresenceInline presence={u.presence} lastSeenAt={u.last_seen_at} />
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          ) : null}

          <button
            ref={closeRef}
            type="button"
            className={styles.modalCloseBtn}
            onClick={() => onClose()}
          >
            Закрыть
          </button>
        </div>
      </div>

      {confirmDialog && (
        <ConfirmDialog
          open
          title={confirmDialog.title}
          message={confirmDialog.message}
          confirmLabel="Подтвердить"
          cancelLabel="Отмена"
          destructive={confirmDialog.destructive}
          confirmSound={confirmDialog.destructive ? 'error' : undefined}
          disabled={removeMemberMutation.isPending}
          onConfirm={confirmDialog.onConfirm}
          onCancel={() => setConfirmDialog(null)}
        />
      )}

      <AvatarFocalPickModal
        key={avatarPickFile ? `${avatarPickFile.name}-${avatarPickFile.lastModified}` : 'closed'}
        open={avatarPickFile !== null}
        file={avatarPickFile}
        onClose={() => setAvatarPickFile(null)}
        onConfirm={({ file, focal }) => {
          setAvatarPickFile(null)
          uploadAvatarMutation.mutate({ file, focal })
        }}
      />
    </>
  )
}
