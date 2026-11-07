import Highlight from '@tiptap/extension-highlight'

import { RICH_TEXT_DEFAULT_HIGHLIGHT_COLOR } from '../constants'

/** Multicolor highlight: Mod-Shift-H всегда с цветом по умолчанию (не «голый» mark). */
export const PortalHighlight = Highlight.extend({
  addKeyboardShortcuts() {
    return {
      'Mod-Shift-h': () =>
        this.editor.commands.toggleHighlight({ color: RICH_TEXT_DEFAULT_HIGHLIGHT_COLOR }),
    }
  },
}).configure({ multicolor: true })
