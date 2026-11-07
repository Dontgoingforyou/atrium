import { useEffect, useState } from 'react'

function readTourActive(): boolean {
  return document.documentElement.getAttribute('data-guided-tour') === '1'
}

export function useGuidedTourActive(): boolean {
  const [active, setActive] = useState(readTourActive)

  useEffect(() => {
    const root = document.documentElement
    const sync = () => setActive(readTourActive())
    const observer = new MutationObserver(sync)
    observer.observe(root, { attributes: true, attributeFilter: ['data-guided-tour'] })
    sync()
    return () => observer.disconnect()
  }, [])

  return active
}
