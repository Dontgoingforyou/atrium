import { memo, useState } from 'react'
import { useResolvedAvatarUrl } from '../../hooks/useResolvedAvatarUrl'
import { useStableImageUrl } from '../../hooks/useStableImageUrl'
import { avatarInnerKind } from '../../utils/avatar/resolveAvatarDisplayState'
import { initialsFromLabel } from '../../utils/avatar/userAvatarText'
import styles from '@/styles/modules/ui/UserAvatar.module.css'

const SIZE_MAP = { sm: 28, md: 36, lg: 44 } as const

export type UserAvatarSize = keyof typeof SIZE_MAP | number

function resolveSize(size: UserAvatarSize): number {
  if (typeof size === 'number') return size
  return SIZE_MAP[size]
}

type Props =
  | {
      /** Подпись для инициалов и alt */
      label: string
      imageUrl?: string | null
      /** Центр кадра 0–1 (из профиля); по умолчанию центр изображения */
      focalX?: number | null
      focalY?: number | null
      size?: UserAvatarSize
      className?: string
      title?: string
      /** Eager — только для видимого аватара в шапке / настройках; списки — lazy. */
      loading?: 'lazy' | 'eager'
      onClick?: undefined
    }
  | {
      /** Подпись для инициалов и alt */
      label: string
      imageUrl?: string | null
      /** Центр кадра 0–1 (из профиля); по умолчанию центр изображения */
      focalX?: number | null
      focalY?: number | null
      size?: UserAvatarSize
      className?: string
      /** Обязательное доступное имя действия кнопки (aria-label/title). */
      title: string
      /** Eager — только для видимого аватара в шапке / настройках; списки — lazy. */
      loading?: 'lazy' | 'eager'
      /** Если задан — корневая кнопка (загрузка аватара в шапке). */
      onClick: () => void
    }

export const UserAvatar = memo(function UserAvatar({
  label,
  imageUrl,
  focalX,
  focalY,
  size = 'md',
  className,
  title,
  onClick,
  loading = 'lazy',
}: Props) {
  const px = resolveSize(size)
  const resolved = useResolvedAvatarUrl(imageUrl)
  const resolvedHref = resolved.kind === 'url' ? resolved.href : null
  const displayedUrl = useStableImageUrl(resolvedHref, resolved.kind === 'pending')
  /** URL, при загрузке которого сработал onError; смена `displayedUrl` сама сбрасывает «битый» кадр. */
  const [failedUrl, setFailedUrl] = useState<string | null>(null)
  const innerKind = avatarInnerKind(displayedUrl, failedUrl)
  const initials = initialsFromLabel(label || '?')
  const combinedClass = [styles.root, onClick ? styles.button : '', className].filter(Boolean).join(' ')

  const fallbackFont = Math.max(10, Math.round(px * 0.36))
  const fx = focalX != null && !Number.isNaN(focalX) ? focalX : 0.5
  const fy = focalY != null && !Number.isNaN(focalY) ? focalY : 0.5
  const objectPosition = `${fx * 100}% ${fy * 100}%`

  const inner =
    innerKind === 'img' ? (
      <img
        src={displayedUrl!}
        alt=""
        className={styles.img}
        style={{ objectPosition }}
        onError={() => setFailedUrl(displayedUrl!)}
        loading={loading}
        decoding="async"
      />
    ) : (
      <span className={styles.fallback} style={{ fontSize: fallbackFont }}>
        {initials}
      </span>
    )

  const style: React.CSSProperties = { width: px, height: px, minWidth: px, minHeight: px }

  if (onClick) {
    return (
      <button
        type="button"
        className={combinedClass}
        style={style}
        onClick={onClick}
        title={title}
        aria-label={title}
      >
        {inner}
      </button>
    )
  }

  return (
    <span className={combinedClass} style={style} title={title ?? label} role="img" aria-label={label}>
      {inner}
    </span>
  )
})
