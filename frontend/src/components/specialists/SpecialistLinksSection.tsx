import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createSpecialistLink,
  deleteSpecialistLink,
  listSpecialistLinks,
} from '../../api/specialists/specialistsApi'
import { useScheduleDeleteWithUndo } from '../../hooks/useScheduleDeleteWithUndo'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import type { SpecialistLink } from '../../types/specialist'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { normalizeHttpUrl } from '../../utils/html/normalizeHttpUrl'
import { specialistLinksQueryKey } from '../../pages/specialists/specialistQueryKeys'
import { IconX } from '../icons/portalIcons'
import styles from '@/styles/modules/specialists/SpecialistDetailModal.module.css'
import linkStyles from '@/styles/modules/specialists/SpecialistLinks.module.css'

function LinkRow({ link, canDelete, onDelete, isDeleting }: {
  link: SpecialistLink
  canDelete: boolean
  onDelete: () => void
  isDeleting: boolean
}) {
  const href = normalizeHttpUrl(link.url)
  return (
    <li className={linkStyles.linkRow}>
      {href ? (
        <a href={href} target="_blank" rel="noopener noreferrer" className={linkStyles.linkAnchor}>
          {link.title}
        </a>
      ) : (
        <span className={linkStyles.linkAnchor}>{link.title}</span>
      )}
      <span className={linkStyles.linkMeta}>{new Date(link.created_at).toLocaleDateString('ru-RU')}</span>
      {canDelete && (
        <button type="button" className={linkStyles.deleteLinkBtn} disabled={isDeleting} onClick={onDelete} title="Удалить" aria-label="Удалить">
          <IconX />
        </button>
      )}
    </li>
  )
}

type Props = {
  specialistSub: string
  currentUserSub: string
  isAdmin: boolean
  canWrite: boolean
}

export function SpecialistLinksSection({ specialistSub, currentUserSub, isAdmin, canWrite }: Props) {
  const queryClient = useQueryClient()
  const scheduleDeleteWithUndo = useScheduleDeleteWithUndo()
  const notifyToast = useNotifyToast()
  const linksQk = specialistLinksQueryKey(specialistSub)

  const { data: links = [], isPending, isError, error } = useQuery({
    queryKey: linksQk,
    queryFn: () => listSpecialistLinks(specialistSub),
  })

  const [title, setTitle] = useState('')
  const [url, setUrl] = useState('')
  const [formError, setFormError] = useState('')

  const createMutation = useMutation({
    mutationFn: (body: { title: string; url: string }) =>
      createSpecialistLink(specialistSub, body),
    onSuccess: () => {
      setTitle('')
      setUrl('')
      setFormError('')
      void queryClient.invalidateQueries({ queryKey: linksQk })
    },
    onError: (e: unknown) => setFormError(userFacingMessageFromUnknown(e)),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteSpecialistLink(specialistSub, id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: linksQk }),
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e)),
  })

  function handleAdd() {
    setFormError('')
    const normalizedUrl = normalizeHttpUrl(url)
    const trimmedTitle = title.trim()
    if (!trimmedTitle || !normalizedUrl) {
      if (url.trim() && !normalizedUrl) {
        setFormError('Укажите корректный адрес (http или https)')
      }
      return
    }
    createMutation.mutate({ title: trimmedTitle, url: normalizedUrl })
  }
  function scheduleLinkDelete(link: SpecialistLink) {
    scheduleDeleteWithUndo({
      message: 'Ссылка удалена',
      optimistic: () => {
        queryClient.setQueryData<SpecialistLink[]>(linksQk, (prev) =>
          prev ? prev.filter((l) => l.id !== link.id) : [],
        )
      },
      revert: () => {
        queryClient.setQueryData<SpecialistLink[]>(linksQk, (prev) => {
          const list = prev ?? []
          if (list.some((l) => l.id === link.id)) return list
          return [...list, link].sort(
            (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
          )
        })
      },
      commit: () => deleteMutation.mutate(link.id),
    })
  }

  return (
    <div>
      {isPending ? (
        <p className="text-muted">Загрузка…</p>
      ) : isError ? (
        <p className="text-danger">{userFacingMessageFromUnknown(error)}</p>
      ) : links.length === 0 ? (
        <p className={styles.emptyHint}>Ссылок пока нет</p>
      ) : (
        <ul className={linkStyles.linkList}>
          {links.map((link) => (
            <LinkRow
              key={link.id}
              link={link}
              canDelete={isAdmin || link.created_by_sub === currentUserSub}
              onDelete={() => scheduleLinkDelete(link)}
              isDeleting={deleteMutation.isPending}
            />
          ))}
        </ul>
      )}

      {canWrite && (
        <div className={linkStyles.addLinkForm}>
          <input
            type="text"
            className="form-input"
            placeholder="Название (напр. CV)"
            value={title}
            maxLength={255}
            onChange={(e) => setTitle(e.target.value)}
          />
          <input
            type="text"
            className="form-input"
            placeholder="https://..."
            value={url}
            maxLength={2048}
            onChange={(e) => setUrl(e.target.value)}
          />
          <button
            type="button"
            className="btn-primary"
            disabled={createMutation.isPending || !title.trim() || !url.trim()}
            onClick={handleAdd}
          >
            Добавить
          </button>
          {formError && <p className="form-error">{formError}</p>}
        </div>
      )}
    </div>
  )
}
