import { useState } from 'react'

import { changelogSeenStorageKey } from '@/constants/changelog'
import { WHATS_NEW_ENTRIES, hasUnseenWhatsNew } from '@/domain/changelog/whatsNew'
import { IconHistory, PORTAL_ICON_SIZE } from '@/components/icons/portalIcons'
import { Modal } from '@/components/ui/Modal'
import { ChangelogList } from '@/components/layout/ChangelogList'
import { useAuthStore } from '@/store/authStore'

import styles from '@/styles/modules/layout/ChangelogButton.module.css'

function readSeenVersion(userSub: string): string | null {
  if (!userSub) return null
  try {
    return localStorage.getItem(changelogSeenStorageKey(userSub))
  } catch {
    return null
  }
}

function rememberSeenVersion(userSub: string, version: string) {
  if (!userSub) return
  try {
    localStorage.setItem(changelogSeenStorageKey(userSub), version)
  } catch {
    // приватный режим без хранилища — кружок останется до перезагрузки
  }
}

export function ChangelogButton() {
  const userSub = useAuthStore((s) => s.user?.sub ?? '')
  const latestVersion = WHATS_NEW_ENTRIES[0]?.version ?? null
  const [open, setOpen] = useState(false)
  const [seenFor, setSeenFor] = useState(() => ({
    sub: userSub,
    version: readSeenVersion(userSub),
  }))
  if (seenFor.sub !== userSub) {
    setSeenFor({ sub: userSub, version: readSeenVersion(userSub) })
  }
  const unseen = hasUnseenWhatsNew(seenFor.version, latestVersion)

  function openChangelog() {
    setOpen(true)
    if (latestVersion != null && userSub && seenFor.version !== latestVersion) {
      rememberSeenVersion(userSub, latestVersion)
      setSeenFor({ sub: userSub, version: latestVersion })
    }
  }

  return (
    <>
      <span className={styles.wrap}>
        <button
          type="button"
          className={open ? `${styles.btn} ${styles.btnActive}` : styles.btn}
          aria-label={unseen ? 'Что нового, есть непрочитанное обновление' : 'Что нового'}
          title="Что нового"
          onClick={openChangelog}
        >
          <IconHistory size={PORTAL_ICON_SIZE} />
        </button>
        {unseen ? <span className={styles.dot} aria-hidden /> : null}
      </span>
      {open ? (
        <Modal title="Что нового" onClose={() => setOpen(false)}>
          <ChangelogList />
        </Modal>
      ) : null}
    </>
  )
}
