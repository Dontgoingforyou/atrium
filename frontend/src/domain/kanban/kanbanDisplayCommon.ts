/** Колонка-агрегатор для карточек в скрытых статусах/колонках канбана. */
export const KANBAN_OTHER_BUCKET = '__portal_other__'

/**
 * Порядок ключей: сохранённый pref + недостающие по position + хвост из ``extraKeys``.
 */
export function mergeOrderedKeys(
  allKeys: string[],
  prefOrder: string[] | null | undefined,
  positionByKey: Map<string, number>,
  extraKeys: string[] = [],
): string[] {
  const fromPref = prefOrder?.length
    ? prefOrder.filter((k) => allKeys.includes(k))
    : [...allKeys].sort((a, b) => (positionByKey.get(a) ?? 0) - (positionByKey.get(b) ?? 0))
  const order = [...fromPref]
  for (const k of allKeys) {
    if (!order.includes(k)) order.push(k)
  }
  const known = new Set(order)
  for (const k of extraKeys) {
    if (!known.has(k)) {
      order.push(k)
      known.add(k)
    }
  }
  return order
}

/**
 * Определяет, в какую сторону от целевой карточки вставить перетаскиваемую.
 *
 * Сравнивает центр перетаскиваемого элемента с центром целевого:
 * - если центр перетаскиваемого ниже центра целевого → вставить ПОСЛЕ (offset = 1)
 * - иначе → вставить ПЕРЕД (offset = 0)
 *
 * Используется в `handleDragEnd` канбана вместо всегда-перед-целевой логики.
 */
export function getKanbanDropOffset(
  overRect: { top: number; height: number },
  activeTranslated: { top: number; height: number } | null | undefined,
): 0 | 1 {
  if (!activeTranslated) return 0
  const activeMidY = activeTranslated.top + activeTranslated.height / 2
  return getKanbanDropOffsetFromMidY(overRect, activeMidY)
}

/** Смещение вставки по вертикали указателя относительно центра целевой карточки. */
export function getKanbanDropOffsetFromMidY(
  overRect: { top: number; height: number },
  activeMidY: number | null | undefined,
): 0 | 1 {
  if (activeMidY == null) return 0
  const overMidY = overRect.top + overRect.height / 2
  return activeMidY >= overMidY ? 1 : 0
}

type KanbanCardRect = { top: number; height: number }

/**
 * Якорь вставки: сосед, ОТНОСИТЕЛЬНО которого сервер должен вставить перетаскиваемую задачу.
 *
 * Почему не индекс: ``columnTasks`` на фронте может быть УЖЕ отфильтрован (например, режим
 * «Мои задачи» — ``mine_only``), тогда как backend переиндексирует ВСЕ видимые ему по RBAC
 * задачи статуса. Индекс в отфильтрованном списке не соответствует индексу в полном списке
 * backend, если между видимыми карточками есть скрытые (не «мои») — из-за этого перемещение
 * «на N карточек» на глазах пользователя приводило к смещению на другое число позиций.
 * Якорь — это ID конкретной соседней карточки, который одинаково однозначен в обоих списках.
 */
export type KanbanInsertAnchor = {
  afterTaskId: string | null
  beforeTaskId: string | null
}

export function kanbanInsertAnchorEquals(a: KanbanInsertAnchor, b: KanbanInsertAnchor): boolean {
  if (a.afterTaskId !== null) return a.afterTaskId === b.afterTaskId
  if (a.beforeTaskId !== null) return a.beforeTaskId === b.beforeTaskId
  return b.afterTaskId === null && b.beforeTaskId === null
}

export function visibleKanbanInsertAnchor(
  columnTasks: Array<{ id: string }>,
  taskId: string,
): KanbanInsertAnchor {
  const idx = columnTasks.findIndex((t) => t.id === taskId)
  if (idx < 0) return { afterTaskId: null, beforeTaskId: null }
  return {
    afterTaskId: idx > 0 ? columnTasks[idx - 1].id : null,
    beforeTaskId: idx < columnTasks.length - 1 ? columnTasks[idx + 1].id : null,
  }
}

export function kanbanReorderPeerTasks<
  T extends { id: string; parent_task_id: string | null; status: string },
