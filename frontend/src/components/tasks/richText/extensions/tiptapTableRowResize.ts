import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import type { EditorView } from '@tiptap/pm/view'
import { cellAround } from '@tiptap/pm/tables'

const ROW_RESIZE_EDGE_PX = 8
const COL_RESIZE_EDGE_PX = 10
const MIN_ROW_HEIGHT = 28

type DragState = {
  startY: number
  startHeight: number
  rowPos: number
  view: EditorView
  pendingHeight: number
  rafId: number | null
}

let activeDrag: DragState | null = null

function closestCell(target: EventTarget | null): HTMLTableCellElement | null {
  if (!(target instanceof Element)) return null
  return target.closest('td, th')
}

function isNearBottomEdge(cell: HTMLTableCellElement, clientX: number, clientY: number): boolean {
  const rect = cell.getBoundingClientRect()
  // У правого края — зона column resize, не перехватываем.
  if (clientX >= rect.right - COL_RESIZE_EDGE_PX) return false
  return clientY >= rect.bottom - ROW_RESIZE_EDGE_PX && clientY <= rect.bottom + 2
}

function dispatchRowHeight(view: EditorView, rowPos: number, heightPx: number): boolean {
  const rowNode = view.state.doc.nodeAt(rowPos)
  if (!rowNode || rowNode.type.name !== 'tableRow') return false
  const height = `${heightPx}px`
  if (rowNode.attrs.height === height) return true
  const tr = view.state.tr.setNodeMarkup(rowPos, undefined, {
    ...rowNode.attrs,
    height,
  })
  view.dispatch(tr)
  return true
}

function scheduleHeightUpdate(drag: DragState) {
  if (drag.rafId != null) return
  drag.rafId = requestAnimationFrame(() => {
    drag.rafId = null
    if (activeDrag !== drag) return
    dispatchRowHeight(drag.view, drag.rowPos, drag.pendingHeight)
  })
}

function onWindowPointerMove(event: PointerEvent) {
  if (!activeDrag) return
  const dy = event.clientY - activeDrag.startY
  activeDrag.pendingHeight = Math.max(MIN_ROW_HEIGHT, Math.round(activeDrag.startHeight + dy))
  scheduleHeightUpdate(activeDrag)
}

function onWindowPointerUp() {
  if (!activeDrag) return
  const { view, rowPos, pendingHeight, rafId } = activeDrag
  if (rafId != null) cancelAnimationFrame(rafId)
  try {
    dispatchRowHeight(view, rowPos, pendingHeight)
  } catch {
    /* ignore */
  }
  view.dom.classList.remove('row-resize-cursor')
  activeDrag = null
  window.removeEventListener('pointermove', onWindowPointerMove)
  window.removeEventListener('pointerup', onWindowPointerUp)
}

export const TableRowResize = Extension.create({
  name: 'tableRowResize',

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey('tableRowResize'),
        props: {
          handleDOMEvents: {
            mousemove(view, event) {
              if (activeDrag) return true
              if (!view.editable || view.dom.classList.contains('resize-cursor')) {
                view.dom.classList.remove('row-resize-cursor')
                return false
              }
              const cell = closestCell(event.target)
              if (cell && isNearBottomEdge(cell, event.clientX, event.clientY)) {
                view.dom.classList.add('row-resize-cursor')
              } else {
                view.dom.classList.remove('row-resize-cursor')
              }
              return false
            },
            mouseleave(view) {
              if (activeDrag) return false
              view.dom.classList.remove('row-resize-cursor')
              return false
            },
          },
        },
        view(editorView) {
          const onMouseDownCapture = (event: MouseEvent) => {
            if (activeDrag) return
            if (!editorView.editable || event.button !== 0) return
            if (editorView.dom.classList.contains('resize-cursor')) return
            const cell = closestCell(event.target)
            if (!cell || !isNearBottomEdge(cell, event.clientX, event.clientY)) return

            const pos = editorView.posAtDOM(cell, 0)
            const $cell = cellAround(editorView.state.doc.resolve(pos))
            if (!$cell) return
            const rowPos = $cell.before($cell.depth)
            const rowNode = editorView.state.doc.nodeAt(rowPos)
            if (!rowNode || rowNode.type.name !== 'tableRow') return

            event.preventDefault()
            event.stopPropagation()
            event.stopImmediatePropagation()

            activeDrag = {
              rowPos,
              view: editorView,
              startY: event.clientY,
              startHeight: Math.max(MIN_ROW_HEIGHT, cell.closest('tr')!.getBoundingClientRect().height),
              pendingHeight: 0,
              rafId: null,
            }
            editorView.dom.classList.add('row-resize-cursor')
            window.addEventListener('pointermove', onWindowPointerMove)
            window.addEventListener('pointerup', onWindowPointerUp)
          }

          editorView.dom.addEventListener('mousedown', onMouseDownCapture, true)

          return {
            destroy() {
              editorView.dom.removeEventListener('mousedown', onMouseDownCapture, true)
              if (activeDrag) {
                if (activeDrag.rafId != null) cancelAnimationFrame(activeDrag.rafId)
                window.removeEventListener('pointermove', onWindowPointerMove)
                window.removeEventListener('pointerup', onWindowPointerUp)
                activeDrag = null
              }
            },
          }
        },
      }),
    ]
  },
})
