import contentStyles from '@/styles/modules/tasks/RichTextEditorContent.module.css'

import {
  BLOCK_REORDER_DROP_MS,
  BLOCK_REORDER_EASING,
  BLOCK_REORDER_LAYOUT_MS,
  blockReorderDropLineRect,
  previewListWrapperTagName,
  siblingOverIndexFromY,
  siblingReorderShiftY,
} from '@/domain/documents/richTextBlockReorder'

type RelRect = { top: number; left: number; height: number; width: number }

export type BlockReorderPreview = {
  overlay: HTMLElement
  dropLine: HTMLElement
  sourceEl: HTMLElement
  siblingEls: HTMLElement[]
  parent: HTMLElement
  sourceIndex: number
  overIndex: number
  originLeft: number
  originTop: number
  startX: number
  startY: number
  rel: RelRect[]
  stride: number
  reducedMotion: boolean
}

function prefersReducedMotion(): boolean {
  return typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches
}

function layoutTransition(reducedMotion: boolean): string {
  if (reducedMotion) return 'none'
  return `transform ${BLOCK_REORDER_LAYOUT_MS}ms ${BLOCK_REORDER_EASING}`
}

function currentMids(preview: BlockReorderPreview): number[] {
  const parentRect = preview.parent.getBoundingClientRect()
  return preview.rel.map((rect) => parentRect.top + rect.top + rect.height / 2)
}

function holeRect(preview: BlockReorderPreview): { left: number; top: number } {
  const parentRect = preview.parent.getBoundingClientRect()
  const rel = preview.rel[preview.overIndex] ?? preview.rel[preview.sourceIndex]
  if (!rel) return { left: preview.originLeft, top: preview.originTop }
  return { left: parentRect.left + rel.left, top: parentRect.top + rel.top }
}

function applySiblingShifts(preview: BlockReorderPreview): void {
  preview.siblingEls.forEach((el, index) => {
    const dy = siblingReorderShiftY(index, preview.sourceIndex, preview.overIndex, preview.stride)
    el.style.transform = dy ? `translateY(${dy}px)` : ''
  })
}

function applyDropLine(preview: BlockReorderPreview, sameParent: boolean): void {
  const rect = sameParent
    ? blockReorderDropLineRect(preview.sourceIndex, preview.overIndex, preview.rel)
    : null
  const line = preview.dropLine
  if (!rect) {
    line.hidden = true
    return
  }
  const parentRect = preview.parent.getBoundingClientRect()
  line.hidden = false
  line.style.left = `${parentRect.left + rect.left}px`
  line.style.top = `${parentRect.top + rect.top}px`
  line.style.width = `${rect.width}px`
  line.style.height = `${rect.height}px`
}

