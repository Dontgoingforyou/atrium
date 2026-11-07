import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createTag, listTags } from '../../api/tags/tagsApi'
import { PORTAL_TAGS_QUERY_KEY } from '../../api/queryKeys'
import { TagColorPicker } from '../../components/tags/TagColorPicker'
import { useThemeStore } from '../../store/themeStore'
import type { PortalTag } from '../../types/document'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { getDefaultTagColor, getTagChipStyle } from '../../utils/tags/tagColor'
import styles from '@/styles/modules/tags/TagPicker.module.css'

interface TagPickerProps {
  selectedIds: string[]
  onChange: (ids: string[]) => void
}

export function TagPicker({ selectedIds, onChange }: TagPickerProps) {
  const queryClient = useQueryClient()
  const theme = useThemeStore((s) => s.theme)
  const [search, setSearch] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newName, setNewName] = useState('')
  const [newColor, setNewColor] = useState(() => getDefaultTagColor(theme))
  const [createError, setCreateError] = useState('')

  const { data: allTags = [], isError, error } = useQuery<PortalTag[]>({
    queryKey: PORTAL_TAGS_QUERY_KEY,
    queryFn: listTags,
  })

  const createMutation = useMutation({
    mutationFn: () => createTag({ name: newName.trim(), color: newColor }),
    onSuccess: (tag) => {
      void queryClient.invalidateQueries({ queryKey: PORTAL_TAGS_QUERY_KEY })
      onChange([...selectedIds, tag.id])
      setNewName('')
      setNewColor(getDefaultTagColor(theme))
      setShowCreateForm(false)
      setSearch('')
      setCreateError('')
    },
    onError: (e: unknown) => setCreateError(userFacingMessageFromUnknown(e)),
  })

  function toggleTag(tagId: string) {
    onChange(
      selectedIds.includes(tagId)
        ? selectedIds.filter((id) => id !== tagId)
        : [...selectedIds, tagId],
    )
  }

  const q = search.trim().toLowerCase()
  const filteredTags = allTags.filter((t) => t.name.toLowerCase().includes(q))
  const exactMatch = allTags.some((t) => t.name.trim().toLowerCase() === q)

  function handleOpenCreate() {
    setNewName(search)
    setShowCreateForm(true)
  }

  function handleCancelCreate() {
    setShowCreateForm(false)
    setNewName('')
    setNewColor(getDefaultTagColor(theme))
    setCreateError('')
  }

  function handleCreateSubmit() {
    createMutation.mutate()
  }

  return (
    <div className={styles.root}>
      <div className={styles.searchRow}>
        <input
          type="text"
          className={`form-input ${styles.searchInput}`}
          placeholder="Поиск тегов…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {search.trim() && !exactMatch && !showCreateForm && (
          <button type="button" className={styles.createBtn} onClick={handleOpenCreate}>
            + Создать «{search.trim()}»
          </button>
        )}
      </div>

      {showCreateForm && (
        <div className={styles.createForm}>
          <input
            type="text"
            className={`form-input ${styles.createFormInput}`}
            placeholder="Название тега"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
          <TagColorPicker value={newColor} onChange={setNewColor} compact />
          <div className={styles.createActions}>
            <button
              type="button"
              className="btn-primary"
              disabled={createMutation.isPending || !newName.trim()}
              onClick={handleCreateSubmit}
            >
              {createMutation.isPending ? 'Создание…' : 'Создать'}
            </button>
            <button type="button" className="btn-secondary" onClick={handleCancelCreate}>
              Отмена
            </button>
          </div>
          {createError && <p className="form-error">{createError}</p>}
        </div>
      )}

      <div className={styles.chips}>
        {isError ? (
          <span className="form-error" role="alert">
            {userFacingMessageFromUnknown(error)}
          </span>
        ) : filteredTags.length === 0 && !showCreateForm ? (
          <span className={styles.emptyHint}>Теги не найдены</span>
        ) : (
          filteredTags.map((tag) => {
            const active = selectedIds.includes(tag.id)
            return (
              <button
                key={tag.id}
                type="button"
                onClick={() => toggleTag(tag.id)}
                className={styles.chip}
                style={getTagChipStyle(tag.color, theme, { active })}
              >
                {tag.name}
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}
