import type { PortalDocumentHistory } from '../../types/document'
import { UserChipBySub } from '../ui/UserChip'
import {
  DOCUMENT_HISTORY_FIELD_LABELS,
  formatDocumentHistoryValue,
  isDocumentCreatedAction,
  isTagIdsReplacedDiff,
} from '@/domain/documents/documentHistoryFormatting'
import { DOCUMENT_ACTION_LABELS } from '@/domain/documents/documentLabels'
import styles from '@/styles/modules/documents/PortalDocumentAside.module.css'

export function DocumentHistoryBlock({
  entries,
  resolveUserSub,
}: {
  entries: PortalDocumentHistory[]
  resolveUserSub: (sub: string) => string
}) {
  if (!entries.length) {
    return <p className="text-muted">Пока нет записей истории.</p>
  }
  return (
    <ul className={styles.historyList}>
      {entries.map((e) => (
        <li key={e.id} className={styles.historyItem}>
          <div className={styles.historyMeta}>
            {new Date(e.changed_at).toLocaleString('ru-RU')}
            {e.changed_by_sub ? (
              <span className={styles.historyActor}>
                {' · '}
                <UserChipBySub sub={e.changed_by_sub} />
              </span>
            ) : null}
          </div>
          <ul className={styles.historyDiff}>
            {Object.entries(e.diff).map(([field, change]) => {
              if (field === 'action' && isDocumentCreatedAction(change)) {
                return (
                  <li key={field}>
                    <strong>{DOCUMENT_HISTORY_FIELD_LABELS.action}:</strong>{' '}
                    {DOCUMENT_ACTION_LABELS.created}
                  </li>
                )
              }
              if (field === 'tag_ids' && isTagIdsReplacedDiff(change)) {
                return (
                  <li key={field}>
                    <strong>{DOCUMENT_HISTORY_FIELD_LABELS.tag_ids}:</strong> обновлены
                  </li>
                )
              }
              if (
                field === 'parent_document_id' &&
                String(change.old ?? '') !== String(change.new ?? '') &&
                String(change.old ?? '').trim() !== '' &&
                String(change.new ?? '').trim() !== ''
              ) {
                return (
                  <li key={field}>
                    <strong>{DOCUMENT_HISTORY_FIELD_LABELS[field] ?? field}:</strong> изменён
                  </li>
                )
              }
              return (
                <li key={field}>
                  <strong>{DOCUMENT_HISTORY_FIELD_LABELS[field] ?? field}:</strong>{' '}
                  {formatDocumentHistoryValue(field, change.old, resolveUserSub)} →{' '}
                  {formatDocumentHistoryValue(field, change.new, resolveUserSub)}
                </li>
              )
            })}
          </ul>
        </li>
      ))}
    </ul>
  )
}
