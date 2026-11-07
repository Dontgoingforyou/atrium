import { useCallback, useEffect, useRef, useState, type MutableRefObject } from 'react'

import type { ChatWsSendJson } from './useChatWebSocket'
import type { ChatWsEvent } from '@/utils/chat/chatWs'
import { shouldAcceptPeerInviteWhileWaiting } from '@/utils/chat/emojiPongMatch'
import { isEmojiPongEventName } from '@/utils/chat/emojiPongWs'
import type { EmojiPongWsEvent } from '@/utils/chat/emojiPongWs'

export type EmojiPongOnlineRole = 'host' | 'guest'

export type EmojiPongIncomingInvite = {
  sessionId: string
  emoji: string
  fromSub: string
  fromName: string
}

export type EmojiPongLiveSession = {
  sessionId: string
  role: EmojiPongOnlineRole
  emoji: string
  peerSub: string
  peerName: string
  /** true после accept; host может слать state, guest — paddle */
  playing: boolean
}

/** Высокочастотный снимок для RAF (без React setState). */
export type EmojiPongNetSnapshot = {
  ball_x: number
  ball_y: number
  vx: number
  vy: number
  host_paddle_x: number
  guest_paddle_x: number
  host_score: number
  guest_score: number
  finished: boolean
  receivedAt: number
}

export type EmojiPongNetBus = {
  /** Ракетка гостя → host (только X). */
  remotePaddleX: number
  /** Последний state от host → guest. */
  snapshot: EmojiPongNetSnapshot | null
}

type Args = {
  chatId: string | null
  currentUserSub: string | null
  isDirect: boolean
}

function emptyNet(): EmojiPongNetBus {
  return { remotePaddleX: 0.5, snapshot: null }
}

/**
 * Онлайн emoji-pong поверх WS чата.
 * Мяч/ракетки — только в netRef (без ререндеров); счёт/сессия — React state.
 */
