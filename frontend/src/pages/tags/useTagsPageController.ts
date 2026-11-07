import { useCallback, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isApiConflictError } from '../../api/apiConflict'
import { createTag, deleteTag, getTagUsages, listTags, updateTag } from '../../api/tags/tagsApi'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { useRightDrawer } from '../../hooks/useRightDrawer'
import { useAuthStore } from '../../store/authStore'
import { useThemeStore } from '../../store/themeStore'
import type { PortalTag } from '../../types/document'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { getDefaultTagColor } from '../../utils/tags/tagColor'
import { invalidateTagUsages } from '../../utils/tags/invalidateTagUsages'
import { isUserManagerOrAdmin } from '@/domain/auth/authRoles'
import type { EditState } from './TagsTable'
import { PORTAL_TAGS_QUERY_KEY, tagUsagesQueryKey } from './tagsQueryKeys'

export function useTagsPageController() {
  const queryClient = useQueryClient()
  const notifyToast = useNotifyToast()
  const theme = useThemeStore((s) => s.theme)
  const user = useAuthStore((s) => s.user)
  const canManageTags = user ? isUserManagerOrAdmin(user) : false

  const [showCreate, setShowCreate] = useState(false)
  const [createName, setCreateName] = useState('')
  const [createColor, setCreateColor] = useState(() => getDefaultTagColor(theme))
  const [createError, setCreateError] = useState('')

  const [editState, setEditState] = useState<EditState | null>(null)
  const [editError, setEditError] = useState('')

  const [tagPendingDelete, setTagPendingDelete] = useState<PortalTag | null>(null)
  const [deleteError, setDeleteError] = useState('')
  const [usageTag, setUsageTag] = useState<PortalTag | null>(null)
  const usageDrawer = useRightDrawer(() => setUsageTag(null))

  const { data: tags = [], isLoading, isError, error } = useQuery<PortalTag[]>({
    queryKey: PORTAL_TAGS_QUERY_KEY,
    queryFn: listTags,
  })

  const usagesQuery = useQuery({
    queryKey: tagUsagesQueryKey(usageTag?.id ?? ''),
    queryFn: () => getTagUsages(usageTag!),
    enabled: usageDrawer.open && usageTag != null,
    staleTime: 0,
    refetchOnMount: 'always',
  })

  const openDrawer = usageDrawer.openDrawer
  const closeDrawer = usageDrawer.closeDrawer

  const openUsageDrawer = useCallback(
    (tag: PortalTag) => {
      setUsageTag(tag)
      openDrawer()
      invalidateTagUsages(queryClient)
    },
    [queryClient, openDrawer],
  )

  const closeUsageDrawer = useCallback(() => {
    closeDrawer()
  }, [closeDrawer])

  const handleUsageDrawerTransitionEnd = usageDrawer.onTransitionEnd

  const resetCreateForm = useCallback(() => {
    setCreateName('')
    setCreateColor(getDefaultTagColor(theme))
    setCreateError('')
    setShowCreate(false)
  }, [theme])

  const createMutation = useMutation({
    mutationFn: () => createTag({ name: createName.trim(), color: createColor }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PORTAL_TAGS_QUERY_KEY })
      resetCreateForm()
    },
    onError: (e: unknown) => setCreateError(userFacingMessageFromUnknown(e)),
  })

  const updateMutation = useMutation({
    mutationFn: (s: EditState) =>
      updateTag(s.id, {
        name: s.name.trim(),
        color: s.color,
        expected_version: s.expected_version,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PORTAL_TAGS_QUERY_KEY })
      setEditState(null)
      setEditError('')
    },
    onError: (e: unknown) => {
      setEditError(userFacingMessageFromUnknown(e))
      if (isApiConflictError(e)) {
        void queryClient.invalidateQueries({ queryKey: PORTAL_TAGS_QUERY_KEY })
      }
    },
  })

  const colorMutation = useMutation({
    mutationFn: ({
      id,
      color,
      expected_version,
    }: {
      id: string
      color: string
      expected_version: number
    }) => updateTag(id, { color, expected_version }),
    onSuccess: (data, vars) => {
      void queryClient.invalidateQueries({ queryKey: PORTAL_TAGS_QUERY_KEY })
      setEditState((s) =>
        s?.id === vars.id
          ? { ...s, color: vars.color, expected_version: data.version }
          : s,
      )
    },
    onError: (e: unknown) => {
      notifyToast(userFacingMessageFromUnknown(e))
      if (isApiConflictError(e)) {
        void queryClient.invalidateQueries({ queryKey: PORTAL_TAGS_QUERY_KEY })
      }
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteTag(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PORTAL_TAGS_QUERY_KEY })
      setTagPendingDelete(null)
      setDeleteError('')
    },
    onError: (e: unknown) => {
      setDeleteError(userFacingMessageFromUnknown(e))
    },
  })

  const startEdit = useCallback((tag: PortalTag) => {
    setTagPendingDelete(null)
    setEditState({ id: tag.id, name: tag.name, color: tag.color, expected_version: tag.version })
    setEditError('')
  }, [])

  const handleCreateSubmit = useCallback(() => {
    if (!createName.trim()) return
    setCreateError('')
    createMutation.mutate()
  }, [createMutation, createName])

  const handleSaveEdit = useCallback(() => {
    if (!editState) return
    setEditError('')
    updateMutation.mutate(editState)
  }, [editState, updateMutation])

  const handleQuickColorChange = useCallback(
    (tag: PortalTag, color: string) => {
      colorMutation.mutate({ id: tag.id, color, expected_version: tag.version })
    },
    [colorMutation],
  )

  const handleViewLinksFromDelete = useCallback(() => {
    if (!tagPendingDelete) return
    const tag = tagPendingDelete
    setTagPendingDelete(null)
    setDeleteError('')
    openUsageDrawer(tag)
  }, [tagPendingDelete, openUsageDrawer])

  const cancelEdit = useCallback(() => {
    setEditState(null)
    setEditError('')
  }, [])

  const requestDelete = useCallback((tag: PortalTag) => {
    setEditState(null)
    setEditError('')
    setTagPendingDelete(tag)
    setDeleteError('')
  }, [])

  const cancelDelete = useCallback(() => {
    setTagPendingDelete(null)
    setDeleteError('')
  }, [])

  const confirmDelete = useCallback(() => {
    if (!tagPendingDelete) return
    deleteMutation.mutate(tagPendingDelete.id)
  }, [deleteMutation, tagPendingDelete])

  const setEditName = useCallback((name: string) => {
    setEditState((s) => (s ? { ...s, name } : s))
  }, [])

  const setEditColor = useCallback((color: string) => {
    setEditState((s) => (s ? { ...s, color } : s))
  }, [])

  return {
    canManageTags,
    tags,
    isLoading,
    isError,
    error,
    showCreate,
    setShowCreate,
    createName,
    setCreateName,
    createColor,
    setCreateColor,
    createError,
    createPending: createMutation.isPending,
    handleCreateSubmit,
    resetCreateForm,
    editState,
    editError,
    setEditName,
    setEditColor,
    updatePending: updateMutation.isPending,
    startEdit,
    handleSaveEdit,
    cancelEdit,
    requestDelete,
    handleQuickColorChange,
    openUsageDrawer,
    tagPendingDelete,
    deleteError,
    deletePending: deleteMutation.isPending,
    confirmDelete,
    cancelDelete,
    handleViewLinksFromDelete,
    usageTag,
    usageDrawerOpen: usageDrawer.open,
    usageDrawerEntered: usageDrawer.entered,
    usagesQuery,
    closeUsageDrawer,
    handleUsageDrawerTransitionEnd,
  }
}

export type TagsPageController = ReturnType<typeof useTagsPageController>
