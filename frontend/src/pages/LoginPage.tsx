import { type FormEvent, useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'

import { getSpaRedirectUri, loginWithPassword } from '../api/authApi'
import { silentRefreshAccessToken } from '../api/rawClient'
import { useAuthStore } from '../store/authStore'
import { AUTH_NEXT_PATH_KEY } from '../constants/auth'
import { userFacingMessageFromUnknown } from '../utils/apiUserMessage'
import { resolveLoginNextQueryParam } from '../utils/auth/authNextPath'
import { goToPostLoginPath } from '../utils/auth/postLoginRedirect'
import styles from '@/styles/modules/auth/LoginPage.module.css'

/**
 * Кастомная форма входа (Figma): email + пароль через POST /auth/login (прокси SSO).
 * Тихий refresh через cookie — если сессия жива, редирект без формы.
 */
export function LoginPage() {
  const accessToken = useAuthStore((s) => s.accessToken)
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const silentAttemptedRef = useRef(false)
  const emailInputRef = useRef<HTMLInputElement>(null)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [silentRefreshing, setSilentRefreshing] = useState(
    () => Boolean(useAuthStore.getState().expiresAt),
  )

  /** Только явный `?next=` — иначе не затираем путь из RequireAuth. */
  const nextFromQuery = resolveLoginNextQueryParam(params.get('next'))

  useEffect(() => {
    if (accessToken) {
      const savedNext = sessionStorage.getItem(AUTH_NEXT_PATH_KEY)
      if (savedNext) {
        sessionStorage.removeItem(AUTH_NEXT_PATH_KEY)
        goToPostLoginPath(savedNext, accessToken, navigate)
      } else {
        navigate(nextFromQuery || '/', { replace: true })
      }
      return
    }

    if (nextFromQuery) {
      sessionStorage.setItem(AUTH_NEXT_PATH_KEY, nextFromQuery)
    }

    let cancelled = false

    void (async () => {
      const { expiresAt } = useAuthStore.getState()
      if (expiresAt && !silentAttemptedRef.current) {
        silentAttemptedRef.current = true
        const newToken = await silentRefreshAccessToken()
        if (cancelled) return
        setSilentRefreshing(false)
        if (newToken) {
          const savedNext = sessionStorage.getItem(AUTH_NEXT_PATH_KEY)
          sessionStorage.removeItem(AUTH_NEXT_PATH_KEY)
          goToPostLoginPath(savedNext || nextFromQuery || '/', newToken, navigate)
        }
      } else {
        setSilentRefreshing(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [accessToken, navigate, nextFromQuery])

  useEffect(() => {
    if (!silentRefreshing && !accessToken) {
      emailInputRef.current?.focus()
    }
  }, [silentRefreshing, accessToken])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    const trimmedEmail = email.trim()
    if (!trimmedEmail || !password) {
      setError('Укажите email и пароль')
      return
    }
    setIsSubmitting(true)
    try {
      const data = await loginWithPassword({
        email: trimmedEmail,
        password,
        redirect_uri: getSpaRedirectUri(),
      })
      useAuthStore.getState().setSession({
        access_token: data.access_token,
        expires_in: data.expires_in,
        oauth_client_id: data.oauth_client_id,
        user: data.user,
      })
      const savedNext = sessionStorage.getItem(AUTH_NEXT_PATH_KEY)
      sessionStorage.removeItem(AUTH_NEXT_PATH_KEY)
      goToPostLoginPath(
        savedNext || nextFromQuery || data.redirect_after_login || '/',
        data.access_token,
        navigate,
      )
    } catch (err) {
      setError(userFacingMessageFromUnknown(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  if (accessToken || silentRefreshing) {
    return null
  }

  return (
    <div className={styles.page} data-theme="light">
      <div className={styles.formSide}>
        <div className={styles.formInner}>
          <h1 className={styles.title}>Войти в «Космолёт»</h1>
          <form className={styles.form} onSubmit={(e) => void handleSubmit(e)}>
            <div className={styles.fields}>
              <label className={styles.field}>
                <span className={styles.label}>Email или логин</span>
                <input
                  ref={emailInputRef}
                  type="text"
                  name="username"
                  autoComplete="username"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={styles.input}
                  placeholder="Email или логин"
                  disabled={isSubmitting}
                  required
                />
              </label>
              <label className={styles.field}>
                <span className={styles.label}>Пароль</span>
                <input
                  type="password"
                  name="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={styles.input}
                  placeholder="Пароль"
                  disabled={isSubmitting}
                  required
                />
              </label>
            </div>
            {error ? (
              <p className={styles.error} role="alert">
                {error}
              </p>
            ) : null}
            <button type="submit" className={styles.submitBtn} disabled={isSubmitting}>
              {isSubmitting ? 'Вход…' : 'Войти'}
            </button>
          </form>
        </div>
      </div>
      <aside className={styles.brandSide} aria-hidden>
        <div className={styles.brandPanel}>
          <div className={styles.brandLogo}>
            <img src="/auth/gustaff-symbol.svg" alt="" className={styles.brandSymbol} />
            <img src="/auth/gustaff-text.svg" alt="" className={styles.brandText} />
          </div>
        </div>
      </aside>
    </div>
  )
}
