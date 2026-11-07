import type { MaterialStatus, MaterialType } from '../../types/learning'

export const MATERIAL_TYPE_LABELS: Record<MaterialType, string> = {
  article: 'Статья',
  video: 'Видео',
  presentation: 'Презентация',
  instruction: 'Инструкция',
}

export const MATERIAL_STATUS_LABELS: Record<MaterialStatus, string> = {
  draft: 'Черновик',
  active: 'Опубликован',
  archived: 'В архиве',
}

export type MaterialFormState = {
  title: string
  body: string
  material_type: MaterialType
  status: MaterialStatus
}

export function emptyMaterialForm(): MaterialFormState {
  return { title: '', body: '', material_type: 'article', status: 'draft' }
}
