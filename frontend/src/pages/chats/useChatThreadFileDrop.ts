import { useCallback, useState } from 'react'

import type { MessageInputHandle } from '../../components/chat/composer/MessageInput'
import { filesFromDataTransfer } from './filesFromDataTransfer'

/** Drag-and-drop файлов на зону чата → MessageInput.addFiles */
export function useChatThreadFileDrop(
  inputRef: React.RefObject<MessageInputHandle | null>,
  disabled: boolean,
) {
  const [dragOver, setDragOver] = useState(false)

  const onDragOver = useCallback(
    (e: React.DragEvent) => {
      if (disabled) return
      e.preventDefault()
      e.dataTransfer.dropEffect = 'copy'
      setDragOver(true)
    },
    [disabled],
  )

  const onDragLeave = useCallback((e: React.DragEvent) => {
    if (e.currentTarget.contains(e.relatedTarget as Node)) return
    setDragOver(false)
  }, [])

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      if (disabled) return
      const files = filesFromDataTransfer(e.dataTransfer)
      if (files.length === 0) return
      inputRef.current?.addFiles(files)
    },
    [disabled, inputRef],
  )

  return { dragOver, onDragOver, onDragLeave, onDrop }
}
