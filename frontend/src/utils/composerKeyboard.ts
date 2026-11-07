import type { KeyboardEvent } from 'react'

export function handleComposerEnterSubmit(
  e: KeyboardEvent<HTMLTextAreaElement>,
  canSubmit: boolean,
  submit: () => void,
): boolean {
  if (e.key !== 'Enter' || e.shiftKey) {
    return false
  }
  e.preventDefault()
  e.stopPropagation()
  if (canSubmit) {
    submit()
  }
  return true
}
