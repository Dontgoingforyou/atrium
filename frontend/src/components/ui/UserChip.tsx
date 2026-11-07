import { UserAvatar } from './UserAvatar'
import { usePortalUserDirectory } from '../../hooks/usePortalUserDirectory'
import styles from '@/styles/modules/ui/UserChip.module.css'

type Props = {
  label: string
  imageUrl?: string | null
  focalX?: number | null
  focalY?: number | null
  size?: 'sm' | 'md'
  className?: string
  title?: string
}

/** Имя пользователя с аватаром слева. */
export function UserChip({
  label,
  imageUrl,
  focalX,
  focalY,
  size = 'sm',
  className,
  title,
}: Props) {
  return (
    <span className={[styles.root, className].filter(Boolean).join(' ')} title={title ?? label}>
      <UserAvatar
        label={label}
        imageUrl={imageUrl}
        focalX={focalX}
        focalY={focalY}
        size={size}
      />
      <span className={styles.label}>{label}</span>
    </span>
  )
}

/** UserChip по sub из кэша пользователей портала. */
export function UserChipBySub({
  sub,
  size = 'sm',
  className,
  labelOverride,
}: {
  sub: string
  size?: 'sm' | 'md'
  className?: string
  labelOverride?: string
}) {
  const { getAvatarProps } = usePortalUserDirectory()
  const props = getAvatarProps(sub, labelOverride ? { label: labelOverride } : undefined)
  return <UserChip {...props} size={size} className={className} />
}
