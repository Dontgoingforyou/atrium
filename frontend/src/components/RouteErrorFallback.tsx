import { useRouteError } from 'react-router'
import styles from '@/styles/modules/ui/ErrorFallback.module.css'

const CHUNK_LOAD_ERROR_MARKERS = [
  'Failed to fetch dynamically imported module',
  'Importing a module script failed',
  'error loading dynamically imported module',
]

/**
 * Сюда попадают необработанные ошибки маршрута, в т.ч. сбой динамического import()
 * (чаще всего — устаревший кэш: старый хэш чанка после пересборки / рестарта dev / нового Docker-образа).
 *
 * Сырое сообщение ошибки показывается только в DEV; в проде — фиксированный текст,
 * чтобы не утекали внутренние детали (пути чанков, фрагменты стека) — см. security.mdc.
 */
export function RouteErrorFallback() {
  const error = useRouteError()
  const message = error instanceof Error ? error.message : String(error)
  const lower = message.toLowerCase()
  const isChunkLoadError = CHUNK_LOAD_ERROR_MARKERS.some((m) => lower.includes(m.toLowerCase()))
  const detail = import.meta.env.DEV ? message : null

  return (
    <div className={styles.fallback}>
      <h1 className={styles.title}>Не удалось загрузить часть интерфейса</h1>
      {isChunkLoadError ? (
        <p>
          Обычно это не баг кода, а <strong>устаревшая вкладка</strong> после пересборки фронтенда или
          обновления контейнера: браузер пытается взять старый JS-файл, которого на сервере уже нет.
        </p>
      ) : (
        <>
          <p className={styles.message}>
            Произошла непредвиденная ошибка. Попробуйте обновить страницу.
          </p>
          {detail ? <p className={styles.message}>{detail}</p> : null}
        </>
      )}
      <p className={styles.actions}>
        <button type="button" className="btn-primary" onClick={() => window.location.reload()}>
          Обновить страницу
        </button>
        <span className={styles.hint}>или жёсткое обновление: Ctrl+Shift+R</span>
      </p>
    </div>
  )
}
