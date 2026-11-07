import type { AuthUser } from '../types/auth'
import { SPA_OAUTH_CALLBACK_PATH } from '../constants/auth'
import { parseJsonOrThrowApi } from './parseResponse'
import { apiFetch, authenticatedFetch } from './rawClient'

export function getSpaRedirectUri(): string {
  const fromEnv = (import.meta.env.VITE_SPA_REDIRECT_URI as string | undefined)?.trim()
  if (fromEnv) {
    return fromEnv
  }
  return `${window.location.origin}${SPA_OAUTH_CALLBACK_PATH}`
}

export async function loginWithPassword(payload: {
  email: string
  password: string
  redirect_uri?: string
}): Promise<TokenExchangeResult> {
  const res = await apiFetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: payload.email,
      password: payload.password,
      redirect_uri: payload.redirect_uri ?? getSpaRedirectUri(),
    }),
    credentials: 'include',
  })
  return parseJsonOrThrowApi<TokenExchangeResult>(res)
}

export async function fetchAuthorizationUrl(params: {
  redirect_uri: string
  code_challenge: string
  state: string
}): Promise<string> {
  const q = new URLSearchParams({
    redirect_uri: params.redirect_uri,
    code_challenge: params.code_challenge,
    state: params.state,
    code_challenge_method: 'S256',
  })
  const res = await apiFetch(`/auth/authorization-url?${q.toString()}`)
  const data = await parseJsonOrThrowApi<{ authorization_url: string }>(res)
  return data.authorization_url
}

export type TokenExchangeResult = {
  access_token: string
  /** Refresh-токен больше не возвращается в теле (хранится в httpOnly cookie 'rt'). */
  refresh_token?: null
  expires_in: number
  oauth_client_id: string
  user: AuthUser
  redirect_after_login?: string
}

export async function exchangeCodeForTokens(payload: {
  code: string
  redirect_uri: string
  code_verifier: string
}): Promise<TokenExchangeResult> {
  const res = await apiFetch('/auth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    credentials: 'include', // ставит httpOnly cookie 'rt' — как и /auth/login, /auth/refresh
  })
  return parseJsonOrThrowApi<TokenExchangeResult>(res)
}

const codeExchangeInFlight = new Map<string, Promise<TokenExchangeResult>>()

/** Дедупликация обмена кода (React Strict Mode вызывает effect дважды). */
export function exchangeCodeForTokensOnce(payload: {
  code: string
  redirect_uri: string
  code_verifier: string
}): Promise<TokenExchangeResult> {
  const { code } = payload
  let pending = codeExchangeInFlight.get(code)
  if (!pending) {
    pending = exchangeCodeForTokens(payload).finally(() => {
      codeExchangeInFlight.delete(code)
    })
    codeExchangeInFlight.set(code, pending)
  }
  return pending
}

export async function fetchMe(): Promise<AuthUser> {
  const res = await authenticatedFetch('/auth/me')
  return parseJsonOrThrowApi<AuthUser>(res)
}
