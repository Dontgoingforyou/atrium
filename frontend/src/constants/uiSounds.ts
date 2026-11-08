/** Ключи localStorage UI-SFX. Значения не менять — сбросят настройку пользователей. */

export const UI_SOUNDS_ENABLED_KEY = 'atrium_ui_sounds_enabled'
export const UI_SOUNDS_KIT_KEY = 'atrium_ui_sounds_kit'

/** Не играть tap на этом контроле и его потомках (колокольчик, превью). */
export const UI_SOUND_SKIP_VALUE = 'skip'
export const UI_SOUND_SKIP_SELECTOR = `[data-ui-sound="${UI_SOUND_SKIP_VALUE}"]`
