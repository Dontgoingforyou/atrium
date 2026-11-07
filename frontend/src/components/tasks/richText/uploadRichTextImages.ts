import type { Editor } from '@tiptap/react'
import { Selection } from '@tiptap/pm/state'

import { uploadDocumentRichMedia, uploadTaskRichMedia } from '@/api/richMediaApi'
import { mapWithConcurrency } from '@/utils/uploadConcurrency'

import { insertUploadedRichMediaAt } from './extensions/tiptapImageExtension'
import type { RichTextEntityType } from './RichTextEditor'

export const RICH_TEXT_IMAGE_UPLOAD_CONCURRENCY = 4

export async function uploadAndInsertRichTextImages(
  editor: Editor,
  files: File[],
  entityType: RichTextEntityType,
  entityId: string,
): Promise<void> {
  const imageFiles = files.filter((f) => f.type.startsWith('image/'))
  if (imageFiles.length === 0) return

  let insertPos = editor.state.selection.to
  await mapWithConcurrency(imageFiles, RICH_TEXT_IMAGE_UPLOAD_CONCURRENCY, async (file) => {
    const media =
      entityType === 'task'
        ? await uploadTaskRichMedia(entityId, file)
        : await uploadDocumentRichMedia(entityId, file)
    insertPos = insertUploadedRichMediaAt(editor, insertPos, media.id)
  })
  const clampedPos = Math.min(insertPos, editor.state.doc.content.size)
  editor.commands.command(({ tr }) => {
    tr.setSelection(Selection.near(tr.doc.resolve(clampedPos), 1))
    return true
  })
  editor.commands.focus()
}

export function imageFilesFromClipboard(data: DataTransfer): File[] {
  return Array.from(data.items)
    .filter((item) => item.kind === 'file' && item.type.startsWith('image/'))
    .map((item) => item.getAsFile())
    .filter((f): f is File => f !== null)
}
