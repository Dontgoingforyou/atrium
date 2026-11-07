import type { ReactNode } from 'react'
import { Navigate } from 'react-router'

import { useAuthStore } from '../../store/authStore'
import { isUserManagerOrAdmin } from '@/domain/auth/authRoles'

export function RequireManagerOrAdmin({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user)
  if (!user || !isUserManagerOrAdmin(user)) {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}
