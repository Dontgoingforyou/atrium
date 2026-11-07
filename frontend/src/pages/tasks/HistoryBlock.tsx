import { memo, useMemo, type ReactNode } from 'react'
import { formatHistoryValue } from '../../domain/tasks/taskHistoryFormatting'
import type { TaskHistoryEntry } from '../../types/task'
import { UserChipBySub } from '../../components/ui/UserChip'
import styles from '@/styles/modules/tasks/TaskDetailPage.module.css'

const HISTORY_FIELD_LABELS: Record<string, string> = {
  title: 'Название',
  description: 'Описание',
  status: 'Статус',
  priority: 'Приоритет',
  assignee_sub: 'Исполнитель',
  assignee_subs: 'Исполнители',
  due_at: 'Срок',
  action: 'Событие',
  document_id: 'Документ',
  chat_id: 'Чат',
}

type HistoryResolvers = {
  resolveUserSub: (sub: string | null | undefined) => string
  resolveDocumentTitle: (id: string) => string
  resolveChatTitle: (id: string) => string
}

const HistoryEntryItem = memo(function HistoryEntryItem({
  entry,
  resolveUserSub,
  resolveDocumentTitle,
  resolveChatTitle,
}: { entry: TaskHistoryEntry } & HistoryResolvers) {
  const resolvers = useMemo(
    () => ({
      documentTitle: resolveDocumentTitle,
      chatTitle: resolveChatTitle,
    }),
    [resolveDocumentTitle, resolveChatTitle],
  )

  const diffRows = useMemo(() => {
    return Object.entries(entry.diff).map(([field, change]): { field: string; node: ReactNode } => {
      if (field === 'action' && change.new === 'created') {
        return { field, node: <strong>Задача создана</strong> }
      }
      return {
        field,
        node: (
          <>
            <strong>{HISTORY_FIELD_LABELS[field] ?? field}:</strong>{' '}
            {formatHistoryValue(field, change.old, resolveUserSub, resolvers)} →{' '}
            {formatHistoryValue(field, change.new, resolveUserSub, resolvers)}
          </>
        ),
      }
    })
  }, [entry.diff, resolveUserSub, resolvers])

  return (
    <li className={styles.historyItem}>
      <div className={styles.historyMeta}>
        {entry.changed_by_sub ? (
          <span className={styles.historyActor}>
            <UserChipBySub sub={entry.changed_by_sub} />
          </span>
        ) : null}
        <time className={styles.historyTime} dateTime={entry.changed_at}>
          {new Date(entry.changed_at).toLocaleString('ru-RU')}
        </time>
      </div>
      <ul className={styles.historyDiff}>
        {diffRows.map(({ field, node }) => (
          <li key={field}>{node}</li>
        ))}
      </ul>
    </li>
  )
})

export const HistoryBlock = memo(function HistoryBlock({
  entries,
  resolveUserSub,
  resolveDocumentTitle,
  resolveChatTitle,
}: { entries: TaskHistoryEntry[] } & HistoryResolvers) {
  if (!entries.length) {
    return <p className="text-muted">Пока нет записей истории.</p>
  }
  return (
    <ul className={styles.historyList}>
      {entries.map((e) => (
        <HistoryEntryItem
          key={e.id}
          entry={e}
          resolveUserSub={resolveUserSub}
          resolveDocumentTitle={resolveDocumentTitle}
          resolveChatTitle={resolveChatTitle}
        />
      ))}
    </ul>
  )
})
