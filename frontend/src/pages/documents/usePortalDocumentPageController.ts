import { useCallback, useEffect, useRef, useState, type RefObject } from 'react'
import { useBlocker, useNavigate } from 'react-router'
import { useMutation, useQuery, type QueryClient } from '@tanstack/react-query'

import { getDocumentHistory, updatePortalDocument } from '../../api/documents/documentsApi'
import { isApiConflictError } from '../../api/apiConflict'
import type { DocumentBodySectionHandle } from '../../components/documents/DocumentBodySection'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { useRightDrawer, type UseRightDrawerReturn } from '../../hooks/useRightDrawer'
import { invalidatePortalSearchQueries } from '@/utils/search/invalidatePortalSearch'
import { invalidateTagUsages } from '@/utils/tags/invalidateTagUsages'
import {
  documentChildrenQueryKey,
  documentHistoryQueryKey,
  portalDocumentQueryKey,
} from '../../utils/documents/documentNavigation'
import {
  patchNavigationTreeDocumentIcon,
  patchNavigationTreeDocumentTitle,
  refetchPortalNavigationTree,
} from '@/utils/navigation/patchPortalNavigationTreeCache'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import type {
  PortalDocument,
  PortalDocumentHistory,
  PortalDocumentUpdate,
} from '../../types/document'

export type DocumentSavePatch = Omit<PortalDocumentUpdate, 'expected_version'> & {
  expected_version?: number
}

type UnsavedExitAction = 'view' | 'navigate'

type SaveMutApi = {
  mutate: (patch: DocumentSavePatch) => void
  mutateAsync: (patch: DocumentSavePatch) => Promise<PortalDocument>
  isPending: boolean
}

export type PortalDocumentPageController = {
  toolbarSlotEl: HTMLDivElement | null
  setToolbarSlotEl: (el: HTMLDivElement | null) => void
  toolbarChromeOpen: boolean
  setToolbarChromeOpen: (open: boolean) => void
  bodyEditing: boolean
  setBodyDirty: (dirty: boolean) => void
  saveMut: SaveMutApi
  historyDrawer: UseRightDrawerReturn
  historyQuery: ReturnType<typeof useQuery<PortalDocumentHistory[]>>
  unsavedExit: UnsavedExitAction | null
  unsavedSaving: boolean
  startBodyEdit: () => void
  requestEndBodyEdit: () => void
  handleUnsavedSave: () => Promise<void>
  handleUnsavedDiscard: () => void
  closeUnsavedDialog: () => void
  navigateAfterTrash: () => void
  onDeleteRevert: () => void
}

function patchAffectsNavOrChildren(patch: DocumentSavePatch): boolean {
  return 'title' in patch || 'icon_emoji' in patch || 'parent_document_id' in patch
}

/**
 * Оркестрация страницы документа: сохранение, режим редактирования тела,
 * блокировка навигации при несохранённых изменениях, drawer истории.
 * Страница остаётся тонкой композицией. ref на body-секцию владеет компонент
 * (не возвращается из контроллера), чтобы не смешивать ref со state в одном объекте.
 */
