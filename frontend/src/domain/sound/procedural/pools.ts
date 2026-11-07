import errorPool from './pool/error.json'
import hoverPool from './pool/hover.json'
import notificationPool from './pool/notification.json'
import successPool from './pool/success.json'
import tapPool from './pool/tap.json'
import warningPool from './pool/warning.json'

import { UI_SOUND_KINDS, type UiSoundKind } from './kinds'
import type { Patch } from './patch'

export { UI_SOUND_KINDS, type UiSoundKind }

export const UI_SOUND_POOLS: Record<UiSoundKind, Patch[]> = {
  tap: tapPool as Patch[],
  hover: hoverPool as Patch[],
  success: successPool as Patch[],
  error: errorPool as Patch[],
  warning: warningPool as Patch[],
  notification: notificationPool as Patch[],
}
