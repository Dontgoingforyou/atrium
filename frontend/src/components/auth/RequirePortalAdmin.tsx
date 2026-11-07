import type { ReactNode } from 'react'
import { Navigate } from 'react-router'

import { useAuthStore } from '../../store/authStore'

export function RequirePortalAdmin({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user)
  if (!user || !user.is_portal_admin) {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}
