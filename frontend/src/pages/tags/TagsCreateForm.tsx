import { TagColorPicker } from '../../components/tags/TagColorPicker'
import styles from '@/styles/modules/tags/TagsPage.module.css'

type Props = {
  name: string
  color: string
  error: string
  pending: boolean
  onNameChange: (name: string) => void
  onColorChange: (color: string) => void
  onSubmit: () => void
  onCancel: () => void
}

export function TagsCreateForm({
  name,
  color,
  error,
  pending,
  onNameChange,
  onColorChange,
  onSubmit,
  onCancel,
}: Props) {
  return (
    <form
      className={styles.createForm}
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit()
      }}
    >
      <div className={styles.createFormField}>
        <label className={styles.createFormLabel} htmlFor="create-tag-name">
          Название
        </label>
        <input
          id="create-tag-name"
          type="text"
          className="form-input"
          placeholder="Название тега"
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          autoFocus
        />
      </div>
      <div className={styles.createFormFieldColor}>
        <label htmlFor="create-tag-color" className={styles.createFormLabel}>
          Цвет
        </label>
        <TagColorPicker
          id="create-tag-color"
          value={color}
          onChange={onColorChange}
          ariaLabel="Цвет тега"
        />
      </div>
      <div className={styles.createActions}>
        <button
          type="submit"
          className={`btn-primary ${styles.pageBtn}`}
          disabled={pending || !name.trim()}
        >
          {pending ? 'Создание…' : 'Создать'}
        </button>
        <button type="button" className={`btn-secondary ${styles.pageBtn}`} onClick={onCancel}>
          Отмена
        </button>
      </div>
      {error ? <p className={`form-error ${styles.errorText}`}>{error}</p> : null}
    </form>
  )
}
