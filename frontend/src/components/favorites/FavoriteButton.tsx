import { useDocumentFavorite } from '../../hooks/useDocumentFavorite'
import { IconStar } from '../icons/portalIcons'
import styles from '@/styles/modules/favorites/FavoriteButton.module.css'

type Props = {
  documentId: string
  title?: string
}

export function FavoriteButton({ documentId, title }: Props) {
  const { isFavorite, isPending, isListError, toggleFavorite } = useDocumentFavorite(documentId)

  const actionLabel = isFavorite ? 'Убрать из избранного' : 'Добавить в избранное'
  const titleSuffix = title ? `: ${title}` : ''
  const disabled = isPending || isListError

  function handleClick() {
    toggleFavorite()
  }

  return (
    <span className={styles.wrapper}>
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled}
        title={isListError ? 'Не удалось загрузить избранное' : `${actionLabel}${titleSuffix}`}
        aria-label={isListError ? 'Не удалось загрузить избранное' : actionLabel}
        aria-pressed={isFavorite}
        className={`${styles.btn} ${isFavorite ? styles.btnActive : styles.btnInactive} ${isPending ? styles.btnWait : ''}`}
      >
        <IconStar filled={isFavorite} />
      </button>
    </span>
  )
}
