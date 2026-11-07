import { useEffect, useId, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { searchPortal } from '@/api/search/searchApi'
import { listDocuments } from '@/api/documents/documentsApi'
import { Modal } from '@/components/ui/Modal'
import { userFacingMessageFromUnknown } from '@/utils/apiUserMessage'
import { documentDialogRecentQueryKey, documentDialogSearchQueryKey } from '@/utils/documents/documentNavigation'
import styles from '@/styles/modules/tasks/RichTextEditorDialogs.module.css'

type DocumentOption = {
  id: string
  title: string
}

type Props = {
  open: boolean
  onClose: () => void
  onInsert: (doc: DocumentOption) => void
}

export function DocumentLinkDialog({ open, onClose, onInsert }: Props) {
  if (!open) return null
  return <DocumentLinkDialogContent onClose={onClose} onInsert={onInsert} />
}

function DocumentLinkDialogContent({
  onClose,
  onInsert,
}: Omit<Props, 'open'>) {
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([])
  const listboxId = useId()

  useEffect(() => {
    requestAnimationFrame(() => inputRef.current?.focus())
  }, [])

  const trimmed = query.trim()
  const useSearch = trimmed.length >= 2

  const recentQuery = useQuery({
    queryKey: documentDialogRecentQueryKey(),
    queryFn: () => listDocuments({ limit: 20 }),
    enabled: !useSearch,
    staleTime: 60_000,
  })

  const searchQuery = useQuery({
    queryKey: documentDialogSearchQueryKey(trimmed),
    queryFn: () => searchPortal({ q: trimmed, types: ['document'], limit: 20 }),
    enabled: useSearch,
    staleTime: 30_000,
  })

  const results: DocumentOption[] = useSearch
    ? (searchQuery.data ?? [])
        .filter((r) => r.entity_type === 'document' && r.title)
        .map((r) => ({ id: r.entity_id, title: r.title! }))
    : (recentQuery.data?.items ?? [])
        .filter((d) => d.title)
        .map((d) => ({ id: d.id, title: d.title! }))

  const isPending = useSearch ? searchQuery.isPending : recentQuery.isPending
  const isError = useSearch ? searchQuery.isError : recentQuery.isError
  const error = useSearch ? searchQuery.error : recentQuery.error

  useEffect(() => {
    if (activeIndex < 0) return
    optionRefs.current[activeIndex]?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex])

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Escape') {
      e.preventDefault()
      onClose()
      return
    }
    if (results.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex((i) => (i < 0 ? 0 : Math.min(results.length - 1, i + 1)))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex((i) => (i <= 0 ? results.length - 1 : i - 1))
    } else if (e.key === 'Enter') {
      const picked = activeIndex >= 0 ? results[activeIndex] : null
      if (picked) {
        e.preventDefault()
        onInsert(picked)
        onClose()
      }
    }
  }

  return (
    <Modal title="Ссылка на документ" onClose={onClose} maxWidth={420}>
      <p className={styles.dialogHint}>
        Начните вводить название документа для поиска.
      </p>
      <input
        ref={inputRef}
        type="search"
        className={styles.dialogInput}
        placeholder="Поиск документа…"
        aria-label="Поиск документа"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          setActiveIndex(-1)
        }}
        onKeyDown={onKeyDown}
        role="combobox"
        aria-expanded={results.length > 0}
        aria-haspopup="listbox"
        aria-autocomplete="list"
        aria-controls={listboxId}
        aria-activedescendant={
          activeIndex >= 0 ? `${listboxId}-opt-${activeIndex}` : undefined
        }
      />
      <div className={styles.dialogDocList} id={listboxId} role="listbox" aria-label="Документы">
        {isPending ? (
          <p className={styles.dialogDocEmpty}>Загрузка…</p>
        ) : isError ? (
          <p className={styles.dialogDocEmpty} role="alert">
            {userFacingMessageFromUnknown(error)}
          </p>
        ) : results.length === 0 ? (
          <p className={styles.dialogDocEmpty}>
            {useSearch ? 'Документы не найдены' : 'Нет доступных документов'}
          </p>
        ) : (
          results.map((doc, index) => (
            <button
              key={doc.id}
              ref={(el) => { optionRefs.current[index] = el }}
              id={`${listboxId}-opt-${index}`}
              type="button"
              className={styles.dialogDocItem}
              role="option"
              aria-selected={activeIndex === index}
              onMouseEnter={() => setActiveIndex(index)}
              onMouseDown={(e) => {
                e.preventDefault()
                onInsert(doc)
                onClose()
              }}
            >
              <span className={styles.dialogDocItemIcon} aria-hidden>
                📄
              </span>
              <span className={styles.dialogDocItemTitle}>{doc.title}</span>
            </button>
          ))
        )}
      </div>
      <div className={styles.dialogActions}>
        <button type="button" className={styles.dialogBtnSecondary} onClick={onClose}>
          Отмена
        </button>
      </div>
    </Modal>
  )
}
