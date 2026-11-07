import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { getDocument, listDocuments } from '../../../api/documents/documentsApi'
import { searchPortal } from '../../../api/search/searchApi'
import { patchTaskWithCas } from '../../../api/tasks/tasksApi'
import { isApiConflictError } from '../../../api/apiConflict'
import { SearchableSinglePicker } from '../../common/SearchableSinglePicker'
import type { SearchablePickerOption } from '../../common/searchablePickerUtils'
import { useDebouncedEffect } from '../../../hooks/useDebouncedEffect'
import { useNotifyToast } from '../../../hooks/useNotifyToast'
import { userFacingMessageFromUnknown } from '../../../utils/apiUserMessage'
import { portalDocumentQueryKey } from '@/utils/documents/documentNavigation'
import {
  taskContextLinksQueryKey,
  taskContextLinksSearchQueryKey,
  taskHistoryQueryKey,
  taskRootQueryKey,
} from '@/pages/tasks/tasksQueryKeys'
import type { PortalTask } from '../../../types/task'
import { TaskHierarchyLinks } from './TaskHierarchyLinks'
import styles from '@/styles/modules/tasks/TaskContextLinksEditor.module.css'

const UNLINKED_OPTION: SearchablePickerOption = { value: '', label: '— не привязан' }

type Props = {
  task: PortalTask
  taskId: string
}

export function TaskContextLinksEditor({ task, taskId }: Props) {
  const queryClient = useQueryClient()
  const notifyToast = useNotifyToast()
  const serverDocId = task.document_id ?? ''
  const [docId, setDocId] = useState(serverDocId)
  const [syncedLink, setSyncedLink] = useState(() => ({ taskId, serverDocId }))
  const [formError, setFormError] = useState('')
  const [pickerQuery, setPickerQuery] = useState('')
  const [debouncedPickerQuery, setDebouncedPickerQuery] = useState('')

  if (taskId !== syncedLink.taskId || serverDocId !== syncedLink.serverDocId) {
    setSyncedLink({ taskId, serverDocId })
    setDocId(serverDocId)
  }

  useDebouncedEffect(
    () => setDebouncedPickerQuery(pickerQuery.trim()),
    [pickerQuery],
    300,
  )

  const searchQ = debouncedPickerQuery
  const useSearch = searchQ.length >= 1

  const listQuery = useQuery({
    queryKey: taskContextLinksQueryKey(taskId),
    queryFn: () => listDocuments({ limit: 50 }),
    enabled: !useSearch,
    staleTime: 30_000,
  })

  const searchQuery = useQuery({
    queryKey: taskContextLinksSearchQueryKey(taskId, searchQ),
    queryFn: () => searchPortal({ q: searchQ, types: ['document'], limit: 50 }),
    enabled: useSearch,
    staleTime: 10_000,
  })

  const selectedDocQuery = useQuery({
    queryKey: portalDocumentQueryKey(docId),
    queryFn: () => getDocument(docId),
    enabled: Boolean(docId),
    staleTime: 60_000,
  })

  const taskDocumentTitle = task.document_title
  const selectedDocTitle = selectedDocQuery.data?.title
  const selectedDocDataId = selectedDocQuery.data?.id
  const selectedDocPending = selectedDocQuery.isPending
  const selectedDocFetching = selectedDocQuery.isFetching

  const documentOptions: SearchablePickerOption[] = useMemo(() => {
    const fromApi = useSearch
      ? (searchQuery.data ?? []).map((hit) => ({
          value: hit.entity_id,
          label: hit.title?.trim() || 'Без названия',
        }))
      : (listQuery.data?.items ?? []).map((d) => ({
          value: d.id,
          label: d.title?.trim() || 'Без названия',
        }))

    const seen = new Set<string>()
    const merged: SearchablePickerOption[] = [UNLINKED_OPTION]
    for (const opt of fromApi) {
      if (!opt.value || seen.has(opt.value)) continue
      seen.add(opt.value)
      merged.push(opt)
    }

    if (docId && !seen.has(docId)) {
      const queryTitle = selectedDocDataId === docId ? selectedDocTitle?.trim() : ''
      const title = queryTitle || taskDocumentTitle?.trim()
      const isLoadingDoc =
        Boolean(docId) &&
        selectedDocDataId !== docId &&
        (selectedDocPending || selectedDocFetching)
      merged.push({
        value: docId,
        label: title || (isLoadingDoc ? 'Загрузка…' : `документ ${docId.slice(0, 8)}…`),
      })
    }

    return merged
  }, [
    useSearch,
    searchQuery.data,
    listQuery.data,
    docId,
    selectedDocTitle,
    selectedDocDataId,
    selectedDocPending,
    selectedDocFetching,
    taskDocumentTitle,
  ])

  const pickerLoading =
    (useSearch && searchQuery.isFetching) || (!useSearch && listQuery.isPending)
  const pickerError = useSearch ? searchQuery.isError : listQuery.isError
  const pickerErrorData = useSearch ? searchQuery.error : listQuery.error

  const saveMutation = useMutation({
    mutationFn: (nextDocId: string) =>
      patchTaskWithCas(
        taskId,
        { document_id: nextDocId || null },
        task.version,
      ),
    onSuccess: (_saved, nextDocId) => {
      setFormError('')
      if (nextDocId) notifyToast('Сохранено')
      void queryClient.invalidateQueries({ queryKey: taskRootQueryKey(taskId) })
      void queryClient.invalidateQueries({ queryKey: taskHistoryQueryKey(taskId) })
    },
    onError: (e) => {
      if (isApiConflictError(e)) {
        void queryClient.invalidateQueries({ queryKey: taskRootQueryKey(taskId) })
      }
      setFormError(userFacingMessageFromUnknown(e))
    },
  })

  const docChanged = docId !== serverDocId

  useDebouncedEffect(() => {
    if (!docChanged) return
    saveMutation.mutate(docId)
  }, [docId, docChanged], 600)

  return (
    <div className={styles.editor}>
      <div className={styles.row}>
        <label className="form-label">
          <span className="form-label-text">Документ</span>
          <SearchableSinglePicker
            value={docId}
            onChange={setDocId}
            options={documentOptions}
            placeholder="Поиск документа…"
            loading={pickerLoading}
            filterLocally={false}
            onQueryChange={setPickerQuery}
          />
        </label>
      </div>
      {saveMutation.isPending || docChanged ? (
        <p className={styles.statusHint}>
          {saveMutation.isPending ? 'Сохраняем…' : 'Есть несохранённые изменения…'}
        </p>
      ) : null}
      {formError ? <p className="form-error">{formError}</p> : null}
      {pickerError ? (
        <p className="form-error" role="alert">
          {userFacingMessageFromUnknown(pickerErrorData)}
        </p>
      ) : null}
      <TaskHierarchyLinks task={task} taskId={taskId} />
    </div>
  )
}
