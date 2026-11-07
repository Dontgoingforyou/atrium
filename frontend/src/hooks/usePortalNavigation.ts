import { useQuery } from '@tanstack/react-query'

import { fetchNavigationTree } from '../api/navigationApi'
import { PORTAL_NAVIGATION_TREE_QUERY_KEY } from '../api/queryKeys'
import { useAuthStore } from '../store/authStore'

export function useNavigationTreeQuery() {
  const accessToken = useAuthStore((s) => s.accessToken)
  return useQuery({
    queryKey: PORTAL_NAVIGATION_TREE_QUERY_KEY,
    queryFn: () => fetchNavigationTree(),
    enabled: Boolean(accessToken),
    staleTime: 60_000,
    refetchOnWindowFocus: true,
    retry: 2,
  })
}
