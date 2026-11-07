import type { CrossSectionLocal } from '@/utils/navigation/navCrossSectionTree'
import { parentDocumentIdForNavSlug } from '@/domain/documents/documentNavSections'
import { DroppableSection, TopLevelSortableDoc } from './NavTopLevelSortableDoc'
import styles from '@/styles/modules/layout/AppLayout.module.css'

type SectionLocal = CrossSectionLocal

type ReorderBody = { before_id?: string; after_id?: string }

export function CrossSectionNavSection({
  section,
  sectionIndex,
  canEdit,
  createPending,
  onCreate,
  isCollapsed,
  onToggleBranch,
  onNestedReorder,
}: {
  section: SectionLocal
  sectionIndex: number
  canEdit: boolean
  createPending: boolean
  onCreate: (slug: string) => void
  isCollapsed: (id: string) => boolean
  onToggleBranch: (id: string) => void
  onNestedReorder: (parentDocId: string, docId: string, body: ReorderBody) => Promise<void>
}) {
  return (
    <DroppableSection slug={section.slug}>
      <div className={styles.sectionHeader}>
        <span className={styles.sectionLabel}>{section.title.toUpperCase()}</span>
        {canEdit ? (
          <div className={styles.navTrailingActionSlot}>
            <button
              type="button"
              className={styles.sectionAddBtn}
              data-tour={sectionIndex === 0 ? 'documents-create' : undefined}
              title={`Создать документ в «${section.title}»`}
              aria-label={`Создать документ в разделе «${section.title}»`}
              disabled={createPending}
              onClick={() => onCreate(section.slug)}
            >
              +
            </button>
          </div>
        ) : null}
      </div>
      {section.docs.length === 0 ? (
        <p className={styles.navEmpty}>Перетащите документ сюда или нажмите +</p>
      ) : (
        section.docs.map((doc) => (
          <TopLevelSortableDoc
            key={doc.id}
            doc={doc}
            slug={section.slug}
            sectionParentId={parentDocumentIdForNavSlug(section.slug)}
            isBranchCollapsed={isCollapsed}
            onToggleBranch={onToggleBranch}
            canEditDocuments={canEdit}
            onNestedReorder={async (documentId, body) => {
              await onNestedReorder(doc.id, documentId, body)
            }}
          />
        ))
      )}
    </DroppableSection>
  )
}
