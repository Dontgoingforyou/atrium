import type { UseQueryResult } from '@tanstack/react-query'
import { Link } from 'react-router'
import type { TagUsages } from '../../api/tags/tagsApi'
import { TAG_USAGE_LIST_LIMIT } from '../../api/tags/tagsApi'
import type { PortalTag } from '../../types/document'
import { TagChip } from './TagChip'
import { tagUsageTaskLabel } from '../../domain/tags/tagUsageLabels'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { RightDrawer } from '../ui/RightDrawer'
import styles from '@/styles/modules/tags/TagUsageDrawer.module.css'

type Props = {
  tag: PortalTag
  usagesQuery: UseQueryResult<TagUsages>
  entered: boolean
  onClose: () => void
  onTransitionEnd: (e: React.TransitionEvent<HTMLElement>) => void
}

export function TagUsageDrawer({
  tag,
  usagesQuery,
  entered,
  onClose,
  onTransitionEnd,
}: Props) {
  const data = usagesQuery.data
  const docs = data?.documents ?? []
  const tasks = data?.tasks ?? []
  const docsTotal = data?.documentsTotal ?? 0
  const docsMore = docsTotal > docs.length ? docsTotal - docs.length : 0
  const tasksMaybeMore = tasks.length >= TAG_USAGE_LIST_LIMIT

  return (
    <RightDrawer
      ariaLabel={`Связи тега ${tag.name}`}
      title="Связи тега"
      entered={entered}
      onClose={onClose}
      onTransitionEnd={onTransitionEnd}
    >
      <p className={styles.tagName}>
        <TagChip storedColor={tag.color} className={styles.tagChip}>
          {tag.name}
        </TagChip>
      </p>

      {usagesQuery.isPending ? (
        <p className="text-muted">Загрузка…</p>
      ) : usagesQuery.isError ? (
        <p className="text-danger">{userFacingMessageFromUnknown(usagesQuery.error)}</p>
      ) : docs.length === 0 && tasks.length === 0 ? (
        <p className={styles.empty}>Связей не найдено</p>
      ) : (
        <>
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>Документы</h3>
            {docs.length === 0 ? (
              <p className={styles.empty}>Нет привязанных документов</p>
            ) : (
              <ul className={styles.linkList}>
                {docs.map((doc) => (
                  <li key={doc.id}>
                    <Link
                      to={`/documents/${encodeURIComponent(doc.id)}`}
                      className={styles.usageLink}
                      onClick={onClose}
                    >
                      {doc.title.trim() || 'Без названия'}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
            {docsMore > 0 ? <p className={styles.moreHint}>и ещё {docsMore}</p> : null}
          </section>

          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>Задачи</h3>
            {tasks.length === 0 ? (
              <p className={styles.empty}>Нет привязанных задач</p>
            ) : (
              <ul className={styles.linkList}>
                {tasks.map((task) => (
                  <li key={task.id}>
                    <Link
                      to={`/tasks/${encodeURIComponent(task.id)}`}
                      className={styles.usageLink}
                      onClick={onClose}
                    >
                      {tagUsageTaskLabel(task)}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
            {tasksMaybeMore ? (
              <p className={styles.moreHint}>показаны первые {TAG_USAGE_LIST_LIMIT}</p>
            ) : null}
          </section>
        </>
      )}
    </RightDrawer>
  )
}
