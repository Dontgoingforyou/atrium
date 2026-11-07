import styles from '@/styles/modules/onboarding/GuidedTour.module.css'

export type SpotlightRect = {
  top: number
  left: number
  width: number
  height: number
}

type Props = {
  /** null — сплошной dim без обводки (переход / ожидание якоря). */
  rect: SpotlightRect | null
}

const PAD = 6

export function TourSpotlight({ rect }: Props) {
  if (!rect) {
    return <div className={styles.dimPanel} style={{ inset: 0 }} aria-hidden />
  }

  const top = Math.max(0, rect.top - PAD)
  const left = Math.max(0, rect.left - PAD)
  const width = Math.max(0, rect.width + PAD * 2)
  const height = Math.max(0, rect.height + PAD * 2)

  return (
    <div className={styles.spotlightRoot} aria-hidden>
      <div
        className={styles.holeCutout}
        style={{
          top,
          left,
          width,
          height,
        }}
      />
    </div>
  )
}
