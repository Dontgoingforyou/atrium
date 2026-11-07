import { useEffect, useState } from 'react'

export const NARROW_LAYOUT_QUERY = '(max-width: 768px)'

export function useNarrowViewport(): boolean {
  const [narrow, setNarrow] = useState(() => window.matchMedia(NARROW_LAYOUT_QUERY).matches)

  useEffect(() => {
    const media = window.matchMedia(NARROW_LAYOUT_QUERY)
    const apply = () => setNarrow(media.matches)
    apply()
    media.addEventListener('change', apply)
    return () => media.removeEventListener('change', apply)
  }, [])

  return narrow
}
