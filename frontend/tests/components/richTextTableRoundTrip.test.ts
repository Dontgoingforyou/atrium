// @vitest-environment jsdom

import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { afterEach, describe, expect, it } from 'vitest'

import { portalTableExtensions } from '../../src/components/tasks/richText/extensions/tiptapTableExtensions'

const SAMPLE_CSV_TABLE =
  '<table class="buildin-csv-import"><thead><tr><th>Партнер</th><th>Город</th></tr></thead><tbody><tr><td>A2SEVEN</td><td>Москва</td></tr></tbody></table>'

describe('richText table HTML round-trip', () => {
  let editor: Editor | null = null

  afterEach(() => {
    editor?.destroy()
    editor = null
  })

  it('preserves buildin-csv-import class after setContent and getHTML', () => {
    editor = new Editor({
      extensions: [
        StarterKit.configure({ heading: false }),
        ...portalTableExtensions,
      ],
      content: SAMPLE_CSV_TABLE,
    })
    const html = editor.getHTML()
    expect(html).toContain('buildin-csv-import')
    expect(html).toContain('A2SEVEN')
    expect(html).toContain('<table')
  })
})
