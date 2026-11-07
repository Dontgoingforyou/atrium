import { useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { addFavorite, listFavorites, removeFavorite } from '../api/favorites/favoritesApi'
import { PORTAL_FAVORITES_QUERY_KEY } from '../api/queryKeys'
import { userFacingMessageFromUnknown } from '../utils/apiUserMessage'
import { useNotifyToast } from './useNotifyToast'

export function useDocumentFavorite(documentId: string) {
  const queryClient = useQueryClient()
  const notifyToast = useNotifyToast()

  const { data: favorites, isError: isListError, error: listError } = useQuery({
    queryKey: PORTAL_FAVORITES_QUERY_KEY,
    queryFn: listFavorites,
  })

  const existing = useMemo(
    () => favorites?.find((f) => f.target_type === 'document' && f.target_id === documentId),
    [favorites, documentId],
  )

  const addMutation = useMutation({
    mutationFn: () => addFavorite({ target_type: 'document', target_id: documentId }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PORTAL_FAVORITES_QUERY_KEY })
      notifyToast('Документ добавлен в избранное')
    },
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e)),
  })

  const removeMutation = useMutation({
    mutationFn: () => removeFavorite(existing!.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PORTAL_FAVORITES_QUERY_KEY })
      notifyToast('Документ убран из избранного')
    },
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e)),
  })

  const isPending = addMutation.isPending || removeMutation.isPending
  const mutationError = addMutation.error ?? removeMutation.error

  function toggleFavorite(): void {
    if (isPending) return
    if (existing) {
      removeMutation.mutate()
      return
    }
    addMutation.mutate()
  }

  const error = mutationError ?? (isListError ? listError : null)

  return {
    isFavorite: Boolean(existing),
    isPending,
    isListError,
    error: error ? userFacingMessageFromUnknown(error) : null,
    toggleFavorite,
  }
}
