import type { NodeViewRendererProps } from '@tiptap/core'

import {
  buildinToggleOpenCommitDelayMs,
  buildinToggleBodySlotState,
  buildinToggleExpandedDataset,
  shouldHoldToggleVisualOpen,
  shouldIgnoreBuildinToggleChromeMutation,
  shouldReleaseOpenToggleSlotHeight,
  shouldSettleToggleChromeOnNodeUpdate,
} from '@/domain/documents/buildinToggle'
import {
  playBuildinToggleSlotHeight,
  settleBuildinToggleSlotHeight,
} from '@/domain/documents/buildinToggleSlotAnim'
import {
  applyBuildinToggleEditChrome,
  buildinToggleAttrsOnTitleEnter,
  insertPlainTextAtSelection,
  invertBuildinToggleOpen,
  isBuildinToggleArrowTarget,
  normalizeBuildinToggleTitle,
  shouldApplyRemoteToggleTitle,
  shouldPreventDefaultOnToggleTitleClick,
  shouldPreventDefaultOnToggleTitleKey,
  shouldToggleBuildinOpenOnChromeClick,
} from '@/domain/documents/buildinToggleTitle'

import { createBuildinToggleChrome } from './tiptapBuildinToggleChrome'
import { enterToggleBodyFromTitle } from './tiptapBuildinToggleEnterBody'
import { bindBuildinToggleBodyCaret } from './tiptapBuildinToggleSelection'
import {
  applyToggleNodeAttrs,
  peekPendingToggleOpen,
  scheduleToggleOpenAttr,
} from './tiptapBuildinToggleOpenCommit'

