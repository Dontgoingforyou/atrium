/**
 * Outside-close слушает mousedown. Вход по click — жест уже завершён,
 * следующий mousedown снаружи это выход; глушить его до pointerup нельзя.
 */
export function shouldHoldOutsideCloseUntilPointerUp(
  openedBy: 'click' | 'pointerdown',
): boolean {
  return openedBy === 'pointerdown'
}