export function startBlockReorderPreview(
  sourceEl: HTMLElement,
  siblingEls: HTMLElement[],
  sourceIndex: number,
  startX: number,
  startY: number,
): BlockReorderPreview | null {
  const parent = sourceEl.parentElement
  if (!parent || sourceIndex < 0 || sourceIndex >= siblingEls.length) return null

  const parentRect = parent.getBoundingClientRect()
  const sourceRect = sourceEl.getBoundingClientRect()
  const next = siblingEls[sourceIndex + 1]
  const stride = Math.max(
    next ? next.getBoundingClientRect().top - sourceRect.top : sourceRect.height,
    sourceRect.height,
  )
  const rel = siblingEls.map((el) => {
    const rect = el.getBoundingClientRect()
    return {
      top: rect.top - parentRect.top,
      left: rect.left - parentRect.left,
      height: rect.height,
      width: rect.width,
    }
  })

  const layer = document.body
  const overlay = document.createElement('div')
  overlay.className = `${contentStyles.editor} ${contentStyles.blockDragOverlay}`
  overlay.setAttribute('aria-hidden', 'true')
  const pm = document.createElement('div')
  pm.className = 'ProseMirror'
  const clone = sourceEl.cloneNode(true) as HTMLElement
  clone.classList.remove(contentStyles.blockReorderSource)
  clone.querySelectorAll('input, textarea, button').forEach((node) => {
    if (node instanceof HTMLInputElement || node instanceof HTMLTextAreaElement) {
      node.tabIndex = -1
      node.readOnly = true
    }
    if (node instanceof HTMLButtonElement) node.tabIndex = -1
  })
  if (clone.tagName === 'LI') {
    const parent = sourceEl.parentElement
    const list = document.createElement(previewListWrapperTagName(parent?.tagName))
    if (parent) list.className = parent.className
    list.appendChild(clone)
    pm.appendChild(list)
  } else {
    pm.appendChild(clone)
  }
  overlay.appendChild(pm)
  overlay.style.left = `${sourceRect.left}px`
  overlay.style.top = `${sourceRect.top}px`
  overlay.style.width = `${sourceRect.width}px`
  overlay.style.margin = '0'
  overlay.style.transform = 'translate(0px, 0px)'
  layer.appendChild(overlay)

  const dropLine = document.createElement('div')
  dropLine.className = contentStyles.blockDropLine
  dropLine.setAttribute('aria-hidden', 'true')
  dropLine.hidden = true
  layer.appendChild(dropLine)

  const reducedMotion = prefersReducedMotion()
  siblingEls.forEach((el, index) => {
    if (index === sourceIndex) return
    el.style.transition = layoutTransition(reducedMotion)
  })
  sourceEl.classList.add(contentStyles.blockReorderSource)

  const preview: BlockReorderPreview = {
    overlay,
    dropLine,
    sourceEl,
    siblingEls,
    parent,
    sourceIndex,
    overIndex: sourceIndex,
    originLeft: sourceRect.left,
    originTop: sourceRect.top,
    startX,
    startY,
    rel,
    stride,
    reducedMotion,
  }
  moveBlockReorderPreview(preview, startX, startY)
  return preview
}

export function moveBlockReorderPreview(
  preview: BlockReorderPreview,
  clientX: number,
  clientY: number,
  sameParent = true,
): void {
  const dx = clientX - preview.startX
  const dy = clientY - preview.startY
  const rotate = preview.reducedMotion ? '0deg' : '1.5deg'
  preview.overlay.style.transform = `translate(${dx}px, ${dy}px) rotate(${rotate})`
  const nextOver = sameParent
    ? siblingOverIndexFromY(clientY, currentMids(preview))
    : preview.sourceIndex
  if (nextOver === preview.overIndex) {
    applyDropLine(preview, sameParent)
    return
  }
  preview.overIndex = nextOver
  applySiblingShifts(preview)
  applyDropLine(preview, sameParent)
}

export function freezeBlockReorderPreview(preview: BlockReorderPreview): void {
  preview.siblingEls.forEach((el) => {
    el.style.transition = 'none'
    el.style.transform = ''
  })
  preview.dropLine.hidden = true
}

export function destroyBlockReorderPreview(preview: BlockReorderPreview): void {
  freezeBlockReorderPreview(preview)
  preview.overlay.remove()
  preview.dropLine.remove()
  preview.sourceEl.classList.remove(contentStyles.blockReorderSource)
}

export function settleBlockReorderPreview(
  preview: BlockReorderPreview,
  onSettled: () => void,
): void {
  const hole = holeRect(preview)
  const targetDx = hole.left - preview.originLeft
  const targetDy = hole.top - preview.originTop
  if (preview.reducedMotion) {
    onSettled()
    return
  }
  const overlay = preview.overlay
  overlay.style.transition = `transform ${BLOCK_REORDER_DROP_MS}ms ${BLOCK_REORDER_EASING}`
  overlay.style.transform = `translate(${targetDx}px, ${targetDy}px)`
  let finished = false
  const finish = () => {
    if (finished) return
    finished = true
    overlay.removeEventListener('transitionend', onEnd)
    window.clearTimeout(timeout)
    onSettled()
  }
  const onEnd = (event: TransitionEvent) => {
    if (event.target !== overlay || event.propertyName !== 'transform') return
    finish()
  }
  overlay.addEventListener('transitionend', onEnd)
  const timeout = window.setTimeout(finish, BLOCK_REORDER_DROP_MS + 40)
}
