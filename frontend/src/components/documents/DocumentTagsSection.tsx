import { useEffect, useRef, useState } from 'react'

import { DOCUMENT_TAGS_EDITOR_ATTR } from '@/domain/documents/documentTagsEditor'
import { TagPicker } from '../common/TagPicker'
import { TagChip } from '../tags/TagChip'
import type { PortalDocument } from '../../types/document'
import shell from '@/styles/modules/documents/PortalDocumentShell.module.css'

const TAGS_EDITOR_ANIM_MS = 280

type Props = {
  data: PortalDocument
  canEdit: boolean
  onSaveTagIds: (tagIds: string[]) => void
}

function tagsEditorAnimMs(): number {
  if (typeof window === 'undefined') return TAGS_EDITOR_ANIM_MS
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : TAGS_EDITOR_ANIM_MS
}

/** Редактор / просмотр тегов документа. */
export function DocumentTagsSection({ data, canEdit, onSaveTagIds }: Props) {
  const [tagIds, setTagIds] = useState<string[]>(() => data.tags.map((t) => t.id))
  const [tagsMounted, setTagsMounted] = useState(false)
  const [tagsOpen, setTagsOpen] = useState(false)
  const closeTimerRef = useRef<number | null>(null)
  const openFrameRef = useRef<number | null>(null)

  useEffect(
    () => () => {
      if (closeTimerRef.current !== null) window.clearTimeout(closeTimerRef.current)
      if (openFrameRef.current !== null) window.cancelAnimationFrame(openFrameRef.current)
    },
    [],
  )

  const openTags = () => {
    if (closeTimerRef.current !== null) {
      window.clearTimeout(closeTimerRef.current)
      closeTimerRef.current = null
    }
    setTagsMounted(true)
    openFrameRef.current = window.requestAnimationFrame(() => {
      openFrameRef.current = window.requestAnimationFrame(() => {
        openFrameRef.current = null
        setTagsOpen(true)
      })
    })
  }

  const closeTags = () => {
    if (openFrameRef.current !== null) {
      window.cancelAnimationFrame(openFrameRef.current)
      openFrameRef.current = null
    }
    setTagsOpen(false)
    if (closeTimerRef.current !== null) window.clearTimeout(closeTimerRef.current)
    closeTimerRef.current = window.setTimeout(() => {
      closeTimerRef.current = null
      setTagsMounted(false)
    }, tagsEditorAnimMs())
  }

  return (
    <div className={shell.tagsRow} {...(canEdit ? { [DOCUMENT_TAGS_EDITOR_ATTR]: true } : {})}>
      {canEdit ? (
        tagsMounted ? (
          <div className={shell.tagsEditorShell} data-state={tagsOpen ? 'open' : 'closed'}>
            <div className={shell.tagsEditorInner}>
              <div className={shell.tagsEditor}>
                <TagPicker
                  selectedIds={tagIds}
                  onChange={(ids) => {
                    setTagIds(ids)
                    onSaveTagIds(ids)
                  }}
                />
                <button
                  type="button"
                  className={shell.tagsClose}
                  aria-label="Закрыть теги"
                  title="Закрыть теги"
                  onMouseDown={(event) => event.stopPropagation()}
                  onClick={closeTags}
                >
                  ✕
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div
            className={`${shell.tagList} ${shell.tagListClickable}`}
            onClick={openTags}
            title="Нажмите, чтобы изменить теги"
          >
            {data.tags.length > 0 ? (
              data.tags.map((t) => (
                <TagChip key={t.id} storedColor={t.color} className={shell.tagChip} active>
                  {t.name}
                </TagChip>
              ))
            ) : (
              <span className={shell.tagsPlaceholder}>+ Добавить теги</span>
            )}
          </div>
        )
      ) : data.tags.length > 0 ? (
        <div className={shell.tagList}>
          {data.tags.map((t) => (
            <TagChip key={t.id} storedColor={t.color} className={shell.tagChip} active>
              {t.name}
            </TagChip>
          ))}
        </div>
      ) : null}
    </div>
  )
}
