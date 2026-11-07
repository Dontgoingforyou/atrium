import { useEffect } from 'react'
import { useNavigate } from 'react-router'

import { registerSpaNavigate } from '@/utils/spaNavigate'

export function SpaNavigateRegistrar() {
  const navigate = useNavigate()
  useEffect(() => {
    registerSpaNavigate((to) => {
      navigate(to)
    })
    return () => registerSpaNavigate(null)
  }, [navigate])
  return null
}
