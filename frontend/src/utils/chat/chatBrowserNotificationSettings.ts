import {
  CHAT_INBOX_BROWSER_OS_ENABLED_KEY,
  CHAT_INBOX_TOAST_ENABLED_KEY,
  CHAT_WEB_PUSH_ENABLED_KEY,
} from '../../constants/chatStorage'

/** Тост внутри SPA при новом сообщении в чате. */
export function getChatInboxToastEnabled(): boolean {
  try {
    const v = localStorage.getItem(CHAT_INBOX_TOAST_ENABLED_KEY)
    if (v === null) return true
    return v === '1'
  } catch {
    return true
  }
}

export function setChatInboxToastEnabled(enabled: boolean): void {
  try {
    localStorage.setItem(CHAT_INBOX_TOAST_ENABLED_KEY, enabled ? '1' : '0')
  } catch {
    /* ignore */
  }
}

/** Дополнительно показывать Notification API, когда вкладка в фоне (нужны разрешение и HTTPS). */
export function getChatInboxBrowserOsEnabled(): boolean {
  try {
    return localStorage.getItem(CHAT_INBOX_BROWSER_OS_ENABLED_KEY) === '1'
  } catch {
    return false
  }
}

export function setChatInboxBrowserOsEnabled(enabled: boolean): void {
  try {
    localStorage.setItem(CHAT_INBOX_BROWSER_OS_ENABLED_KEY, enabled ? '1' : '0')
  } catch {
    /* ignore */
  }
}

export function getChatWebPushSubscriptionOptIn(): boolean {
  try {
    return localStorage.getItem(CHAT_WEB_PUSH_ENABLED_KEY) === '1'
  } catch {
    return false
  }
}

export function setChatWebPushSubscriptionOptIn(enabled: boolean): void {
  try {
    localStorage.setItem(CHAT_WEB_PUSH_ENABLED_KEY, enabled ? '1' : '0')
  } catch {
    /* ignore */
  }
}
