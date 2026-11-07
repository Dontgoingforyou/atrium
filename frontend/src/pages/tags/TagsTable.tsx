import { Fragment } from 'react'
import type { PortalTag } from '../../types/document'
import { IconLink, IconPencil, IconTrash } from '../../components/icons/portalIcons'
import { TagColorPicker } from '../../components/tags/TagColorPicker'
import { TagChip } from '../../components/tags/TagChip'
import styles from '@/styles/modules/tags/TagsPage.module.css'

export interface EditState {
  id: string
  name: string
  color: string
  expected_version: number
}

type Props = {
  tags: PortalTag[]
  canManageTags: boolean
  editState: EditState | null
  editError: string
  updatePending: boolean
  onStartEdit: (tag: PortalTag) => void
  onEditNameChange: (name: string) => void
  onEditColorChange: (color: string) => void
  onSaveEdit: () => void
  onCancelEdit: () => void
  onRequestDelete: (tag: PortalTag) => void
  onQuickColorChange: (tag: PortalTag, color: string) => void
  onViewUsages: (tag: PortalTag) => void
}

export function TagsTable({
  tags,
  canManageTags,
  editState,
  editError,
  updatePending,
  onStartEdit,
  onEditNameChange,
  onEditColorChange,
  onSaveEdit,
  onCancelEdit,
  onRequestDelete,
  onQuickColorChange,
  onViewUsages,
}: Props) {
  return (
    <div className={styles.tableCard}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Тег</th>
            <th>Slug</th>
            <th>Цвет</th>
            <th className={styles.actionsCell} />
          </tr>
        </thead>
        <tbody>
          {tags.map((tag) => (
            <Fragment key={tag.id}>
              <tr>
                <td>
                  <TagChip storedColor={tag.color} className={styles.tagChip}>
                    {tag.name}
                  </TagChip>
                </td>
                <td className={styles.slugCell}>{tag.slug}</td>
                <td>
                  {canManageTags ? (
                    <label
                      className={styles.colorSwatchBtn}
                      style={{ backgroundColor: tag.color }}
                      title={`Изменить цвет ${tag.color}`}
                    >
                      <input
                        type="color"
                        className={styles.swatchColorInput}
                        value={tag.color}
                        onChange={(e) => onQuickColorChange(tag, e.target.value)}
                        aria-label={`Изменить цвет тега ${tag.name}`}
                      />
                    </label>
                  ) : (
                    <span
                      className={styles.colorSwatch}
                      style={{ backgroundColor: tag.color }}
                      title={tag.color}
                    />
                  )}
                  <span className={styles.slugCell}>{tag.color}</span>
                </td>
                <td className={styles.actionsCell}>
                  <div className={styles.actions}>
                    <button
                      type="button"
                      className={styles.iconBtn}
                      title="Связи"
                      aria-label={`Связи тега ${tag.name}`}
                      onClick={() => onViewUsages(tag)}
                    >
                      <IconLink />
                    </button>
                    {canManageTags ? (
                      <>
                        <button
                          type="button"
                          className={styles.iconBtn}
                          title="Редактировать"
                          aria-label="Редактировать тег"
                          onClick={() => onStartEdit(tag)}
                        >
                          <IconPencil />
                        </button>
                        <button
                          type="button"
                          className={`${styles.iconBtn} ${styles.iconBtnDanger}`}
                          title="Удалить"
                          aria-label="Удалить тег"
                          onClick={() => onRequestDelete(tag)}
                        >
                          <IconTrash />
                        </button>
                      </>
                    ) : null}
                  </div>
                </td>
              </tr>
              {canManageTags && editState?.id === tag.id ? (
                <tr className={styles.editRow}>
                  <td colSpan={3}>
                    <form
                      id={`tag-edit-${tag.id}`}
                      className={styles.editForm}
                      onSubmit={(e) => {
                        e.preventDefault()
                        onSaveEdit()
                      }}
                    >
                      <input
                        type="text"
                        className={`form-input ${styles.editFormField}`}
                        value={editState.name}
                        onChange={(e) => onEditNameChange(e.target.value)}
                        aria-label="Название тега"
                        autoFocus
                      />
                      <TagColorPicker
                        value={editState.color}
                        onChange={onEditColorChange}
                        compact
                        ariaLabel="Цвет тега"
                      />
                      {editError ? <p className={`form-error ${styles.errorText}`}>{editError}</p> : null}
                    </form>
                  </td>
                  <td className={styles.actionsCell}>
                    <div className={styles.editActions}>
                      <button
                        type="submit"
                        form={`tag-edit-${tag.id}`}
                        className={`btn-primary ${styles.pageBtn}`}
                        disabled={updatePending || !editState.name.trim()}
                      >
                        {updatePending ? 'Сохранение…' : 'Сохранить'}
                      </button>
                      <button
                        type="button"
                        className={`btn-secondary ${styles.pageBtn}`}
                        onClick={onCancelEdit}
                      >
                        Отмена
                      </button>
                    </div>
                  </td>
                </tr>
              ) : null}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  )
}
