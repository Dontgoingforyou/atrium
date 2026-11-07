/**
 * Путь OAuth2 PKCE callback в SPA. Должен совпадать с Valid redirect URIs в IdP.
 */
export const SPA_OAUTH_CALLBACK_PATH = '/auth/callback'

/** sessionStorage: не слать logout-beacon при beforeunload (переход SPA → SQLAdmin). */
export const SKIP_LOGOUT_BEACON_ONCE_KEY = 'cosmolet_skip_logout_beacon_once'

/** sessionStorage: путь возврата после входа (post-login redirect). Общий для RequireAuth, LoginPage, AuthCallbackPage и backend docs_router.py. */
export const AUTH_NEXT_PATH_KEY = 'auth_next'

/** Ключ localStorage для zustand persist authStore. Кросс-слейный (бэкенд docs_router.py), не переименовывать. */
export const AUTH_PERSIST_KEY = 'cosmolet-auth'
