import { getSchema } from '@tiptap/core'
import { generateHTML, generateJSON } from '@tiptap/html'
import { prosemirrorJSONToYDoc, yDocToProsemirrorJSON } from '@tiptap/y-tiptap'
import * as Y from 'yjs'

import { tiptapExtensions } from './schema.mjs'

const Y_FRAGMENT = 'default'

const schema = getSchema(tiptapExtensions)

function collectTypes(node, types = new Set()) {
  if (node?.type) types.add(node.type)
  if (Array.isArray(node?.content)) {
    for (const child of node.content) collectTypes(child, types)
  }
  if (Array.isArray(node?.marks)) {
    for (const mark of node.marks) types.add(mark.type)
  }
  return types
}

/** HTML → JSON редактора той же схемой, что у SPA. */
export function htmlToEditorJson(html) {
  return generateJSON(html, tiptapExtensions)
}

export function jsonHasType(json, typeName) {
  return collectTypes(json).has(typeName)
}

export function htmlToYUpdate(html) {
  const json = htmlToEditorJson(html)
  if (/<table[\s>]/i.test(html) && !jsonHasType(json, 'table')) {
    console.warn('collab hydrate: в HTML есть <table>, схема его отбросила')
  }
  if (/<mark[\s>]/i.test(html) && !jsonHasType(json, 'highlight')) {
    console.warn('collab hydrate: в HTML есть <mark>, схема его отбросила')
  }
  const ydoc = prosemirrorJSONToYDoc(schema, json, Y_FRAGMENT)
  return Y.encodeStateAsUpdate(ydoc)
}

export function ydocToHtml(document) {
  const json = yDocToProsemirrorJSON(document, Y_FRAGMENT)
  return generateHTML(json, tiptapExtensions)
}
