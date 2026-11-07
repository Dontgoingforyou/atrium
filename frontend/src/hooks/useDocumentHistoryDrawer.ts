import { useRightDrawer, type UseRightDrawerReturn } from './useRightDrawer'

export type UseDocumentHistoryDrawerReturn = UseRightDrawerReturn

export function useDocumentHistoryDrawer(): UseDocumentHistoryDrawerReturn {
  return useRightDrawer()
}
