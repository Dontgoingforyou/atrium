import type { EmojiMartData } from '@emoji-mart/data'
import Picker from '@emoji-mart/react'
import i18nRu from '@emoji-mart/data/i18n/ru.json'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

import { patchPortalDocumentWithCas } from '../../api/documents/documentsApi'
import { useClickOutside } from '../../hooks/useClickOutside'
import { useDropdownPosition } from '../../hooks/useDropdownPosition'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { useAuthStore } from '../../store/authStore'
import { isUserManagerOrAdmin } from '@/domain/auth/authRoles'
import { loadEmojiMartDataWithRuSearch } from '../../utils/emojiDataRuLazy'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { portalDocumentQueryKey } from '@/utils/documents/documentNavigation'
import { patchNavigationTreeDocumentIcon } from '@/utils/navigation/patchPortalNavigationTreeCache'
import { DocGlyph } from './NavDocRowParts'
import styles from '@/styles/modules/layout/NavDocumentTreeIcon.module.css'

type Props = {
  documentId: string
  iconEmoji?: string | null
  glyphClassName: string
  /** Крупнее — рядом с заголовком на странице документа */
  size?: 'nav' | 'page'
}

const EMOJI_PICKER_MAX_HEIGHT = 400

function useEmojiMartTheme(): 'light' | 'dark' {
  const [theme, setTheme] = useState<'light' | 'dark'>(() =>
    typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light',
  )
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const fn = () => setTheme(mq.matches ? 'dark' : 'light')
    mq.addEventListener('change', fn)
    return () => mq.removeEventListener('change', fn)
  }, [])
  return theme
}

export function NavDocumentTreeIcon({ documentId, iconEmoji, glyphClassName, size = 'nav' }: Props) {
  const qc = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const notify = useNotifyToast()
  const canEditIcon = user ? isUserManagerOrAdmin(user) : false
  const [open, setOpen] = useState(false)
  const anchorRef = useRef<HTMLButtonElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const popoverPos = useDropdownPosition(open, anchorRef, EMOJI_PICKER_MAX_HEIGHT)
  const theme = useEmojiMartTheme()
  const [emojiMartData, setEmojiMartData] = useState<EmojiMartData | null>(null)

  const close = useCallback(() => setOpen(false), [])

  useEffect(() => {
    if (!open) return
    let cancelled = false
    void loadEmojiMartDataWithRuSearch().then((d) => {
      if (!cancelled) setEmojiMartData(d)
    })
    return () => {
      cancelled = true
    }
  }, [open])

  useClickOutside(open, [anchorRef, popoverRef], close, 'pointerdown')

  useEffect(() => {
    if (!open) return
    function onKeydown(e: KeyboardEvent) {
      if (e.key === 'Escape') close()
    }
    document.addEventListener('keydown', onKeydown)
    return () => document.removeEventListener('keydown', onKeydown)
  }, [open, close])

  const mut = useMutation({
    mutationFn: (next: string | null) => patchPortalDocumentWithCas(documentId, { icon_emoji: next }),
    onMutate: (next) => {
      const prev = iconEmoji ?? null
      patchNavigationTreeDocumentIcon(qc, documentId, next)
      return { prev }
    },
    onError: (err, _next, ctx) => {
      if (ctx?.prev !== undefined) {
        patchNavigationTreeDocumentIcon(qc, documentId, ctx.prev)
      }
      notify(userFacingMessageFromUnknown(err))
    },
    onSuccess: (doc) => {
      patchNavigationTreeDocumentIcon(qc, documentId, doc.icon_emoji ?? null)
      void qc.invalidateQueries({ queryKey: portalDocumentQueryKey(documentId) })
    },
  })

  const emojiClass = size === 'page' ? `${styles.emojiGlyph} ${styles.emojiGlyphPage}` : styles.emojiGlyph

  if (!canEditIcon) {
    return (
      <span className={styles.wrap} aria-hidden>
        {iconEmoji ? <span className={emojiClass}>{iconEmoji}</span> : <DocGlyph className={glyphClassName} />}
      </span>
    )
  }

  return (
    <span className={styles.wrap}>
      <button
        ref={anchorRef}
        type="button"
        className={styles.iconBtn}
        title="Выбрать эмодзи"
        aria-label="Выбрать эмодзи для документа"
        aria-expanded={open}
        onPointerDown={(e) => e.stopPropagation()}
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          setOpen((v) => !v)
        }}
      >
        {iconEmoji ? (
          <span className={emojiClass} aria-hidden>
            {iconEmoji}
          </span>
        ) : (
          <DocGlyph className={glyphClassName} />
        )}
      </button>
      {open
        ? createPortal(
            <div
              ref={popoverRef}
              className={styles.popover}
              style={{
                top: popoverPos.top,
                left: Math.max(8, popoverPos.left),
                maxHeight: popoverPos.maxHeight,
                overflowY: 'auto',
              }}
              role="dialog"
              aria-label="Выбор эмодзи"
            >
              {emojiMartData ? (
                <Picker
                  data={emojiMartData}
                  i18n={i18nRu}
                  locale="ru"
                  set="native"
                  theme={theme}
                  dynamicWidth
                  perLine={11}
                  emojiSize={26}
                  emojiButtonSize={40}
                  maxFrequentRows={3}
                  previewPosition="none"
                  onEmojiSelect={(sel: { native: string }) => {
                    mut.mutate(sel.native)
                    close()
                  }}
                />
              ) : (
                <div className={`text-muted ${styles.popoverLoading}`}>Загрузка…</div>
              )}
              <div className={styles.popoverFooter}>
                <button
                  type="button"
                  className={styles.resetLink}
                  onClick={() => {
                    mut.mutate(null)
                    close()
                  }}
                >
                  Убрать эмодзи
                </button>
              </div>
            </div>,
            document.body,
          )
        : null}
    </span>
  )
}
