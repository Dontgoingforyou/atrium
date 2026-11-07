import { tourAnchorSelector, type GuidedTourStepSource } from '../domain/onboarding/guidedTour'

export const FIRST_DOCUMENT_LINK = 'a[href^="/documents/"]'

export type DocumentStepId = 'nav-documents' | 'document-title' | 'document-body' | 'document-comments'

type DocumentStepBase = Pick<GuidedTourStepSource, 'id' | 'title' | 'selector'>

const DOCUMENT_STEP_BASE: Record<DocumentStepId, DocumentStepBase> = {
  'nav-documents': {
    id: 'nav-documents',
    title: 'Документы',
    selector: tourAnchorSelector('nav-documents'),
  },
  'document-title': {
    id: 'document-title',
    title: 'Заголовок документа',
    selector: tourAnchorSelector('document-title'),
  },
  'document-body': {
    id: 'document-body',
    title: 'Содержимое',
    selector: tourAnchorSelector('document-body'),
  },
  'document-comments': {
    id: 'document-comments',
    title: 'Комментарии',
    selector: tourAnchorSelector('document-comments'),
  },
}

export function documentStep(
  id: DocumentStepId,
  rest: Omit<Partial<GuidedTourStepSource>, 'id' | 'title' | 'selector' | 'body'> & {
    body: GuidedTourStepSource['body']
  },
): GuidedTourStepSource {
  return { ...DOCUMENT_STEP_BASE[id], ...rest }
}
