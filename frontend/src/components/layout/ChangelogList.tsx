import { useState } from 'react'

import {
  WHATS_NEW_ENTRIES,
  formatWhatsNewDate,
  whatsNewPage,
} from '@/domain/changelog/whatsNew'

import styles from '@/styles/modules/changelog/ChangelogList.module.css'

export function ChangelogList() {
  const [loadedPages, setLoadedPages] = useState(1)
  const visible = Array.from({ length: loadedPages }, (_, pageIndex) =>
    whatsNewPage(WHATS_NEW_ENTRIES, pageIndex),
  ).flat()
  const hasMore = whatsNewPage(WHATS_NEW_ENTRIES, loadedPages).length > 0

  return (
    <div className={styles.listWrap}>
      <ol className={styles.list}>
        {visible.map((entry, index) => (
          <li key={entry.version} className={index === 0 ? styles.latest : styles.entry}>
            <p className={styles.version}>{entry.version}</p>
            <time className={styles.date} dateTime={entry.date}>
              {formatWhatsNewDate(entry.date)}
            </time>
            <p className={styles.text}>{entry.text}</p>
          </li>
        ))}
      </ol>
      {hasMore ? (
        <button
          type="button"
          className={styles.more}
          onClick={() => setLoadedPages((pages) => pages + 1)}
        >
          Показать предыдущие
        </button>
      ) : null}
    </div>
  )
}
