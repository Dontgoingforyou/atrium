import type { SpecialistNote } from '../../types/specialist'

export function countSpecialistNotes(notes: SpecialistNote[]): number {
  return notes.reduce((sum, note) => sum + 1 + countSpecialistNotes(note.replies ?? []), 0)
}