export function useEmojiPongOnline({ chatId, currentUserSub, isDirect }: Args) {
  const sendRef = useRef<ChatWsSendJson | null>(null)
  const liveSessionRef = useRef<EmojiPongLiveSession | null>(null)
  const incomingInviteRef = useRef<EmojiPongIncomingInvite | null>(null)
  const netRef = useRef<EmojiPongNetBus>(emptyNet())
  const lastScoreKeyRef = useRef('')

  const [incomingInvite, setIncomingInvite] = useState<EmojiPongIncomingInvite | null>(null)
  const [liveSession, setLiveSession] = useState<EmojiPongLiveSession | null>(null)
  const [waitingForAccept, setWaitingForAccept] = useState(false)
  /** Редкий тик: смена счёта / finished — чтобы UI результат обновился. */
  const [matchTick, setMatchTick] = useState(0)
  const pendingInviteSessionRef = useRef<string | null>(null)

  // Сброс при смене чата — во время рендера (React docs: «Adjusting state when a
  // prop changes»), без эффекта, чтобы не ловить react-hooks/set-state-in-effect.
  const [prevChatId, setPrevChatId] = useState(chatId)
  if (chatId !== prevChatId) {
    setPrevChatId(chatId)
    setIncomingInvite(null)
    setLiveSession(null)
    setWaitingForAccept(false)
  }

  useEffect(() => {
    liveSessionRef.current = liveSession
  }, [liveSession])

  useEffect(() => {
    incomingInviteRef.current = incomingInvite
  }, [incomingInvite])

  const bindSend = useCallback((send: ChatWsSendJson) => {
    sendRef.current = send
  }, [])

  useEffect(() => {
    netRef.current = emptyNet()
    lastScoreKeyRef.current = ''
    incomingInviteRef.current = null
    pendingInviteSessionRef.current = null
  }, [chatId])

  const send = useCallback((payload: Record<string, unknown>): boolean => {
    if (!sendRef.current) return false
    sendRef.current(payload)
    return true
  }, [])

  const clearSession = useCallback(() => {
    netRef.current = emptyNet()
    lastScoreKeyRef.current = ''
    setLiveSession(null)
    setWaitingForAccept(false)
    setIncomingInvite(null)
    incomingInviteRef.current = null
    pendingInviteSessionRef.current = null
  }, [])

  const cancelOnline = useCallback(() => {
    const pending = pendingInviteSessionRef.current
    if (pending) {
      send({ event: 'emoji_pong_decline', session_id: pending })
    }
    const invite = incomingInviteRef.current
    if (invite && invite.sessionId !== pending) {
      send({ event: 'emoji_pong_decline', session_id: invite.sessionId })
    }
    const live = liveSessionRef.current
    if (live?.playing) {
      send({
        event: 'emoji_pong_end',
        session_id: live.sessionId,
        host_score: 0,
        guest_score: 0,
      })
    }
    clearSession()
  }, [clearSession, send])

  const becomeGuest = useCallback(
    (invite: EmojiPongIncomingInvite): boolean => {
      const ok = send({
        event: 'emoji_pong_accept',
        session_id: invite.sessionId,
      })
      if (!ok) return false
      pendingInviteSessionRef.current = null
      setWaitingForAccept(false)
      setIncomingInvite(null)
      incomingInviteRef.current = null
      netRef.current = emptyNet()
      setLiveSession({
        sessionId: invite.sessionId,
        role: 'guest',
        emoji: invite.emoji,
        peerSub: invite.fromSub,
        peerName: invite.fromName,
        playing: true,
      })
      return true
    },
    [send],
  )

  const invitePeer = useCallback(
    (emoji: string) => {
      if (!isDirect || !currentUserSub) return null
      const existing = incomingInviteRef.current
      if (existing) {
        return becomeGuest(existing) ? existing.sessionId : null
      }
      const sessionId = crypto.randomUUID()
      pendingInviteSessionRef.current = sessionId
      setWaitingForAccept(true)
      setIncomingInvite(null)
      incomingInviteRef.current = null
      netRef.current = emptyNet()
      setLiveSession({
        sessionId,
        role: 'host',
        emoji,
        peerSub: '',
        peerName: '',
        playing: false,
      })
      send({
        event: 'emoji_pong_invite',
        session_id: sessionId,
        emoji,
      })
      return sessionId
    },
    [becomeGuest, currentUserSub, isDirect, send],
  )

  const acceptInvite = useCallback(() => {
    const invite = incomingInviteRef.current
    if (!invite || !currentUserSub) return
    becomeGuest(invite)
  }, [becomeGuest, currentUserSub])

  const declineInvite = useCallback(() => {
    const invite = incomingInviteRef.current
    if (!invite) return
    send({
      event: 'emoji_pong_decline',
      session_id: invite.sessionId,
    })
    setIncomingInvite(null)
    incomingInviteRef.current = null
  }, [send])

  const sendPaddle = useCallback(
    (paddleX: number) => {
      const live = liveSessionRef.current
      if (!live?.playing) return
      send({
        event: 'emoji_pong_paddle',
        session_id: live.sessionId,
        paddle_x: paddleX,
      })
    },
    [send],
  )

  const sendState = useCallback(
    (state: Omit<EmojiPongNetSnapshot, 'receivedAt'>) => {
      const live = liveSessionRef.current
      if (!live?.playing || live.role !== 'host') return
      send({
        event: 'emoji_pong_state',
        session_id: live.sessionId,
        ...state,
      })
    },
    [send],
  )

  const sendEnd = useCallback(
    (hostScore: number, guestScore: number) => {
      const live = liveSessionRef.current
      if (!live) return
      send({
        event: 'emoji_pong_end',
        session_id: live.sessionId,
        host_score: hostScore,
        guest_score: guestScore,
      })
    },
    [send],
  )

  useEffect(() => {
    if (!waitingForAccept || !liveSession || liveSession.playing) return
    const sessionId = liveSession.sessionId
    const emoji = liveSession.emoji
    const tick = () => {
      send({
        event: 'emoji_pong_invite',
        session_id: sessionId,
        emoji,
      })
    }
    const id = window.setInterval(tick, 2000)
    return () => window.clearInterval(id)
  }, [liveSession, send, waitingForAccept])

  const bumpMatchUi = useCallback((hostScore: number, guestScore: number, finished: boolean) => {
    const key = `${hostScore}:${guestScore}:${finished ? 1 : 0}`
    if (key === lastScoreKeyRef.current) return
    lastScoreKeyRef.current = key
    setMatchTick((n) => n + 1)
  }, [])

  const handleWsEvent = useCallback(
    (e: ChatWsEvent): boolean => {
      if (!isEmojiPongEventName(e.type)) return false
      const ev = e as EmojiPongWsEvent
      if (!currentUserSub || ev.user_sub === currentUserSub) return true

      if (ev.type === 'emoji_pong_invite') {
        if (!isDirect) return true
        const invite: EmojiPongIncomingInvite = {
          sessionId: ev.session_id,
          emoji: ev.emoji,
          fromSub: ev.user_sub,
          fromName: ev.display_name || ev.user_sub.slice(0, 8),
        }
        const pending = pendingInviteSessionRef.current
        if (pending && shouldAcceptPeerInviteWhileWaiting(pending, invite.sessionId)) {
          becomeGuest(invite)
          return true
        }
        setIncomingInvite(invite)
        incomingInviteRef.current = invite
        return true
      }

      if (ev.type === 'emoji_pong_accept') {
        if (pendingInviteSessionRef.current !== ev.session_id) return true
        pendingInviteSessionRef.current = null
        setWaitingForAccept(false)
        setIncomingInvite(null)
        incomingInviteRef.current = null
        setLiveSession((prev) =>
          prev && prev.sessionId === ev.session_id
            ? {
                ...prev,
                peerSub: ev.user_sub,
                peerName: ev.display_name || ev.user_sub.slice(0, 8),
                playing: true,
              }
            : prev,
        )
        return true
      }

      if (ev.type === 'emoji_pong_decline') {
        if (pendingInviteSessionRef.current === ev.session_id) {
          clearSession()
          return true
        }
        if (incomingInviteRef.current?.sessionId === ev.session_id) {
          setIncomingInvite(null)
          incomingInviteRef.current = null
        }
        return true
      }

      if (ev.type === 'emoji_pong_paddle') {
        if (
          liveSessionRef.current?.playing
          && liveSessionRef.current.sessionId === ev.session_id
          && liveSessionRef.current.role === 'host'
        ) {
          netRef.current.remotePaddleX = ev.paddle_x
        }
        return true
      }

      if (ev.type === 'emoji_pong_state') {
        if (
          liveSessionRef.current?.playing
          && liveSessionRef.current.sessionId === ev.session_id
          && liveSessionRef.current.role === 'guest'
        ) {
          netRef.current.snapshot = {
            ball_x: ev.ball_x,
            ball_y: ev.ball_y,
            vx: ev.vx,
            vy: ev.vy,
            host_paddle_x: ev.host_paddle_x,
            guest_paddle_x: ev.guest_paddle_x,
            host_score: ev.host_score,
            guest_score: ev.guest_score,
            finished: ev.finished,
            receivedAt: performance.now(),
          }
          bumpMatchUi(ev.host_score, ev.guest_score, ev.finished)
        }
        return true
      }

      if (ev.type === 'emoji_pong_end') {
        if (liveSessionRef.current?.sessionId === ev.session_id) {
          const prev = netRef.current.snapshot
          netRef.current.snapshot = {
            ball_x: prev?.ball_x ?? 0.5,
            ball_y: prev?.ball_y ?? 1,
            vx: 0,
            vy: 0,
            host_paddle_x: prev?.host_paddle_x ?? 0.5,
            guest_paddle_x: prev?.guest_paddle_x ?? 0.5,
            host_score: ev.host_score,
            guest_score: ev.guest_score,
            finished: true,
            receivedAt: performance.now(),
          }
          bumpMatchUi(ev.host_score, ev.guest_score, true)
        }
        return true
      }

      return true
    },
    [becomeGuest, bumpMatchUi, clearSession, currentUserSub, isDirect],
  )

  return {
    bindSend,
    handleWsEvent,
    incomingInvite,
    acceptInvite,
    declineInvite,
    invitePeer,
    liveSession,
    waitingForAccept,
    /** Высокочастотный канал — читать только из RAF / physics. */
    netRef: netRef as MutableRefObject<EmojiPongNetBus>,
    matchTick,
    sendPaddle,
    sendState,
    sendEnd,
    clearSession,
    cancelOnline,
  }
}
