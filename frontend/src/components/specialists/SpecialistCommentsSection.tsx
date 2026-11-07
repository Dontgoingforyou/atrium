import { useQueryClient } from '@tanstack/react-query'

import {
  createSpecialistNote,
  deleteSpecialistNote,
  listSpecialistNotes,
  patchSpecialistNote,
  uploadSpecialistNoteMedia,
} from '../../api/specialists/specialistsApi'
import { useSearchHighlightQuery } from '../../hooks/useSearchHighlightQuery'
import { specialistNotesQueryKey } from '../../pages/specialists/specialistQueryKeys'
import type { SpecialistNote } from '../../types/specialist'
import type { ThreadComment } from '../../types/commentThread'
import { invalidatePortalSearchQueries } from '@/utils/search/invalidatePortalSearch'
import { PortalCommentThread } from '../comments/PortalCommentThread'

function noteToThread(note: SpecialistNote): ThreadComment {
  return {
    id: note.id,
    parent_id: note.parent_id,
    author_sub: note.author_sub,
    author_display_name: note.author_display_name,
    body: note.body,
    mentions: note.mentions ?? [],
    version: note.version ?? 1,
    created_at: note.created_at,
    updated_at: note.updated_at,
    replies: (note.replies ?? []).map(noteToThread),
    media: note.media ?? [],
  }
}

type Props = {
  specialistSub: string
  currentUserSub: string
  isAdmin: boolean
  canWrite: boolean
}

export function SpecialistCommentsSection({ specialistSub, currentUserSub, isAdmin, canWrite }: Props) {
  const queryClient = useQueryClient()
  const highlightQuery = useSearchHighlightQuery()
  const notesQk = specialistNotesQueryKey(specialistSub)

  return (
    <PortalCommentThread
      queryKey={notesQk}
      list={async () => (await listSpecialistNotes(specialistSub)).map(noteToThread)}
      create={async (body) => {
        const created = await createSpecialistNote(specialistSub, body)
        invalidatePortalSearchQueries(queryClient)
        return created
      }}
      remove={async (id) => {
        await deleteSpecialistNote(specialistSub, id)
        invalidatePortalSearchQueries(queryClient)
      }}
      update={async (id, body) => {
        const updated = await patchSpecialistNote(specialistSub, id, body)
        invalidatePortalSearchQueries(queryClient)
        return updated
      }}
      uploadImage={(file) => uploadSpecialistNoteMedia(specialistSub, file)}
      currentUserSub={currentUserSub}
      resolveUserSub={(sub) => sub}
      canDeleteAny={isAdmin}
      canCompose={canWrite}
      highlightQuery={highlightQuery}
    />
  )
}
