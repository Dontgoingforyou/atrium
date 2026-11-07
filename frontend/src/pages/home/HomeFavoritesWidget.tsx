import { Link } from 'react-router'
import type { PortalFavorite } from '../../types/favorite'
import { IconFileText } from '../../components/icons/portalIcons'
import styles from '@/styles/modules/home/HomePage.module.css'
import { CountBadge } from './HomeKpi'

function FavoriteChip({ favorite }: { favorite: PortalFavorite }) {
  const href = `/documents/${encodeURIComponent(favorite.target_id)}`

  return (
    <Link to={href} className={styles.favoriteChip}>
      <span className={styles.favoriteChipIcon} aria-hidden>
        <IconFileText />
      </span>
      <span className={styles.favoriteChipTitle}>{favorite.title}</span>
    </Link>
  )
}

export function HomeFavoritesWidget({ favorites }: { favorites: PortalFavorite[] }) {
  return (
    <section className={styles.section} data-tour="home-favorites">
      <div className={styles.widgetHeader}>
        <div className={styles.widgetHeaderMain}>
          <h2 className="section-heading">Избранное</h2>
          <CountBadge label={String(favorites.length)} tone="circle" />
        </div>
      </div>
      {favorites.length === 0 ? (
        <p className={`text-muted ${styles.textSmall}`}>
          Нет элементов в избранном — добавьте звёздочку на странице документа или в списке документов
        </p>
      ) : (
        <div className={styles.favoriteChips}>
          {favorites.map((f) => (
            <FavoriteChip key={f.id} favorite={f} />
          ))}
        </div>
      )}
    </section>
  )
}
