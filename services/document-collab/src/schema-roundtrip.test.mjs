import assert from 'node:assert/strict'
import { test } from 'node:test'

import * as Y from 'yjs'

import { htmlToEditorJson, htmlToYUpdate, jsonHasType, ydocToHtml } from './html-yjs.mjs'

const TABLE_WITH_MARK =
  '<table class="portal-rich-table"><tbody>' +
  '<tr><th><p>Имя</p></th><th><p>Стек</p></th></tr>' +
  '<tr><td><p>Родион Х.</p></td>' +
  '<td><p><mark data-color="#fef08a" style="background-color: #fef08a">Golang</mark></p></td></tr>' +
  '</tbody></table>'

function htmlThroughYdoc(html) {
  const ydoc = new Y.Doc()
  Y.applyUpdate(ydoc, htmlToYUpdate(html))
  return ydocToHtml(ydoc)
}

test('таблица не распадается в абзацы при HTML→Y→HTML', () => {
  const json = htmlToEditorJson(TABLE_WITH_MARK)
  assert.equal(jsonHasType(json, 'table'), true)
  assert.equal(jsonHasType(json, 'tableCell'), true)

  const html = htmlThroughYdoc(TABLE_WITH_MARK)
  assert.match(html, /<table/)
  assert.match(html, /Родион Х\./)
  assert.doesNotMatch(html, /^<p>Имя<\/p>/)
})

test('подсветка (овалы) сохраняется при HTML→Y→HTML', () => {
  const json = htmlToEditorJson(TABLE_WITH_MARK)
  assert.equal(jsonHasType(json, 'highlight'), true)

  const html = htmlThroughYdoc(TABLE_WITH_MARK)
  assert.match(html, /<mark/)
  assert.match(html, /Golang/)
  assert.match(html, /background-color/)
})

test('заголовок buildin-toggle сохраняется при HTML→Y→HTML', () => {
  const src =
    '<details class="buildin-toggle"><summary>ЧТО</summary><div class="buildin-toggle-body"><p>тело</p></div></details>'
  const json = htmlToEditorJson(src)
  assert.equal(jsonHasType(json, 'buildinToggle'), true)
  const html = htmlThroughYdoc(src)
  assert.match(html, /<summary>ЧТО<\/summary>/)
  assert.match(html, /тело/)
})