>(
  dragged: T,
  columnStatus: string,
  columnVisibleTasks: T[],
  siblingsByParentId: Map<string, T[]>,
  taskById: Map<string, T>,
  subtasksFlat: boolean,
): T[] {
  if (!subtasksFlat && dragged.parent_task_id) {
    const parent = taskById.get(dragged.parent_task_id)
    if (parent && parent.status === columnStatus) {
      return (siblingsByParentId.get(dragged.parent_task_id) ?? []).filter(
        (st) => st.status === columnStatus,
      )
    }
  }
  return columnVisibleTasks
}

/**
 * Якорь вставки в ``others`` (без перетаскиваемой) по Y указателя и rect карточек колонки.
 *
 * Обходит зависимость от одного ``over`` на ``dragEnd``, который отстаёт при быстром drag.
 */
export function resolveKanbanInsertAnchorFromPointer(
  columnTasks: Array<{ id: string }>,
  taskId: string,
  activeMidY: number | null | undefined,
  cardRects: ReadonlyMap<string, KanbanCardRect>,
): KanbanInsertAnchor {
  const others = columnTasks.filter((t) => t.id !== taskId)
  if (others.length === 0) {
    return { afterTaskId: null, beforeTaskId: null }
  }

  if (activeMidY == null) {
    // Нет данных об указателе — оставляем задачу перед тем же соседом, где она была.
    const oldIndex = columnTasks.findIndex((t) => t.id === taskId)
    const clamped = Math.min(Math.max(0, oldIndex), others.length - 1)
    return { afterTaskId: null, beforeTaskId: others[clamped].id }
  }

  for (let i = 0; i < others.length; i++) {
    const rect = cardRects.get(others[i].id)
    if (!rect) continue
    const midY = rect.top + rect.height / 2
    if (activeMidY < midY) {
      return i === 0
        ? { afterTaskId: null, beforeTaskId: others[0].id }
        : { afterTaskId: others[i - 1].id, beforeTaskId: null }
    }
  }

  return { afterTaskId: others[others.length - 1].id, beforeTaskId: null }
}

/** Фильтр приоритетов с учётом связи родитель ↔ подзадачи. */
export function filterTasksByPriorityWithFamily<T extends { id: string; parent_task_id: string | null; priority: string }>(
  tasks: T[],
  priorities: string[],
): T[] {
  if (priorities.length === 0) return tasks
  const prioritySet = new Set(priorities)
  const byId = new Map(tasks.map((t) => [t.id, t]))
  const visibleIds = new Set<string>()

  for (const t of tasks) {
    if (prioritySet.has(t.priority)) visibleIds.add(t.id)
  }

  for (const id of [...visibleIds]) {
    const t = byId.get(id)
    if (!t) continue
    if (t.parent_task_id) visibleIds.add(t.parent_task_id)
  }

  for (const t of tasks) {
    if (t.parent_task_id && visibleIds.has(t.parent_task_id)) {
      visibleIds.add(t.id)
    }
  }

  return tasks.filter((t) => visibleIds.has(t.id))
}

export function orderTasksForListView<T extends { id: string; parent_task_id: string | null }>(tasks: T[]): T[] {
  const ids = new Set(tasks.map((t) => t.id))
  const childrenByParent = new Map<string, T[]>()
  const roots: T[] = []
  const orphans: T[] = []

  for (const t of tasks) {
    if (!t.parent_task_id) {
      roots.push(t)
      continue
    }
    if (!ids.has(t.parent_task_id)) {
      orphans.push(t)
      continue
    }
    const arr = childrenByParent.get(t.parent_task_id) ?? []
    arr.push(t)
    childrenByParent.set(t.parent_task_id, arr)
  }

  const ordered: T[] = []
  for (const root of roots) {
    ordered.push(root)
    ordered.push(...(childrenByParent.get(root.id) ?? []))
  }
  ordered.push(...orphans)
  return ordered
}

/** Видимый порядок колонок + опциональный ``KANBAN_OTHER_BUCKET`` в конце. */
export function buildDisplayOrderWithOtherBucket(
  fullOrder: string[],
  hiddenKeys: Set<string>,
  showAllHiddenColumns: boolean,
  hasHiddenItems: boolean,
): string[] {
  const visibleOrder = showAllHiddenColumns ? fullOrder : fullOrder.filter((k) => !hiddenKeys.has(k))
  const hasOtherBucket = !showAllHiddenColumns && hasHiddenItems
  return hasOtherBucket ? [...visibleOrder, KANBAN_OTHER_BUCKET] : visibleOrder
}
