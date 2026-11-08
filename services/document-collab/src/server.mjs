/**
 * Hocuspocus: sync Yjs + authenticate/snapshot через Atrium internal API.
 * Канон в Postgres — HTML body (CAS); Y.Doc — runtime.
 */
import { Server } from '@hocuspocus/server'
import * as Y from 'yjs'

import { htmlToYUpdate, ydocToHtml } from './html-yjs.mjs'

const PORT = Number(process.env.PORT || 1234)
const API_BASE = (process.env.ATRIUM_API_BASE_URL || 'http://api:8000/api/v1').replace(/\/$/, '')
const SERVICE_TOKEN = (process.env.DOCUMENT_COLLAB_SERVICE_TOKEN || '').trim()
const STORE_DEBOUNCE_MS = Number(process.env.DOCUMENT_COLLAB_STORE_DEBOUNCE_MS || 2000)

if (!SERVICE_TOKEN) {
  console.warn('DOCUMENT_COLLAB_SERVICE_TOKEN пуст — authenticate/snapshot будут отклоняться API')
}

function serviceHeaders() {
  return {
    'Content-Type': 'application/json',
    'X-Collab-Service-Token': SERVICE_TOKEN,
  }
}

async function apiJson(path, { method = 'GET', body } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: serviceHeaders(),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  const text = await res.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = { raw: text }
  }
  return { ok: res.ok, status: res.status, data }
}

const server = Server.configure({
  port: PORT,
  debounce: STORE_DEBOUNCE_MS,
  async onAuthenticate({ token, documentName }) {
    if (!token || typeof token !== 'string') {
      throw new Error('Нет collab ticket')
    }
    const { ok, status, data } = await apiJson('/internal/document-collab/authenticate', {
      method: 'POST',
      body: { ticket: token },
    })
    if (!ok) {
      console.warn('collab authenticate failed', status, data)
      throw new Error('Отказ authenticate')
    }
    if (String(data.document_id) !== String(documentName)) {
      throw new Error('documentName ≠ ticket document_id')
    }
    return {
      documentId: data.document_id,
      userSub: data.user_sub,
      displayName: data.display_name || data.user_sub,
      version: data.version,
      body: data.body ?? null,
    }
  },
  async onLoadDocument({ document, context }) {
    if (document.getXmlFragment('default').length > 0) {
      return document
    }
    let body = context?.body ?? null
    let version = context?.version
    if ((body == null || body === '') || version == null) {
      const { ok, data } = await apiJson(`/internal/document-collab/documents/${document.name}`)
      if (ok && data) {
        body = data.body
        version = data.version
        context.version = version
        context.body = body
      }
    }
    if (body && String(body).trim()) {
      try {
        Y.applyUpdate(document, htmlToYUpdate(String(body)))
      } catch (err) {
        console.warn('collab hydrate HTML→Y failed', err)
      }
    }
    return document
  },
  async onStoreDocument({ document, context }) {
    let html
    try {
      html = ydocToHtml(document)
    } catch (err) {
      console.warn('collab export Y→HTML failed', err)
      return
    }
    const expected = context?.version
    if (!expected || !context?.userSub) {
      console.warn('collab store: нет version/userSub в context — пропуск snapshot')
      return
    }
    const { ok, status, data } = await apiJson(
      `/internal/document-collab/documents/${document.name}/snapshot`,
      {
        method: 'POST',
        body: {
          body: html || null,
          expected_version: expected,
          actor_sub: context.userSub,
          actor_display_name: context.displayName || null,
        },
      },
    )
    if (status === 409) {
      const loaded = await apiJson(`/internal/document-collab/documents/${document.name}`)
      if (loaded.ok && loaded.data?.version) {
        context.version = loaded.data.version
      }
      console.warn('collab snapshot conflict 409, version refreshed', context.version)
      return
    }
    if (!ok) {
      console.warn('collab snapshot failed', status, data)
      return
    }
    if (data?.version) {
      context.version = data.version
    }
  },
})

server.listen().then(() => {
  console.log(`document-collab Hocuspocus listening on :${PORT}, API=${API_BASE}`)
})
