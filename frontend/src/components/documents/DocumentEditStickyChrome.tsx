import { type ReactNode, type RefCallback } from 'react'

import { DocumentBreadcrumbNav } from './DocumentBreadcrumbNav'
import type { PortalDocument } from '../../types/document'
import styles from '@/styles/modules/documents/PortalDocumentShell.module.css'

type BreadcrumbItem = PortalDocument['breadcrumb'][number]

type Props = {
  breadcrumb: BreadcrumbItem[]
  currentTitle: string
  toolbarSlotRef: RefCallback<HTMLDivElement | null>
  toolbarOpen?: boolean
  viewersSlot?: ReactNode
}

export function DocumentEditStickyChrome({
  breadcrumb,
  currentTitle,
  toolbarSlotRef,
  toolbarOpen = false,
  viewersSlot,
}: Props) {
  return (
    <div className={styles.docStickyChrome} data-toolbar={toolbarOpen ? 'open' : 'closed'}>
      <div className={styles.docStickyChromeTop}>
        <DocumentBreadcrumbNav breadcrumb={breadcrumb} currentTitle={currentTitle} embedded />
        {viewersSlot}
      </div>
      <div
        className={styles.docToolbarSlotShell}
        data-state={toolbarOpen ? 'open' : 'closed'}
        aria-hidden={!toolbarOpen ? true : undefined}
      >
        <div ref={toolbarSlotRef} className={styles.docToolbarSlot} />
      </div>
    </div>
  )
}
