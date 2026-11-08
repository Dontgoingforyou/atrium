import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
} from 'react'
import { RichTextEditor } from '../tasks/richText/RichTextEditor'
import { useDebouncedEffect } from '../../hooks/useDebouncedEffect'
import { useClickOutside } from '../../hooks/useClickOutside'
import { useDocumentCollabSession } from '../../hooks/useDocumentCollabSession'
import { useSanitizedRichHtml } from '../../hooks/useSanitizedRichHtml'
import { useSearchHighlightQuery } from '../../hooks/useSearchHighlightQuery'
import { useHighlightedSafeHtml } from '../../hooks/useHighlightedSafeHtml'
import { useScrollToSearchHit } from '../../hooks/useScrollToSearchHit'
import { applyBuildinToggleAutoOpen } from '../../domain/documents/buildinToggle'
import { DOCUMENT_TAGS_EDITOR_SELECTOR } from '../../domain/documents/documentTagsEditor'
import { BLOCK_REORDER_HANDLE_SELECTOR } from '../../domain/documents/richTextBlockReorder'
import { handleRichTextContainerClick } from '../../utils/html/richTextLinkClick'
import {
  documentBodyIsDirty,
  normalizeDocumentBody,
} from '../../utils/documents/normalizeDocumentBody'
import {
  collabCaretColorFromSub,
  isDocumentCollabPersistActive,
} from '../../utils/documents/documentCollab'
import styles from '@/styles/modules/documents/PortalDocumentShell.module.css'
import '@/styles/modules/search/SearchHitMark.module.css'

/** Схлопывание панели; смена режима редактора — после неё (см. transition у .docToolbarSlotShell). */
const TOOLBAR_ANIM_MS = 280

/** Порталы в document.body: меню, диалоги и ручка перестановки блока. */
const BODY_EDIT_OUTSIDE_IGNORE = `[role="menu"], [role="dialog"], [role="listbox"], [data-table-float-menu], [data-table-float-slot], ${BLOCK_REORDER_HANDLE_SELECTOR}, ${DOCUMENT_TAGS_EDITOR_SELECTOR}`

export type DocumentBodySectionHandle = {
  isDirty: () => boolean
  flushSave: () => Promise<void>
  discardChanges: () => void
}

type Props = {
  documentId: string
  body: string | null | undefined
  canEdit: boolean
  isBodyEditing: boolean
  isSaving: boolean
  onSave: (body: string | null) => void
  onFlushSave: (body: string | null) => Promise<unknown>
  onDirtyChange?: (dirty: boolean) => void
  onStartEdit?: () => void
  onRequestEndEdit?: () => void
  /** Открыт диалог несохранённых изменений — не разворачивать панель до закрытия. */
  unsavedDialogOpen?: boolean
  /** Слот для тулбара в sticky chrome страницы документа. */
  toolbarSlotEl?: HTMLElement | null
  /** Открытость chrome-панели (вместе с анимацией скрытия, не только bodyEditing). */
  onToolbarChromeOpen?: (open: boolean) => void
  currentUserSub?: string
  currentUserDisplayName?: string
}

