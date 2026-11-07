import styles from '@/styles/modules/tags/TagColorPicker.module.css'

type Props = {
  value: string
  onChange: (color: string) => void
  compact?: boolean
  id?: string
  ariaLabel?: string
}

/** Простой picker: native input + hex. Ограничения контраста — при отображении (TagChip). */
export function TagColorPicker({ value, onChange, compact = false, id, ariaLabel }: Props) {
  return (
    <div className={styles.row}>
      <input
        id={id}
        type="color"
        className={`${styles.colorInput}${compact ? ` ${styles.colorInputCompact}` : ''}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-label={ariaLabel}
      />
      <span className={styles.hexLabel}>{value.toUpperCase()}</span>
    </div>
  )
}
