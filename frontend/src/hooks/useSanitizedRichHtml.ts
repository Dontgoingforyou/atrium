import { useEffect, useState } from 'react'
import { prepareRichHtmlForDisplay } from '../utils/html/sanitizeRichHtml'

/** Асинхронно подставляет presigned URL для rich-media и санитизирует HTML. */
export function useSanitizedRichHtml(html: string | null | undefined): string {
  const [safe, setSafe] = useState('')

  useEffect(() => {
    let cancelled = false
    prepareRichHtmlForDisplay(html?.trim() ?? '').then((out) => {
      if (!cancelled) setSafe(out)
    })
    return () => {
      cancelled = true
    }
  }, [html])

  return safe
}
