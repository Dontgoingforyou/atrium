// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import {
  collabCaretColorFromSub,
  documentCollabTicketPath,
  documentCollabWsUrl,
  isDocumentCollabPersistActive,
  isSameRichTextCollaboration,
  shouldSeedCollabEditorFromLocalHtml,
} from '@/utils/documents/documentCollab'

describe('documentCollab helpers', () => {
  it('строит path тикета', () => {
    expect(documentCollabTicketPath('abc-1')).toBe('/portal/documents/abc-1/collab-ws-ticket')
  })

  it('encodeURIComponent в path', () => {
    expect(documentCollabTicketPath('a/b')).toBe('/portal/documents/a%2Fb/collab-ws-ticket')
  })

  it('ws url same-origin /collab', () => {
    expect(documentCollabWsUrl()).toMatch(/^wss?:\/\/.+\/collab$/)
  })

  it('стабильный цвет из sub', () => {
    const a = collabCaretColorFromSub('user-1')
    const b = collabCaretColorFromSub('user-1')
    const c = collabCaretColorFromSub('user-2')
    expect(a).toBe(b)
    expect(a).not.toBe(c)
    expect(a).toMatch(/^hsl\(\d+ 70% 45%\)$/)
  })

  it('persist active только при ready', () => {
    expect(isDocumentCollabPersistActive('ready')).toBe(true)
    expect(isDocumentCollabPersistActive('connecting')).toBe(false)
    expect(isDocumentCollabPersistActive('unavailable')).toBe(false)
    expect(isDocumentCollabPersistActive('idle')).toBe(false)
  })

  it('тот же ydoc — та же collab-сессия, новый объект не считается сменой', () => {
    const ydoc = { id: 1 }
    const prev = { ydoc }
    const next = { ydoc }
    const other = { ydoc: { id: 2 } }
    expect(isSameRichTextCollaboration(prev, next)).toBe(true)
    expect(isSameRichTextCollaboration(prev, other)).toBe(false)
    expect(isSameRichTextCollaboration(null, prev)).toBe(false)
  })

  it('seed collab, если локальный HTML отличается', () => {
    expect(shouldSeedCollabEditorFromLocalHtml('<p>черновик</p>', '<p>сервер</p>')).toBe(true)
    expect(shouldSeedCollabEditorFromLocalHtml('<p>то же</p>', '<p>то же</p>')).toBe(false)
    expect(shouldSeedCollabEditorFromLocalHtml('  <p>x</p>  ', '<p>x</p>')).toBe(false)
  })
})
