import { useCallback, useEffect, useLayoutEffect, useRef, useSyncExternalStore } from 'react'

import type { ChatWsEvent } from '@/utils/chat/chatWs'
import {
  formatEphemeralHint,
  peersToEphemeralList,
  type EphemeralPeer,
} from '@/utils/chat/chatEphemeral'
import type { ChatWsSendJson } from './useChatWebSocket'

/** Запас, если keepalive не дошёл; при активном наборе peer обновляется чаще. */
const PEER_TTL_MS = 10_000
const TICK_MS = 800

type PeerState = {
  displayName: string
  typing: boolean
  voice: boolean
  expiresAt: number
}

const EMPTY_PEERS: EphemeralPeer[] = []

type Store = {
  peers: Map<string, PeerState>
  version: number
  /** Кэш для useSyncExternalStore — стабильная ссылка между рендерами. */
  snapshot: EphemeralPeer[]
}

function refreshSnapshot(store: Store) {
  store.snapshot = store.peers.size === 0 ? EMPTY_PEERS : peersToEphemeralList(store.peers)
}

function createStore(): Store {
  return { peers: new Map(), version: 0, snapshot: EMPTY_PEERS }
}

function bump(store: Store) {
  store.version += 1
  refreshSnapshot(store)
}

function pruneExpired(store: Store, now: number): boolean {
  let changed = false
  for (const [sub, p] of store.peers) {
    if (p.expiresAt < now && (p.typing || p.voice)) {
      store.peers.delete(sub)
      changed = true
    }
  }
  return changed
}

/** Состояние «печатает / записывает голос» по WS; отправка эфемерных событий. */
export function useChatEphemeral(chatId: string | null, currentUserSub: string | null) {
  const sendRef = useRef<ChatWsSendJson | null>(null)
  const lastSentRef = useRef<Record<string, boolean>>({})
  const storeRef = useRef<Store>(createStore())
  const listenersRef = useRef(new Set<() => void>())

  const subscribe = useCallback((onStoreChange: () => void) => {
    listenersRef.current.add(onStoreChange)
    return () => listenersRef.current.delete(onStoreChange)
  }, [])

  const getPeersSnapshot = useCallback((): EphemeralPeer[] => storeRef.current.snapshot, [])
  const peers = useSyncExternalStore(subscribe, getPeersSnapshot, () => EMPTY_PEERS)

  const notifyListeners = useCallback(() => {
    for (const l of listenersRef.current) {
      l()
    }
  }, [])

  const bindSendEphemeral = useCallback((send: ChatWsSendJson) => {
    sendRef.current = send
  }, [])

  const resetStore = useCallback(() => {
    storeRef.current = createStore()
    bump(storeRef.current)
    notifyListeners()
  }, [notifyListeners])

  useLayoutEffect(() => {
    // Не обнуляем send на смене chatId здесь — onConnection перепривяжет.
    // Иначе гонка с async WS: typing/emoji_pong уходят в никуда.
    lastSentRef.current = {}
  }, [chatId])

  useEffect(() => {
    resetStore()
  }, [chatId, resetStore])

  useEffect(() => {
    if (!chatId) return
    const tick = () => {
      if (document.visibilityState === 'hidden') return
      const store = storeRef.current
      if (pruneExpired(store, Date.now())) {
        bump(store)
        notifyListeners()
      }
    }
    const id = window.setInterval(tick, TICK_MS)
    return () => window.clearInterval(id)
  }, [chatId, notifyListeners])

  const notifyEphemeral = useCallback((event: 'typing' | 'voice_recording', active: boolean) => {
    if (!active) {
      if (lastSentRef.current[event] === false) return
      lastSentRef.current[event] = false
    } else {
      if (document.visibilityState === 'hidden') return
      lastSentRef.current[event] = true
    }
    sendRef.current?.({ event, active })
  }, [])

  const applyPeerEvent = useCallback(
    (e: Extract<ChatWsEvent, { type: 'typing' } | { type: 'voice_recording' }>) => {
      if (!e.user_sub || e.user_sub === currentUserSub) return

      const store = storeRef.current
      const next = new Map(store.peers)
      const cur = next.get(e.user_sub) ?? {
        displayName: e.display_name,
        typing: false,
        voice: false,
        expiresAt: 0,
      }
      const updated: PeerState = {
        ...cur,
        displayName: e.display_name || cur.displayName,
        typing: e.type === 'typing' ? e.active : cur.typing,
        voice: e.type === 'voice_recording' ? e.active : cur.voice,
        expiresAt: e.active ? Date.now() + PEER_TTL_MS : cur.expiresAt,
      }
      if (!updated.typing && !updated.voice) {
        next.delete(e.user_sub)
      } else {
        next.set(e.user_sub, updated)
      }
      store.peers = next
      bump(store)
      notifyListeners()
    },
    [currentUserSub, notifyListeners],
  )

  const handleWsEvent = useCallback(
    (e: ChatWsEvent) => {
      if (e.type !== 'typing' && e.type !== 'voice_recording') return false
      applyPeerEvent(e)
      return true
    },
    [applyPeerEvent],
  )

  const ephemeralHint = formatEphemeralHint(peers)

  return { ephemeralHint, ephemeralPeers: peers, notifyEphemeral, handleWsEvent, bindSendEphemeral }
}
