/** Ключи localStorage для PKCE (тот же origin, что и старт входа). */
export const PKCE_STORAGE_STATE_KEY = 'atrium_pkce_state'
export const PKCE_STORAGE_VERIFIER_KEY = 'atrium_pkce_verifier'

function randomUrlSafe(len: number): string {
  const bytes = new Uint8Array(len)
  crypto.getRandomValues(bytes)
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
  let s = ''
  for (let i = 0; i < len; i += 1) {
    s += alphabet[bytes[i]! % alphabet.length]
  }
  return s
}

function base64Url(buf: ArrayBuffer): string {
  const bin = String.fromCharCode(...new Uint8Array(buf))
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

export async function createPkcePair(): Promise<{ verifier: string; challenge: string }> {
  const verifier = randomUrlSafe(64)
  const data = new TextEncoder().encode(verifier)
  const digest = await crypto.subtle.digest('SHA-256', data)
  const challenge = base64Url(digest)
  return { verifier, challenge }
}
