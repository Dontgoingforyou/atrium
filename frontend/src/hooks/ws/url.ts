/** Преобразует HTTP(S)-URL API в WS(S)-URL для того же path. */
export function toWsUrl(apiBase: string, path: string): string {
  const base = apiBase.startsWith('http') ? apiBase : `${window.location.origin}${apiBase}`
  return base.replace(/^http/, 'ws') + path
}