export const DocumentBodySection = forwardRef<DocumentBodySectionHandle, Props>(
  function DocumentBodySection(
    {
      documentId,
      body,
      canEdit,
      isBodyEditing,
      isSaving,
      onSave,
      onFlushSave,
      onDirtyChange,
      onStartEdit,
      onRequestEndEdit,
      unsavedDialogOpen = false,
      toolbarSlotEl,
      onToolbarChromeOpen,
      currentUserSub,
      currentUserDisplayName,
    },
    ref,
  ) {
    const [value, setValue] = useState(body ?? '')
    const [prevBody, setPrevBody] = useState(body)
    const [savedFlash, setSavedFlash] = useState(false)
    const [toolbarCollapsing, setToolbarCollapsing] = useState(false)
    const [editUiSync, setEditUiSync] = useState(() => ({
      isBodyEditing,
      unsavedDialogOpen,
    }))
    const wasSavingRef = useRef(false)
    const editorSheetRef = useRef<HTMLDivElement>(null)
    const toolbarSlotElRef = useRef<HTMLElement | null>(null)
    const exitTimerRef = useRef<number | null>(null)

    const collabEnabled = Boolean(canEdit && isBodyEditing && currentUserSub)
    const { session: collabSession, status: collabStatus } = useDocumentCollabSession({
      documentId,
      enabled: collabEnabled,
      userSub: currentUserSub,
      displayName: currentUserDisplayName,
    })
    const collabPersist = isDocumentCollabPersistActive(collabStatus)
    const collaboration = useMemo(() => {
      if (!collabPersist || !collabSession || !currentUserSub) return null
      return {
        ydoc: collabSession.ydoc,
        provider: collabSession.provider,
        user: {
          name: currentUserDisplayName || currentUserSub,
          color: collabCaretColorFromSub(currentUserSub),
        },
      }
    }, [collabPersist, collabSession, currentUserSub, currentUserDisplayName])

    // layout: до paint и до клика по тулбару, иначе слот ещё null в outside-check.
    useLayoutEffect(() => {
      toolbarSlotElRef.current = toolbarSlotEl ?? null
    }, [toolbarSlotEl])

    // Охраняемый setState в рендере (React «adjusting state when props change»):
    // условие становится false после установки — цикла рендеров нет, а синхронизация
    // отрабатывает до paint, без мигания старого значения.
    if (prevBody !== body) {
      setPrevBody(body)
      // Collab: REST body/version обновляется (snapshot/meta), Y.Doc не сбрасываем
      const skipSync =
        Boolean(collaboration) || (isBodyEditing && documentBodyIsDirty(value, body))
      if (!skipSync) {
        setValue(body ?? '')
      }
    }

    if (
      isBodyEditing !== editUiSync.isBodyEditing ||
      unsavedDialogOpen !== editUiSync.unsavedDialogOpen
    ) {
      const prev = editUiSync
      setEditUiSync({ isBodyEditing, unsavedDialogOpen })
      if (!isBodyEditing) {
        setToolbarCollapsing(false)
      } else if (isBodyEditing && prev.unsavedDialogOpen && !unsavedDialogOpen) {
        setToolbarCollapsing(false)
      }
    }

    const toolbarExpanded = isBodyEditing && !toolbarCollapsing
    useLayoutEffect(() => {
      onToolbarChromeOpen?.(toolbarExpanded)
    }, [toolbarExpanded, onToolbarChromeOpen])
    useLayoutEffect(() => {
      return () => onToolbarChromeOpen?.(false)
    }, [onToolbarChromeOpen])
    // При collab dirty не блокирует выход: snapshot пишет Hocuspocus через CAS
    const dirty =
      canEdit && isBodyEditing && !collabPersist && documentBodyIsDirty(value, body)

    useEffect(() => {
      onDirtyChange?.(dirty)
    }, [dirty, onDirtyChange])

    useEffect(
      () => () => {
        if (exitTimerRef.current !== null) {
          window.clearTimeout(exitTimerRef.current)
        }
      },
      [],
    )

    const scheduleEndEdit = useCallback(() => {
      if (!isBodyEditing || toolbarCollapsing) return
      setToolbarCollapsing(true)
      if (exitTimerRef.current !== null) {
        window.clearTimeout(exitTimerRef.current)
      }
      exitTimerRef.current = window.setTimeout(() => {
        exitTimerRef.current = null
        onRequestEndEdit?.()
      }, TOOLBAR_ANIM_MS)
    }, [isBodyEditing, toolbarCollapsing, onRequestEndEdit])

    useClickOutside(
      isBodyEditing && !unsavedDialogOpen,
      [editorSheetRef, toolbarSlotElRef],
      scheduleEndEdit,
      'mousedown',
      BODY_EDIT_OUTSIDE_IGNORE,
    )

    const handleIdleStartEdit = useCallback(
      (e: ReactMouseEvent) => {
        if (isBodyEditing) return
        if ((e.target as HTMLElement).closest('a')) return
        onStartEdit?.()
      },
      [isBodyEditing, onStartEdit],
    )

    useDebouncedEffect(
      () => {
        if (!canEdit || !isBodyEditing) return
        if (collabPersist) return
        const b = normalizeDocumentBody(value)
        if (b === normalizeDocumentBody(body)) return
        onSave(b)
      },
      [value, body, canEdit, isBodyEditing, onSave, collabPersist],
      600,
    )

    useEffect(() => {
      if (isSaving) {
        wasSavingRef.current = true
        return
      }
      if (wasSavingRef.current) {
        wasSavingRef.current = false
        const t1 = window.setTimeout(() => setSavedFlash(true), 0)
        const t2 = window.setTimeout(() => setSavedFlash(false), 2000)
        return () => {
          window.clearTimeout(t1)
          window.clearTimeout(t2)
        }
      }
    }, [isSaving])

    useEffect(() => {
      if (!isBodyEditing) return
      const onKey = (e: KeyboardEvent) => {
        if (e.key === 'Escape') scheduleEndEdit()
      }
      document.addEventListener('keydown', onKey)
      return () => document.removeEventListener('keydown', onKey)
    }, [isBodyEditing, scheduleEndEdit])

    useImperativeHandle(
      ref,
      () => ({
        isDirty: () => (collabPersist ? false : documentBodyIsDirty(value, body)),
        flushSave: async () => {
          if (collabPersist) return
          const b = normalizeDocumentBody(value)
          if (b === normalizeDocumentBody(body)) return
          await onFlushSave(b)
        },
        discardChanges: () => {
          setValue(body ?? '')
        },
      }),
      [value, body, onFlushSave, collabPersist],
    )

    const safeBodyHtml = useSanitizedRichHtml(body)
    const highlightQuery = useSearchHighlightQuery()
    const bodyHtmlRef = useRef<HTMLDivElement>(null)

    const readOnlyHtml = useMemo(() => {
      if (!body || body.trim() === '') {
        return '<p class="body-placeholder">Нет текста</p>'
      }
      return applyBuildinToggleAutoOpen(safeBodyHtml)
    }, [body, safeBodyHtml])

    const displayHtml = useHighlightedSafeHtml(readOnlyHtml, highlightQuery)
    const showHtmlView = !canEdit || (Boolean(highlightQuery) && !isBodyEditing)
    useScrollToSearchHit(bodyHtmlRef, highlightQuery, showHtmlView && Boolean(safeBodyHtml))

    if (showHtmlView) {
      return (
        <div
          ref={bodyHtmlRef}
          className={styles.bodyHtml}
          dangerouslySetInnerHTML={{ __html: displayHtml }}
          onClick={(e) =>
            handleRichTextContainerClick(e, canEdit ? () => handleIdleStartEdit(e) : undefined)
          }
          onDoubleClick={canEdit ? handleIdleStartEdit : undefined}
        />
      )
    }

    return (
      <div
        ref={editorSheetRef}
        className={`${styles.bodyEditorSheet} ${!isBodyEditing ? styles.bodyEditorSheetIdle : ''}`}
        onClick={!isBodyEditing ? handleIdleStartEdit : undefined}
        onDoubleClick={!isBodyEditing ? handleIdleStartEdit : undefined}
      >
        <RichTextEditor
          content={value || '<p></p>'}
          onChange={setValue}
          minRows={isBodyEditing ? 4 : 1}
          entityType="document"
          entityId={documentId}
          appearance="sheet"
          showToolbar
          toolbarExpanded={toolbarExpanded}
          toolbarSlotEl={toolbarSlotEl}
          editable={isBodyEditing}
          collaboration={collaboration}
        />
        {!collaboration && collabStatus !== 'connecting' && (isSaving || savedFlash) ? (
          <p className={styles.bodySaveStatus} aria-live="polite">
            {isSaving ? 'Сохранение…' : 'Сохранено'}
          </p>
        ) : null}
      </div>
    )
  },
)
