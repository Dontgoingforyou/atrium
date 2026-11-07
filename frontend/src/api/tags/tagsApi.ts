import type { PortalDocumentBrief, PortalTag, PortalTagCreate, PortalTagUpdate } from '../../types/document'
import type { PortalTask } from '../../types/task'
import { parseJsonOrThrowApi } from '../parseResponse'
import { authenticatedFetch } from '../rawClient'
import { listDocuments } from '../documents/documentsApi'
import { listTasks } from '../tasks/tasksApi'

// ── CRUD тегов ────────────────────────────────────────────────────────────

export async function listTags(): Promise<PortalTag[]> {
  const res = await authenticatedFetch('/portal/tags')
  return parseJsonOrThrowApi(res)
}

export async function createTag(data: PortalTagCreate): Promise<PortalTag> {
  const res = await authenticatedFetch('/portal/tags', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return parseJsonOrThrowApi(res)
}

export async function updateTag(id: string, data: PortalTagUpdate): Promise<PortalTag> {
  const res = await authenticatedFetch(`/portal/tags/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return parseJsonOrThrowApi(res)
}

export async function deleteTag(id: string): Promise<void> {
  const res = await authenticatedFetch(`/portal/tags/${id}`, { method: 'DELETE' })
  await parseJsonOrThrowApi(res)
}

// ── Агрегатор использования тега (документы + задачи) ──────────────────────

export const TAG_USAGE_LIST_LIMIT = 100

export type TagUsages = {
  documents: PortalDocumentBrief[]
  documentsTotal: number
  tasks: PortalTask[]
}

export async function getTagUsages(
  tag: PortalTag,
  limit = TAG_USAGE_LIST_LIMIT,
): Promise<TagUsages> {
  const [docsPage, tasks] = await Promise.all([
    listDocuments({ tag_slug: tag.slug, skip: 0, limit }),
    listTasks({ tag_id: tag.id, skip: 0, limit }),
  ])
  return {
    documents: docsPage.items,
    documentsTotal: docsPage.total,
    tasks,
  }
}
