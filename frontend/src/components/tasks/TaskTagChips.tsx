import type { PortalTag } from '../../types/task'
import { TagChip } from '../tags/TagChip'
import styles from '@/styles/modules/tasks/TaskTagChips.module.css'

export function TaskTagChips({ tags }: { tags: PortalTag[] }) {
  if (!tags.length) return null
  return (
    <div className={styles.chips}>
      {tags.map((tag) => (
        <TagChip key={tag.id} storedColor={tag.color} className={styles.chip} border="soft">
          {tag.name}
        </TagChip>
      ))}
    </div>
  )
}
