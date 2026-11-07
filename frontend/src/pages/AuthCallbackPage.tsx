import { useEffect, useState } from 'react'
import type { NavigateFunction } from 'react-router'
import { useNavigate, useSearchParams } from 'react-router'

import { exchangeCodeForTokensOnce, getSpaRedirectUri } from '../api/authApi'
import { useAuthStore } from '../store/authStore'
import { userFacingMessageFromUnknown } from '../utils/apiUserMessage'
import { PKCE_STORAGE_STATE_KEY, PKCE_STORAGE_VERIFIER_KEY } from '../utils/auth/pkce'
import { AUTH_NEXT_PATH_KEY } from '../constants/auth'
import { goToPostLoginPath } from '../utils/auth/postLoginRedirect'
import styles from '@/styles/modules/auth/AuthStatusPage.module.css'

function ExchangeAndRedirect(props: { code: string; verifier: string; navigate: NavigateFunction }) {
  const { code, verifier, navigate } = props
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const data = await exchangeCodeForTokensOnce({
          code,
          redirect_uri: getSpaRedirectUri(),
          code_verifier: verifier,
        })
        localStorage.removeItem(PKCE_STORAGE_STATE_KEY)
        localStorage.removeItem(PKCE_STORAGE_VERIFIER_KEY)
        useAuthStore.getState().setSession({
          access_token: data.access_token,
          expires_in: data.expires_in,
          oauth_client_id: data.oauth_client_id,
          user: data.user,
        })
        const rawNext = sessionStorage.getItem(AUTH_NEXT_PATH_KEY) || data.redirect_after_login || '/'
        sessionStorage.removeItem(AUTH_NEXT_PATH_KEY)
        goToPostLoginPath(rawNext, data.access_token, navigate)
      } catch (e) {
        if (import.meta.env.DEV) console.error(e)
        if (!cancelled) {
          setError(userFacingMessageFromUnknown(e))
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [code, verifier, navigate])

  if (error) {
    return (
      <div className={styles.panel} role="alert">
        Ошибка входа: {error}
      </div>
    )
  }
  return <div className={styles.panel}>Завершение входа…</div>
}

export function AuthCallbackPage() {
  const [search] = useSearchParams()
  const navigate = useNavigate()

  const oauthErr = search.get('error')
  if (oauthErr) {
    return (
      <div className={styles.panel} role="alert">
        Ошибка входа: {search.get('error_description') || oauthErr}
      </div>
    )
  }

  const code = search.get('code')
  const state = search.get('state')
  const savedState = localStorage.getItem(PKCE_STORAGE_STATE_KEY)
  const verifier = localStorage.getItem(PKCE_STORAGE_VERIFIER_KEY)

  if (!code || !state) {
    return (
      <div className={styles.panel} role="alert">
        В адресе нет параметров OAuth. Откройте вход с <a href="/login">/login</a>.
      </div>
    )
  }
  if (!verifier || !savedState) {
    return (
      <div className={styles.panelWide}>
        <p>
          Не найдены данные PKCE. Используйте один и тот же хост при входе (localhost vs 127.0.0.1).
        </p>
        <p>
          <a href="/login">Повторить вход</a>
        </p>
      </div>
    )
  }
  if (state !== savedState) {
    return (
      <div className={styles.panel} role="alert">
        Параметр state не совпадает. Закройте лишние вкладки и откройте <a href="/login">/login</a>.
      </div>
    )
  }

  return <ExchangeAndRedirect code={code} verifier={verifier} navigate={navigate} />
}
