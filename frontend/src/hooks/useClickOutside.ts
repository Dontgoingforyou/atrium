import { useEffect, type RefObject } from 'react'

/**
 * Закрывает элемент при клике вне его.
 *
 * @param active   - слушать ли события (обычно `open`)
 * @param refs     - рефы контейнеров, клик внутри которых не считается "outside"
 * @param onClose  - вызывается при клике вне всех переданных рефов
 * @param eventType - тип события (по умолчанию `'click'` в capture-фазе)
 * @param ignoreSelector - CSS-селектор для узлов, порталируемых напрямую в `document.body`
 *   (например, выпадающие меню тулбара), клик по которым также не считается "outside"
 */
export function useClickOutside(
  active: boolean,
  refs: ReadonlyArray<RefObject<Element | null>>,
  onClose: () => void,
  eventType: 'click' | 'mousedown' | 'pointerdown' = 'click',
  ignoreSelector?: string,
): void {
  useEffect(() => {
    if (!active) return
    function handleOutside(e: Event) {
      const target = e.target as Node
      if (refs.some((r) => r.current?.contains(target))) return
      if (ignoreSelector && target instanceof Element && target.closest(ignoreSelector)) return
      onClose()
    }
    document.addEventListener(eventType, handleOutside, true)
    return () => document.removeEventListener(eventType, handleOutside, true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, onClose, eventType, ignoreSelector])
}
