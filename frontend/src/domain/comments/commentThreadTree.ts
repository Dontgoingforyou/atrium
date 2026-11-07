import type { ThreadComment } from '../../types/commentThread'

/**
 * Удаляет комментарий (или ответ на любой глубине вложенности) по id, перестраивая
 * дерево иммутабельно: новые объекты создаются только на пути к удалённому узлу.
 * Если узел с id не найден — возвращается исходный массив (та же ссылка), чтобы
 * не провоцировать лишние ре-рендеры потребителей.
 */
export function removeCommentById(comments: ThreadComment[], id: string): ThreadComment[] {
  let changed = false
  const result: ThreadComment[] = []
  for (const c of comments) {
    if (c.id === id) {
      changed = true
      continue
    }
    if (c.replies.length === 0) {
      result.push(c)
      continue
    }
    const pruned = removeCommentById(c.replies, id)
    if (pruned !== c.replies) {
      changed = true
      result.push({ ...c, replies: pruned })
    } else {
      result.push(c)
    }
  }
  return changed ? result : comments
}
