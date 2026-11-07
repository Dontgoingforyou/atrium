export const DEFAULT_DELAYED_ACTION_MS = 5_000

export type DelayedActionPayload = {
  message: string
  /**
   * Реальный запрос к backend. Вызывается ИСКЛЮЧИТЕЛЬНО по истечении таймера —
   * никогда синхронно в момент действия пользователя. Это делает окно отмены
   * F5-safe: обновление/закрытие страницы до истечения таймера не даёт запросу уйти.
   */
  onCommit: () => void
  /** Восстановление UI при отмене (до commit). */
  onRevert?: () => void
  /** Дополнительная логика при нажатии «Отменить». */
  onUndoClick?: () => void
  /** Подпись кнопки собственного действия карточки (например «Открыть»), кроме «Отменить». */
  actionLabel?: string
  /** Обработчик кнопки actionLabel — закрывает карточку без commit/revert. */
  onAction?: () => void
}

export type PendingDelayedAction = DelayedActionPayload & { id: string }

export class DelayedActionQueue {
  private readonly items = new Map<string, PendingDelayedAction>()
  private readonly timers = new Map<string, ReturnType<typeof setTimeout>>()
  private readonly delayMs: number
  private readonly onChange: (list: PendingDelayedAction[]) => void
  private readonly createId: () => string

  constructor(
    delayMs: number,
    onChange: (list: PendingDelayedAction[]) => void,
    createId: () => string = () => crypto.randomUUID(),
  ) {
    this.delayMs = delayMs
    this.onChange = onChange
    this.createId = createId
  }

  private emit() {
    this.onChange([...this.items.values()])
  }

  private removeSilently(id: string) {
    const timer = this.timers.get(id)
    if (timer) {
      clearTimeout(timer)
      this.timers.delete(id)
    }
    this.items.delete(id)
  }

  schedule(payload: DelayedActionPayload): string {
    const id = this.createId()
    this.items.set(id, { id, ...payload })

    const timer = setTimeout(() => {
      const item = this.items.get(id)
      this.removeSilently(id)
      this.emit()
      item?.onCommit()
    }, this.delayMs)
    this.timers.set(id, timer)

    this.emit()
    return id
  }

  undo(id: string) {
    const item = this.items.get(id)
    if (!item) return
    this.removeSilently(id)
    this.emit()
    item.onUndoClick?.()
    item.onRevert?.()
  }

  /** Кнопка собственного действия карточки (например «Открыть») — закрывает карточку без commit/revert. */
  runAction(id: string) {
    const item = this.items.get(id)
    if (!item) return
    this.removeSilently(id)
    this.emit()
    item.onAction?.()
  }

  /** Отменяет все ожидающие действия и вызывает их onRevert (например при размонтировании). */
  cancelAll() {
    const pending = [...this.items.values()]
    for (const id of this.items.keys()) {
      this.removeSilently(id)
    }
    this.emit()
    for (const item of pending) {
      item.onRevert?.()
    }
  }


  clearTimersOnly() {
    for (const timer of this.timers.values()) {
      clearTimeout(timer)
    }
    this.timers.clear()
  }

  getPendingList(): PendingDelayedAction[] {
    return [...this.items.values()]
  }
}
