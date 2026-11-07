/**
 * Утилиты работы с URLSearchParams.
 *
 * Единственный источник правды для повторяющихся паттернов
 * чтения/записи query-параметров в строке URL.
 */

/**
 * Считать все значения повторяющегося параметра (`?key=a&key=b`) как массив строк.
 * Пустые строки фильтруются; дубликаты удаляются.
 */
export function parseRepeatedSearchParam(params: URLSearchParams, key: string): string[] {
  return [...new Set(params.getAll(key).filter(Boolean))]
}

/**
 * Установить повторяющийся параметр в копии `params`:
 * сначала удаляет все значения по ключу, затем добавляет каждое из `values`.
 * Возвращает новый объект URLSearchParams (оригинал не мутируется).
 */
export function setRepeatedSearchParam(
  params: URLSearchParams,
  key: string,
  values: string[],
): URLSearchParams {
  const next = new URLSearchParams(params)
  next.delete(key)
  for (const v of values) next.append(key, v)
  return next
}
