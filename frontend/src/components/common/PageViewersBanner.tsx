import { UserAvatar } from '../ui/UserAvatar'
import { collabCaretColorFromSub } from '@/utils/documents/documentCollab'
import styles from '@/styles/modules/ui/PageViewersBanner.module.css'

export type PageViewer = {
  sub: string
  display_name: string
}

type Props = {
  viewers: PageViewer[]
  currentUserSub?: string | null
  /**
   * `avatars` — круги с обводкой цвета курсора.
   * `names` — текстовый список (задачи и прочее).
   */
  appearance?: 'names' | 'avatars'
  avatarBySub?: Record<string, string | undefined>
}

export function PageViewersBanner({
  viewers,
  currentUserSub,
  appearance = 'names',
  avatarBySub,
}: Props) {
  const others = viewers.filter((v) => v.sub !== currentUserSub)
  if (others.length === 0) return null

  if (appearance === 'avatars') {
    const names = others.map((v) => v.display_name).join(', ')
    return (
      <div
        className={`${styles.banner} ${styles.bannerAvatars}`}
        role="status"
        aria-live="polite"
        aria-label={`Кто еще на странице сейчас: ${names}`}
      >
        <span className={styles.avatarsLabel}>Кто еще на странице сейчас</span>
        <ul className={styles.avatars}>
          {others.map((v) => {
            const ring = collabCaretColorFromSub(v.sub)
            return (
              <li
                key={v.sub}
                className={styles.avatarRing}
                style={{ ['--viewer-ring' as string]: ring }}
                title={v.display_name}
              >
                <UserAvatar
                  label={v.display_name}
                  imageUrl={avatarBySub?.[v.sub]}
                  size={18}
                  className={styles.avatarFace}
                  title={v.display_name}
                />
              </li>
            )
          })}
        </ul>
      </div>
    )
  }

  const names = others.map((v) => v.display_name).join(', ')
  return (
    <div className={styles.banner} role="status" aria-live="polite">
      Сейчас на странице: {names}
    </div>
  )
}
