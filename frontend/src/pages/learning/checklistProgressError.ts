import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'

/** GET my-progress отвечает 404, пока пользователь не начал чек-лист. */
const PROGRESS_ABSENT_HINT = 'Прохождение не найдено'

export function isChecklistProgressAbsentError(error: unknown): boolean {
  return userFacingMessageFromUnknown(error).includes(PROGRESS_ABSENT_HINT)
}
