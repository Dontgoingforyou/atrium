import { useEffect, useState } from 'react'
import { Link } from 'react-router'

import { authenticatedFetch } from '../api/rawClient'
import { SKIP_LOGOUT_BEACON_ONCE_KEY } from '../constants/auth'
import styles from '@/styles/modules/auth/AuthStatusPage.module.css'

/**
 * Маршрут SPA `/admin-bridge`: cookie-сессия SQLAdmin по Bearer и переход на `/admin/`.
 * Только is_portal_admin (проверка на бэкенде). В nginx отдаётся статикой, не API.
 */
export function AdminPanelBridgePage() {
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      const res = await authenticatedFetch('/auth/admin-session', {
        method: 'POST',
        credentials: 'same-origin',
      })
      if (cancelled) return
      if (res.ok) {
        // Тело ответа опционально — cookie уже выставлена; не требуем JSON.
        try {
          await res.json()
        } catch {
          /* ignore malformed body */
        }
        sessionStorage.setItem(SKIP_LOGOUT_BEACON_ONCE_KEY, '1')
        window.location.replace('/admin/')
        return
      }
      if (res.status === 403) {
        setError('Нет прав доступа к панели администратора.')
        return
      }
      if (res.status === 401) {
        setError('Сессия истекла. Войдите снова.')
        return
      }
      setError('Не удалось открыть панель администратора.')
    })()
    return () => {
      cancelled = true
    }
  }, [])

  if (error) {
    return (
      <div className={styles.bridgePanel}>
        <p className={styles.bridgeError} role="alert">
          {error}
        </p>
        <Link to="/">На главную</Link>
      </div>
    )
  }

  return (
    <div className={styles.bridgePanel}>
      <p className={styles.bridgeMuted}>Открытие панели администратора…</p>
    </div>
  )
}
