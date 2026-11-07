import { useEffect, useRef, useState } from 'react'

import { selectStableImageUrl } from '../utils/avatar/selectStableImageUrl'

/**
 * Хук для плавной смены URL изображения без мерцания.
 *
 * Показывает старый URL до тех пор, пока новый не загружен в браузере.
 * Решает проблему мерцания при рефетче presigned URL от MinIO:
 * каждый рефетч генерирует новую подпись, браузер видит другой src
 * и на момент сетевого запроса показывает пустое место или инициалы.
 *
 * Когда imageUrl становится null/undefined — по умолчанию сразу пусто.
 * ``holdWhenEmpty`` держит предыдущий кадр (ожидание EA proxy blob).
 */
export function useStableImageUrl(
  imageUrl: string | null | undefined,
  holdWhenEmpty = false,
): string | null | undefined {
  const [displayedUrl, setDisplayedUrl] = useState<string | null | undefined>(imageUrl)
  const cancelRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    // Отменяем предыдущую незаконченную предзагрузку
    cancelRef.current?.()
    cancelRef.current = null

    // Случай null/undefined обрабатывается в возвращаемом значении ниже
    if (!imageUrl) return

    const el = new window.Image()
    el.src = imageUrl

    let cancelled = false
    cancelRef.current = () => {
      cancelled = true
      el.onload = null
      el.onerror = null
    }

    if (el.complete && el.naturalWidth > 0) {
      // Изображение уже в кеше — откладываем через микротаск,
      // чтобы не вызывать setState синхронно в теле эффекта
      Promise.resolve().then(() => {
        if (!cancelled) setDisplayedUrl(imageUrl)
      })
      return
    }

    // Грузим в фоне, показываем старый URL до готовности нового
    el.onload = () => {
      if (!cancelled) setDisplayedUrl(imageUrl)
    }
    el.onerror = () => {
      // При ошибке всё равно переключаем — onError на img-теге сработает и покажет fallback
      if (!cancelled) setDisplayedUrl(imageUrl)
    }

    return () => {
      cancelled = true
      el.onload = null
      el.onerror = null
    }
  }, [imageUrl])

  return selectStableImageUrl(imageUrl, displayedUrl, holdWhenEmpty)
}
