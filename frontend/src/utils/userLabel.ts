/**
 * Минимальная форма пользователя, по которой строится отображаемое имя.
 * Структурный тип — применим к PortalUser и любому объекту с теми же полями.
 */
export type UserLabelSource = {
  sub: string
  display_name?: string | null
  email?: string | null
  username?: string | null
}

/**
 * Отображаемое имя пользователя: первый непустой из display_name / email / username / sub.
 *
 * Единый источник правды для подписей пользователей в пикерах, чате, комментариях,
 * фильтрах и т.п. — не дублировать формулу `||` по компонентам.
 *
 * При `trim: true` каждое поле обрезается от краёв перед проверкой (для подписей
 * в аватарах/тултипах, где висящие пробелы портят вид).
 */
export function getUserDisplayLabel(
  u: UserLabelSource,
  options: { trim?: boolean } = {},
): string {
  const trim = options.trim
  const pick = (v: string | null | undefined): string | undefined =>
    v ? (trim ? v.trim() : v) || undefined : undefined
  return pick(u.display_name) || pick(u.email) || pick(u.username) || u.sub
}
