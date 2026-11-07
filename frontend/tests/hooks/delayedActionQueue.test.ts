import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { DelayedActionQueue, DEFAULT_DELAYED_ACTION_MS } from '../../src/hooks/delayedActionQueue'

function createQueue(delayMs = DEFAULT_DELAYED_ACTION_MS) {
  const onChange = vi.fn()
  let nextId = 0
  const queue = new DelayedActionQueue(delayMs, onChange, () => `id-${nextId++}`)
  return { queue, onChange }
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('DEFAULT_DELAYED_ACTION_MS', () => {
  it('окно отмены — 5 секунд', () => {
    expect(DEFAULT_DELAYED_ACTION_MS).toBe(5_000)
  })
})

describe('DelayedActionQueue: истечение таймера', () => {
  it('вызывает onCommit по истечении таймера и не трогает onRevert', () => {
    const { queue } = createQueue(5_000)
    const onCommit = vi.fn()
    const onRevert = vi.fn()

    queue.schedule({ message: 'Удалено', onCommit, onRevert })
    expect(onCommit).not.toHaveBeenCalled()

    vi.advanceTimersByTime(5_000)

    expect(onCommit).toHaveBeenCalledTimes(1)
    expect(onRevert).not.toHaveBeenCalled()
    expect(queue.getPendingList()).toHaveLength(0)
  })

  it('не вызывает onCommit раньше времени', () => {
    const { queue } = createQueue(5_000)
    const onCommit = vi.fn()

    queue.schedule({ message: 'Удалено', onCommit })
    vi.advanceTimersByTime(4_999)

    expect(onCommit).not.toHaveBeenCalled()
    expect(queue.getPendingList()).toHaveLength(1)
  })
})

describe('DelayedActionQueue: undo', () => {
  it('ранний undo вызывает onRevert и onUndoClick, но не onCommit — даже если таймер потом истекает', () => {
    const { queue } = createQueue(5_000)
    const onCommit = vi.fn()
    const onRevert = vi.fn()
    const onUndoClick = vi.fn()

    const id = queue.schedule({ message: 'Удалено', onCommit, onRevert, onUndoClick })
    queue.undo(id)

    expect(onRevert).toHaveBeenCalledTimes(1)
    expect(onUndoClick).toHaveBeenCalledTimes(1)
    expect(onCommit).not.toHaveBeenCalled()
    expect(queue.getPendingList()).toHaveLength(0)

    // Таймер должен быть погашен — commit не должен внезапно сработать позже.
    vi.advanceTimersByTime(10_000)
    expect(onCommit).not.toHaveBeenCalled()
  })

  it('игнорирует undo неизвестного/уже обработанного id', () => {
    const { queue } = createQueue(5_000)
    const onRevert = vi.fn()
    queue.schedule({ message: 'Удалено', onCommit: vi.fn(), onRevert })

    queue.undo('unknown-id')

    expect(onRevert).not.toHaveBeenCalled()
    expect(queue.getPendingList()).toHaveLength(1)
  })
})

describe('DelayedActionQueue: runAction (информационные тосты)', () => {
  it('вызывает onAction и закрывает карточку без commit/revert', () => {
    const { queue } = createQueue(5_000)
    const onCommit = vi.fn()
    const onRevert = vi.fn()
    const onAction = vi.fn()

    const id = queue.schedule({ message: 'Документ восстановлен', onCommit, onRevert, onAction })
    queue.runAction(id)

    expect(onAction).toHaveBeenCalledTimes(1)
    expect(onCommit).not.toHaveBeenCalled()
    expect(onRevert).not.toHaveBeenCalled()
    expect(queue.getPendingList()).toHaveLength(0)
  })

  it('игнорирует runAction неизвестного id', () => {
    const { queue } = createQueue(5_000)
    const onAction = vi.fn()
    queue.schedule({ message: 'A', onCommit: vi.fn(), onAction })
    queue.runAction('missing')
    expect(onAction).not.toHaveBeenCalled()
    expect(queue.getPendingList()).toHaveLength(1)
  })
})

describe('DelayedActionQueue: F5-safe (beforeunload) — clearTimersOnly', () => {
  it('не вызывает ни onCommit, ни onRevert, даже если время истекло', () => {
    const { queue } = createQueue(5_000)
    const onCommit = vi.fn()
    const onRevert = vi.fn()

    queue.schedule({ message: 'Удалено', onCommit, onRevert })
    queue.clearTimersOnly()

    expect(queue.getPendingList()).toHaveLength(1)

    vi.advanceTimersByTime(10_000)

    expect(onCommit).not.toHaveBeenCalled()
    expect(onRevert).not.toHaveBeenCalled()
    expect(queue.getPendingList()).toHaveLength(1)
  })
})

describe('DelayedActionQueue: cancelAll (например размонтирование)', () => {
  it('вызывает onRevert для всех ожидающих действий и гасит таймеры', () => {
    const { queue } = createQueue(5_000)
    const onCommitA = vi.fn()
    const onRevertA = vi.fn()
    const onCommitB = vi.fn()
    const onRevertB = vi.fn()

    queue.schedule({ message: 'A', onCommit: onCommitA, onRevert: onRevertA })
    queue.schedule({ message: 'B', onCommit: onCommitB, onRevert: onRevertB })

    queue.cancelAll()

    expect(onRevertA).toHaveBeenCalledTimes(1)
    expect(onRevertB).toHaveBeenCalledTimes(1)
    expect(queue.getPendingList()).toHaveLength(0)

    vi.advanceTimersByTime(10_000)
    expect(onCommitA).not.toHaveBeenCalled()
    expect(onCommitB).not.toHaveBeenCalled()
  })
})

describe('DelayedActionQueue: несколько параллельных действий', () => {
  it('undo одного действия не влияет на таймер другого', () => {
    const { queue } = createQueue(5_000)
    const onCommitA = vi.fn()
    const onRevertA = vi.fn()
    const onCommitB = vi.fn()

    const idA = queue.schedule({ message: 'A', onCommit: onCommitA, onRevert: onRevertA })
    queue.schedule({ message: 'B', onCommit: onCommitB })

    queue.undo(idA)
    expect(onRevertA).toHaveBeenCalledTimes(1)
    expect(queue.getPendingList()).toHaveLength(1)

    vi.advanceTimersByTime(5_000)
    expect(onCommitA).not.toHaveBeenCalled()
    expect(onCommitB).toHaveBeenCalledTimes(1)
  })

  it('уведомляет подписчика (onChange) при добавлении и удалении элементов', () => {
    const { queue, onChange } = createQueue(5_000)

    const id = queue.schedule({ message: 'A', onCommit: vi.fn() })
    expect(onChange).toHaveBeenLastCalledWith([expect.objectContaining({ id, message: 'A' })])

    queue.undo(id)
    expect(onChange).toHaveBeenLastCalledWith([])
  })
})
