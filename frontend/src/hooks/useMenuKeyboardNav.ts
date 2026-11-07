import { useEffect, type KeyboardEvent, type RefObject } from 'react'

const MENUITEM_SELECTOR = '[role="menuitem"]:not([disabled])'

/**
 * Клавиатурная навигация для overlay-меню (role="menu" с role="menuitem"):
 * - при открытии — фокус на первый доступный пункт;
 * - ArrowUp/Down/Home/End — перемещение фокуса между пунктами (roving tabindex);
 * - Escape — закрыть меню и вернуть фокус на триггер;
 * - на триггере ArrowDown/Enter/Space — открыть меню.
 *
 * Эталон — components/documents/DocumentActionsMenu.tsx. Дополняет useClickOutside
 * (закрытие по клику вне), но не заменяет её.
 */
export function useMenuKeyboardNav(
  open: boolean,
  setOpen: (open: boolean) => void,
  triggerRef: RefObject<HTMLButtonElement | null>,
  menuRef: RefObject<HTMLElement | null>,
) {
  useEffect(() => {
    if (!open) return
    const items = menuRef.current?.querySelectorAll<HTMLElement>(MENUITEM_SELECTOR)
    items?.[0]?.focus()
  }, [open, menuRef])

  function getMenuItems(): HTMLElement[] {
    const list = menuRef.current?.querySelectorAll<HTMLElement>(MENUITEM_SELECTOR)
    return list ? Array.from(list) : []
  }

  function focusMenuItem(index: number): void {
    const items = getMenuItems()
    if (items.length === 0) return
    const i = (index + items.length) % items.length
    items[i].focus()
  }

  function handleMenuKeyDown(e: KeyboardEvent<HTMLElement>): void {
    const items = getMenuItems()
    if (items.length === 0) return
    const currentIndex = items.findIndex((el) => el === document.activeElement)
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        focusMenuItem(currentIndex < 0 ? 0 : currentIndex + 1)
        break
      case 'ArrowUp':
        e.preventDefault()
        focusMenuItem(currentIndex < 0 ? 0 : currentIndex - 1)
        break
      case 'Home':
        e.preventDefault()
        focusMenuItem(0)
        break
      case 'End':
        e.preventDefault()
        focusMenuItem(items.length - 1)
        break
      case 'Enter':
      case ' ':
      case 'Spacebar':
        if (currentIndex >= 0) {
          e.preventDefault()
          ;(items[currentIndex] as HTMLElement).click()
        }
        break
      case 'Escape':
        e.preventDefault()
        setOpen(false)
        triggerRef.current?.focus()
        break
    }
  }

  function handleTriggerKeyDown(e: KeyboardEvent<HTMLButtonElement>): void {
    if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
      if (!open) {
        e.preventDefault()
        setOpen(true)
      }
    }
  }

  return { handleMenuKeyDown, handleTriggerKeyDown }
}
