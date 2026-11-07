import { FLOATING_DM_WIDGET_SESSION_KEY } from '../../constants/chatStorage'

export type FloatingDmWidgetView = 'list' | 'picker' | 'groupPicker' | 'chat'

export type FloatingDmWidgetSession = {
  view: FloatingDmWidgetView
  activeChatId: string | null
}

export function readFloatingDmWidgetSession(): FloatingDmWidgetSession | null {
  try {
    const raw = sessionStorage.getItem(FLOATING_DM_WIDGET_SESSION_KEY)
    if (!raw) return null
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return null
    const o = parsed as Record<string, unknown>
    const view = o.view
    if (view !== 'list' && view !== 'picker' && view !== 'groupPicker' && view !== 'chat') {
      return null
    }
    const activeChatId = o.activeChatId
    return {
      view,
      activeChatId: typeof activeChatId === 'string' ? activeChatId : null,
    }
  } catch {
    return null
  }
}

export function writeFloatingDmWidgetSession(session: FloatingDmWidgetSession | null): void {
  try {
    if (session === null) {
      sessionStorage.removeItem(FLOATING_DM_WIDGET_SESSION_KEY)
      return
    }
    sessionStorage.setItem(FLOATING_DM_WIDGET_SESSION_KEY, JSON.stringify(session))
  } catch {
    /* ignore quota / private mode */
  }
}
