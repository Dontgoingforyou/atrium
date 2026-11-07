import { authenticatedFetch } from '../api/rawClient'
import { parseJsonOrThrowApi } from '../api/parseResponse'
import { warnTourCleanupError } from './tourCleanupLog'

export const TOUR_DEMO_DOCUMENT_TITLE = 'Учебный документ'

export type EnsureTourDemoDocumentResult =
  | { ok: true; created: boolean; documentId: string }
  | { ok: false; reason: string }

export async function ensureGuidedTourDemoDocument(): Promise<EnsureTourDemoDocumentResult> {
  try {
    const res = await authenticatedFetch('/portal/documents/tour-demo/ensure', {
      method: 'POST',
    })
    const body = (await parseJsonOrThrowApi(res)) as { id: string; created?: boolean }
    if (!body.id) {
      return { ok: false, reason: 'Не удалось подготовить учебный документ.' }
    }
    return { ok: true, created: Boolean(body.created), documentId: body.id }
  } catch {
    return { ok: false, reason: 'Не удалось подготовить учебный документ.' }
  }
}

export async function cleanupGuidedTourDemoDocument(): Promise<void> {
  try {
    await authenticatedFetch('/portal/documents/tour-demo', { method: 'DELETE' })
  } catch (e) {
    warnTourCleanupError('demo document', e)
  }
}

export { stepNeedsTourDemoDocument } from '../domain/onboarding/guidedTour'