export function createBuildinToggleNodeView({
  node,
  editor,
  getPos,
}: NodeViewRendererProps) {
  const { root, header, arrow, titleInput, deleteBtn, bodySlot, bodyClip, contentDOM } =
    createBuildinToggleChrome(String(node.attrs.title ?? ''))

  const initialPos = getPos()
  const pendingAtCreate = typeof initialPos === 'number' ? peekPendingToggleOpen(initialPos) : undefined
  const attrsOpenAtCreate = Boolean(node.attrs.open)
  let visualOpen = attrsOpenAtCreate
  let lastAttrsOpen = attrsOpenAtCreate
  let pendingOpen: boolean | null = pendingAtCreate ?? null

  const paintExpandedChrome = (isOpen: boolean) => {
    visualOpen = isOpen
    root.dataset.expanded = buildinToggleExpandedDataset(isOpen)
    arrow.setAttribute('aria-expanded', buildinToggleExpandedDataset(isOpen))
    bodySlot.dataset.state = buildinToggleBodySlotState(isOpen)
    bodyClip.inert = !isOpen
  }

  const settleExpandedChrome = (isOpen: boolean) => {
    paintExpandedChrome(isOpen)
    settleBuildinToggleSlotHeight(bodySlot, isOpen)
  }

  const animateExpandedChrome = (isOpen: boolean) => {
    const stateChanged = bodySlot.dataset.state !== buildinToggleBodySlotState(isOpen)
    paintExpandedChrome(isOpen)
    if (stateChanged) {
      playBuildinToggleSlotHeight(bodySlot, isOpen)
    }
  }

  settleExpandedChrome(attrsOpenAtCreate)
  if (pendingOpen !== null && pendingOpen !== attrsOpenAtCreate) {
    const pending = pendingOpen
    requestAnimationFrame(() => {
      animateExpandedChrome(pending)
    })
  }

  let isLocallyDirty = false
  let suppressTitleCommit = false

  const syncChrome = () => {
    applyBuildinToggleEditChrome(titleInput, deleteBtn, editor.isEditable, contentDOM)
  }
  const bodyCaret = bindBuildinToggleBodyCaret(editor, contentDOM, getPos, syncChrome)
  syncChrome()
  editor.on('transaction', syncChrome)

  const commitTitle = (openOnEnter = false) => {
    if (!editor.isEditable) return
    const pos = getPos()
    if (typeof pos !== 'number') return
    const current = editor.state.doc.nodeAt(pos)
    if (!current || current.type.name !== 'buildinToggle') return
    const title = normalizeBuildinToggleTitle(titleInput.value)
    const attrs = openOnEnter
      ? buildinToggleAttrsOnTitleEnter(
          { title: String(current.attrs.title ?? ''), open: Boolean(current.attrs.open) },
          title,
        )
      : { title, open: Boolean(current.attrs.open) }
    applyToggleNodeAttrs(editor, pos, attrs)
    if (openOnEnter) {
      settleExpandedChrome(true)
    }
    isLocallyDirty = false
  }

  titleInput.addEventListener('input', () => {
    if (!editor.isEditable) return
    isLocallyDirty = true
  })
  titleInput.addEventListener('blur', () => {
    if (suppressTitleCommit) {
      suppressTitleCommit = false
      return
    }
    commitTitle()
  })
  const stopTitleKeyFromEditor = (event: KeyboardEvent) => {
    event.stopPropagation()
    event.stopImmediatePropagation()
  }

  titleInput.addEventListener(
    'keydown',
    (event) => {
      if (event.altKey && (event.key === 'ArrowUp' || event.key === 'ArrowDown')) {
        event.preventDefault()
        stopTitleKeyFromEditor(event)
        const pos = getPos()
        if (typeof pos === 'number') {
          editor.commands.moveRichTextBlock(event.key === 'ArrowUp' ? 'up' : 'down', pos)
        }
        return
      }
      stopTitleKeyFromEditor(event)
      if (shouldPreventDefaultOnToggleTitleKey(event.key)) {
        event.preventDefault()
        if (!editor.isEditable) return
        const next = insertPlainTextAtSelection(
          titleInput.value,
          titleInput.selectionStart ?? titleInput.value.length,
          titleInput.selectionEnd ?? titleInput.selectionStart ?? titleInput.value.length,
          ' ',
        )
        titleInput.value = next.value
        titleInput.setSelectionRange(next.caret, next.caret)
        isLocallyDirty = true
        return
      }
      if (event.key !== 'Enter' && event.key !== 'Escape') return
      event.preventDefault()
      if (event.key === 'Enter') {
        const pos = getPos()
        if (typeof pos !== 'number') {
          commitTitle(true)
          editor.commands.focus()
          return
        }
        const current = editor.state.doc.nodeAt(pos)
        if (!current || current.type.name !== 'buildinToggle') {
          editor.commands.focus()
          return
        }
        const title = normalizeBuildinToggleTitle(titleInput.value)
        const attrs = buildinToggleAttrsOnTitleEnter(
          { title: String(current.attrs.title ?? ''), open: Boolean(current.attrs.open) },
          title,
        )
        enterToggleBodyFromTitle(editor, pos, attrs)
        settleExpandedChrome(true)
        isLocallyDirty = false
        return
      }
      commitTitle()
      titleInput.blur()
      editor.commands.focus()
    },
    true,
  )
  titleInput.addEventListener(
    'keyup',
    (event) => {
      stopTitleKeyFromEditor(event)
      if (shouldPreventDefaultOnToggleTitleKey(event.key)) {
        event.preventDefault()
      }
    },
    true,
  )

  const removeToggle = () => {
    if (!editor.isEditable) return
    const pos = getPos()
    if (typeof pos !== 'number') return
    editor.commands.command(({ tr, state }) => {
      const current = state.doc.nodeAt(pos)
      if (!current || current.type.name !== 'buildinToggle') return false
      tr.delete(pos, pos + current.nodeSize)
      return true
    })
    editor.commands.focus()
  }

  deleteBtn.addEventListener('mousedown', (event) => {
    event.stopPropagation()
    removeToggle()
  })

  const invertToggleOpen = () => {
    if (!editor.isEditable) return
    const pos = getPos()
    if (typeof pos !== 'number') return
    const current = editor.state.doc.nodeAt(pos)
    if (!current || current.type.name !== 'buildinToggle') return
    const newOpen = invertBuildinToggleOpen(visualOpen)
    pendingOpen = newOpen
    animateExpandedChrome(newOpen)
    scheduleToggleOpenAttr(
      editor,
      pos,
      newOpen,
      buildinToggleOpenCommitDelayMs(),
      normalizeBuildinToggleTitle(titleInput.value),
    )
  }

  arrow.addEventListener('mousedown', (event) => {
    if (!editor.isEditable) return
    event.preventDefault()
    event.stopPropagation()
    suppressTitleCommit = true
    invertToggleOpen()
  })
  arrow.addEventListener('click', (event) => {
    if (!editor.isEditable) return
    event.preventDefault()
    event.stopPropagation()
  })

  header.addEventListener('mousedown', (event) => {
    if ((event.target as HTMLElement).closest('.buildin-toggle-delete')) {
      return
    }
    if (isBuildinToggleArrowTarget(event.target)) {
      return
    }
    if (!editor.isEditable) return
    event.stopPropagation()
  })

  header.addEventListener('click', (event) => {
    const target = event.target as HTMLElement
    if (target.closest('.buildin-toggle-delete')) {
      event.stopPropagation()
      event.preventDefault()
      return
    }
    if (isBuildinToggleArrowTarget(target)) {
      if (editor.isEditable) {
        event.stopPropagation()
        event.preventDefault()
      }
      return
    }
    if (target.closest('.buildin-toggle-title-input')) {
      if (editor.isEditable) {
        event.stopPropagation()
      }
      if (shouldPreventDefaultOnToggleTitleClick()) {
        event.preventDefault()
      }
      return
    }
    if (!editor.isEditable) {
      return
    }
    event.stopPropagation()
    event.preventDefault()
    if (!shouldToggleBuildinOpenOnChromeClick(target)) return
    invertToggleOpen()
  })

  return {
    dom: root,
    contentDOM,
    ignoreMutation: (mutation: { target: EventTarget | null }) =>
      shouldIgnoreBuildinToggleChromeMutation(mutation.target, contentDOM),
    destroy() {
      bodyCaret.destroy()
      editor.off('transaction', syncChrome)
    },
    update: (updatedNode: typeof node) => {
      if (updatedNode.type.name !== 'buildinToggle') {
        return false
      }
      const attrsOpen = Boolean(updatedNode.attrs.open)
      if (
        shouldSettleToggleChromeOnNodeUpdate({
          pendingOpen,
          prevOpen: lastAttrsOpen,
          nextOpen: attrsOpen,
        })
      ) {
        pendingOpen = null
        settleExpandedChrome(attrsOpen)
      } else if (!shouldHoldToggleVisualOpen(pendingOpen, attrsOpen)) {
        pendingOpen = null
        if (
          shouldReleaseOpenToggleSlotHeight({
            isOpen: attrsOpen,
            hasInlineHeight: Boolean(bodySlot.style.height),
            isHoldingVisual: false,
          })
        ) {
          bodySlot.style.height = ''
        }
      }
      lastAttrsOpen = attrsOpen
      const attrsTitle = String(updatedNode.attrs.title ?? '')
      if (
        shouldApplyRemoteToggleTitle({
          inputValue: titleInput.value,
          attrsTitle,
          isInputFocused: document.activeElement === titleInput,
          isLocallyDirty,
        })
      ) {
        titleInput.value = attrsTitle
      }
      syncChrome()
      return true
    },
  }
}