export function usePortalDocumentPageController(
  documentId: string,
  data: PortalDocument,
  qc: QueryClient,
  bodySectionRef: RefObject<DocumentBodySectionHandle | null>,
): PortalDocumentPageController {
  const navigate = useNavigate()
  const [toolbarSlotEl, setToolbarSlotEl] = useState<HTMLDivElement | null>(null)
  const [toolbarChromeOpen, setToolbarChromeOpen] = useState(false)
  const notifyToast = useNotifyToast()
  const [bodyEditing, setBodyEditing] = useState(false)
  const [bodyDirty, setBodyDirty] = useState(false)
  const [unsavedExit, setUnsavedExit] = useState<UnsavedExitAction | null>(null)
  const [unsavedSaving, setUnsavedSaving] = useState(false)
  const [saveQueueBusy, setSaveQueueBusy] = useState(false)
  const historyDrawer = useRightDrawer()

  const queuedPatchRef = useRef<DocumentSavePatch | null>(null)
  const inFlightRef = useRef(false)
  const inflightPromiseRef = useRef<Promise<PortalDocument> | null>(null)

  const resolveExpectedVersion = useCallback(
    (patch: DocumentSavePatch): number => {
      if (patch.expected_version != null) return patch.expected_version
      const cached = qc.getQueryData<PortalDocument>(portalDocumentQueryKey(documentId))
      return cached?.version ?? data.version
    },
    [qc, documentId, data.version],
  )

  useEffect(() => {
    setBodyEditing(false)
    setToolbarChromeOpen(false)
    setBodyDirty(false)
    setUnsavedExit(null)
    queuedPatchRef.current = null
    inFlightRef.current = false
    inflightPromiseRef.current = null
    setSaveQueueBusy(false)
  }, [documentId])

  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      bodyEditing && bodyDirty && currentLocation.pathname !== nextLocation.pathname,
  )

  useEffect(() => {
    if (blocker.state === 'blocked') {
      setUnsavedExit('navigate')
    }
  }, [blocker.state, unsavedExit])

  useEffect(() => {
    if (!bodyEditing || !bodyDirty) return
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => window.removeEventListener('beforeunload', onBeforeUnload)
  }, [bodyEditing, bodyDirty])

  const historyQuery = useQuery({
    queryKey: documentHistoryQueryKey(documentId),
    queryFn: () => getDocumentHistory(documentId),
    enabled: historyDrawer.open,
  })

  const invalidate = useCallback(
    (next: PortalDocument, patch: DocumentSavePatch) => {
      void qc.setQueryData(portalDocumentQueryKey(documentId), next)
      if (patchAffectsNavOrChildren(patch)) {
        if ('title' in patch) {
          patchNavigationTreeDocumentTitle(qc, documentId, next.title)
        }
        if ('icon_emoji' in patch) {
          patchNavigationTreeDocumentIcon(qc, documentId, next.icon_emoji ?? null)
        }
        refetchPortalNavigationTree(qc)
      }
      void qc.invalidateQueries({ queryKey: documentHistoryQueryKey(documentId) })
      if (patchAffectsNavOrChildren(patch) && next.parent_document_id) {
        void qc.invalidateQueries({
          queryKey: documentChildrenQueryKey(next.parent_document_id),
        })
      }
    },
    [qc, documentId],
  )

  const saveMut = useMutation({
    mutationFn: (patch: DocumentSavePatch) =>
      updatePortalDocument(documentId, {
        ...patch,
        expected_version: resolveExpectedVersion(patch),
      }),
    onSuccess: (next, patch) => {
      invalidate(next, patch)
      invalidatePortalSearchQueries(qc)
      if ('tag_ids' in patch) {
        invalidateTagUsages(qc)
      }
    },
    onError: (e) => {
      if (isApiConflictError(e)) {
        notifyToast(e.message)
        void qc.invalidateQueries({ queryKey: portalDocumentQueryKey(documentId) })
        return
      }
      notifyToast(userFacingMessageFromUnknown(e))
    },
  })
  const mutateAsyncRef = useRef(saveMut.mutateAsync)
  mutateAsyncRef.current = saveMut.mutateAsync

  const enqueueSave = useCallback(
    (patch: DocumentSavePatch): Promise<PortalDocument> => {
      if (inFlightRef.current && inflightPromiseRef.current) {
        queuedPatchRef.current = { ...queuedPatchRef.current, ...patch }
        return inflightPromiseRef.current
      }
      inFlightRef.current = true
      setSaveQueueBusy(true)
      const drain = async (): Promise<PortalDocument> => {
        let current: DocumentSavePatch = patch
        let result: PortalDocument | undefined
        try {
          while (true) {
            try {
              result = await mutateAsyncRef.current(current)
            } catch (err) {
              if (isApiConflictError(err)) {
                queuedPatchRef.current = null
                void qc.invalidateQueries({ queryKey: portalDocumentQueryKey(documentId) })
                throw err
              }
              const afterError = queuedPatchRef.current
              queuedPatchRef.current = null
              if (!afterError) throw err
              current = afterError
              continue
            }
            const next = queuedPatchRef.current
            if (next) {
              queuedPatchRef.current = null
              current = next
              continue
            }
            inFlightRef.current = false
            const sneaked = queuedPatchRef.current
            if (sneaked) {
              inFlightRef.current = true
              queuedPatchRef.current = null
              current = sneaked
              continue
            }
            inflightPromiseRef.current = null
            setSaveQueueBusy(false)
            return result as PortalDocument
          }
        } catch (err) {
          inFlightRef.current = false
          inflightPromiseRef.current = null
          setSaveQueueBusy(false)
          throw err
        }
      }
      const promise = drain()
      inflightPromiseRef.current = promise
      return promise
    },
    [documentId, qc],
  )

  const saveMutApi: SaveMutApi = {
    mutate: (patch) => {
      void enqueueSave(patch)
    },
    mutateAsync: (patch) => enqueueSave(patch),
    isPending: saveMut.isPending || saveQueueBusy,
  }

  const finishBodyExit = useCallback(() => {
    setBodyEditing(false)
    setUnsavedExit(null)
    if (blocker.state === 'blocked') {
      blocker.proceed?.()
    }
  }, [blocker])

  const startBodyEdit = useCallback(() => {
    setBodyEditing(true)
  }, [])

  const requestEndBodyEdit = useCallback(() => {
    if (!bodyEditing) return
    if (!bodyDirty) {
      setBodyEditing(false)
      return
    }
    setUnsavedExit('view')
  }, [bodyEditing, bodyDirty])

  const closeUnsavedDialog = useCallback(() => {
    setUnsavedExit(null)
    if (blocker.state === 'blocked') {
      blocker.reset?.()
    }
  }, [blocker])

  const handleUnsavedSave = useCallback(async () => {
    setUnsavedSaving(true)
    try {
      await bodySectionRef.current?.flushSave()
      finishBodyExit()
    } catch (e) {
      notifyToast(userFacingMessageFromUnknown(e))
    } finally {
      setUnsavedSaving(false)
    }
  }, [bodySectionRef, finishBodyExit, notifyToast])

  const handleUnsavedDiscard = useCallback(() => {
    bodySectionRef.current?.discardChanges()
    finishBodyExit()
  }, [bodySectionRef, finishBodyExit])

  const navigateAfterTrash = useCallback(() => {
    const parentId = data.parent_document_id
    void navigate(parentId ? `/documents/${encodeURIComponent(parentId)}` : '/')
  }, [data.parent_document_id, navigate])

  const onDeleteRevert = useCallback(() => {
    void navigate(`/documents/${encodeURIComponent(documentId)}`)
    void qc.invalidateQueries({ queryKey: portalDocumentQueryKey(documentId) })
  }, [documentId, navigate, qc])

  return {
    toolbarSlotEl,
    setToolbarSlotEl,
    toolbarChromeOpen,
    setToolbarChromeOpen,
    bodyEditing,
    setBodyDirty,
    saveMut: saveMutApi,
    historyDrawer,
    historyQuery,
    unsavedExit,
    unsavedSaving,
    startBodyEdit,
    requestEndBodyEdit,
    handleUnsavedSave,
    handleUnsavedDiscard,
    closeUnsavedDialog,
    navigateAfterTrash,
    onDeleteRevert,
  }
}
