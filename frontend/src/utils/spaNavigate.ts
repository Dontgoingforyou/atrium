/** Навигация SPA без циклического импорта на router/routes. */

type NavigateFn = (to: string) => void | Promise<void>

let navigateFn: NavigateFn | null = null

export function registerSpaNavigate(fn: NavigateFn | null): void {
  navigateFn = fn
}

export function spaNavigate(to: string): void {
  if (navigateFn) {
    void navigateFn(to)
    return
  }
  window.location.assign(to)
}
