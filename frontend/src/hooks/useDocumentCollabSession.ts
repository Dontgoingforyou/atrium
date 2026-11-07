import { useEffect, useRef, useState } from 'react'
import { HocuspocusProvider } from '@hocuspocus/provider'
import * as Y from 'yjs'
import { fetchWsTicket } from '@/hooks/ws/fetchWsTicket'
import {
  DOCUMENT_COLLAB_CONNECT_TIMEOUT_MS,
  collabCaretColorFromSub,
  documentCollabTicketPath,
  documentCollabWsUrl,
} from '@/utils/documents/documentCollab'

export type DocumentCollabSession = {
  ydoc: Y.Doc
  provider: HocuspocusProvider
}

export type DocumentCollabStatus = 'idle' | 'connecting' | 'ready' | 'unavailable'

export function useDocumentCollabSession({
  documentId,
  enabled,
  userSub,
  displayName,
}: {
  documentId: string
  enabled: boolean
  userSub: string | undefined
  displayName: string | undefined
}): { session: DocumentCollabSession | null; status: DocumentCollabStatus } {
  const canConnect = Boolean(enabled && documentId && userSub)
  const connectKey = canConnect ? `${documentId}:${userSub}:${displayName ?? ''}` : null

  const [session, setSession] = useState<DocumentCollabSession | null>(null)
  const [status, setStatus] = useState<DocumentCollabStatus>('idle')
  const genRef = useRef(0)

  const [prevConnectKey, setPrevConnectKey] = useState(connectKey)
  if (connectKey !== prevConnectKey) {
    setPrevConnectKey(connectKey)
    setSession(null)
    setStatus(connectKey ? 'connecting' : 'idle')
  }

  useEffect(() => {
    if (!connectKey || !documentId || !userSub) return

    const gen = ++genRef.current
    let cancelled = false
    let provider: HocuspocusProvider | null = null
    let ydoc: Y.Doc | null = null
    let timeoutId: number | null = null
    let settled = false

    const cleanupSocket = () => {
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId)
        timeoutId = null
      }
      provider?.destroy()
      ydoc?.destroy()
      provider = null
      ydoc = null
    }

    const failUnavailable = () => {
      if (cancelled || gen !== genRef.current || settled) return
      settled = true
      cleanupSocket()
      setSession(null)
      setStatus('unavailable')
    }

    const markReady = () => {
      if (cancelled || gen !== genRef.current || settled || !provider || !ydoc) return
      settled = true
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId)
        timeoutId = null
      }
      setSession({ ydoc, provider })
      setStatus('ready')
    }

    void (async () => {
      const ticket = await fetchWsTicket(documentCollabTicketPath(documentId))
      if (cancelled || gen !== genRef.current) return
      if (!ticket) {
        failUnavailable()
        return
      }
      ydoc = new Y.Doc()
      provider = new HocuspocusProvider({
        url: documentCollabWsUrl(),
        name: documentId,
        document: ydoc,
        token: ticket,
        onSynced: () => {
          markReady()
        },
        onAuthenticationFailed: () => {
          failUnavailable()
        },
        onClose: () => {
          // До первого sync закрытие сокета = сервис недоступен / сеть.
          if (!settled) failUnavailable()
        },
      })
      provider.setAwarenessField('user', {
        name: displayName || userSub,
        color: collabCaretColorFromSub(userSub),
      })
      if (cancelled || gen !== genRef.current) {
        cleanupSocket()
        return
      }
      timeoutId = window.setTimeout(failUnavailable, DOCUMENT_COLLAB_CONNECT_TIMEOUT_MS)
    })()

    return () => {
      cancelled = true
      genRef.current += 1
      cleanupSocket()
    }
  }, [connectKey, documentId, userSub, displayName])

  return { session, status }
}
