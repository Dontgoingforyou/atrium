import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'

import styles from '@/styles/modules/ui/ErrorBoundary.module.css'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback
      // Сырое сообщение ошибки — только в dev; в проде пользователю не показываем внутренние детали.
      const detail = import.meta.env.DEV ? this.state.error?.message : null
      return (
        <div className={styles.fallback} role="alert">
          <h2 className={styles.title}>Что-то пошло не так</h2>
          <p className={styles.message}>
            Произошла непредвиденная ошибка. Попробуйте перезагрузить страницу.
          </p>
          {detail ? <pre className={styles.detail}>{detail}</pre> : null}
          <button type="button" className={styles.reload} onClick={() => window.location.reload()}>
            Перезагрузить
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
