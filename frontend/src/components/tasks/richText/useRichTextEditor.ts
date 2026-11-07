import { useEditor } from '@tiptap/react'
import type { Transaction } from '@tiptap/pm/state'
import { columnResizingPluginKey } from '@tiptap/pm/tables'
import StarterKit from '@tiptap/starter-kit'
import Heading from '@tiptap/extension-heading'
import TextAlign from '@tiptap/extension-text-align'
import Underline from '@tiptap/extension-underline'
import Link from '@tiptap/extension-link'
import FontFamily from '@tiptap/extension-font-family'
import TaskList from '@tiptap/extension-task-list'
import { TaskItem } from '@tiptap/extension-list'
import { Color } from '@tiptap/extension-color'
import { TextStyle } from '@tiptap/extension-text-style'
import Collaboration from '@tiptap/extension-collaboration'
import CollaborationCaret from '@tiptap/extension-collaboration-caret'
import type { HocuspocusProvider } from '@hocuspocus/provider'
import type * as Y from 'yjs'
import { useCallback, useEffect, useMemo, useRef } from 'react'

import { isBuildinToggleTitleInputTarget } from '@/domain/documents/buildinToggleTitle'
import {
  mapClickCoordsToDocPos,
  resolveRichTextFocusTarget,
  type RichTextFocusTarget,
} from '@/domain/documents/richTextEditorFocus'
import { interceptRichTextLinkClick } from '@/utils/html/richTextLinkClick'
import { sanitizeRichHtml } from '@/utils/html/sanitizeRichHtml'
import { rememberEmittedRichHtml, shouldApplyExternalRichHtml } from '@/utils/html/emittedRichHtml'
import { isSameRichTextCollaboration, shouldSeedCollabEditorFromLocalHtml } from '@/utils/documents/documentCollab'

import { BlockReorder } from './extensions/tiptapBlockReorderExtension'
import { FontSize } from './extensions/tiptapFontSizeExtension'
import { LineHeight } from './extensions/tiptapLineHeightExtension'
import { ParagraphIndent } from './extensions/tiptapParagraphIndentExtension'
import { TabHandler } from './extensions/tiptapTabHandler'
import { BuildinToggle } from './extensions/tiptapBuildinToggleExtension'
import { isNativeCaretInToggleBody } from './extensions/tiptapBuildinToggleSelection'
import { DocumentImage } from './extensions/tiptapImageExtension'
import { DocumentLink } from './extensions/documentLinkExtension'
import { PortalHighlight } from './extensions/portalHighlight'
import { portalTableExtensions } from './extensions/tiptapTableExtensions'
import { FONT_FAMILY_OPTIONS } from './constants'
import { imageFilesFromClipboard, uploadAndInsertRichTextImages } from './uploadRichTextImages'
import type { RichTextEntityType } from './RichTextEditor'

const ALLOWED_FONTS = FONT_FAMILY_OPTIONS.map((o) => o.value).filter(Boolean)

export type RichTextCollaboration = {
  ydoc: Y.Doc
  provider: HocuspocusProvider
  user: { name: string; color: string }
}

export function useRichTextEditor({
  content,
  onChange,
  editable = true,
  autoFocus = true,
  onFormatTick,
  onLinkShortcut,
  entityType,
  entityId,
  collaboration,
}: {
  content: string
  onChange: (html: string) => void
  editable?: boolean
  autoFocus?: boolean
  onFormatTick?: () => void
  onLinkShortcut?: () => void
  entityType?: RichTextEntityType
  entityId?: string
  collaboration?: RichTextCollaboration | null
}) {
  const onFormatTickRef = useRef(onFormatTick)
  const onLinkShortcutRef = useRef(onLinkShortcut)
  const entityTypeRef = useRef(entityType)
  const entityIdRef = useRef(entityId)
  const pendingUploadsRef = useRef<File[]>([])
  const flushingUploadsRef = useRef(false)
  const selfEmittedHtmlRef = useRef<Set<string>>(new Set())
  const lastHtmlRef = useRef(content)
  const pendingCollabSeedHtmlRef = useRef<string | null>(null)
  const prevCollaborationRef = useRef(collaboration)
  const prevEditableRef = useRef(editable)
  const lastPointerRef = useRef<{ x: number; y: number } | null>(null)
  useEffect(() => {
    onFormatTickRef.current = onFormatTick
    onLinkShortcutRef.current = onLinkShortcut
    entityTypeRef.current = entityType
    entityIdRef.current = entityId
  })

  const uploadImagesRef = useRef<(files: File[]) => Promise<void>>(async () => {})

  const collabYdoc = collaboration?.ydoc
  const collabProvider = collaboration?.provider
  const collabUserName = collaboration?.user.name
  const collabUserColor = collaboration?.user.color

  // Схема HTML↔Y.Doc в services/document-collab/src/schema.mjs должна совпадать
  // с этим набором (без Collaboration* / TabHandler / TableRowResize / BlockReorder).
  const extensions = useMemo(() => {
    const hasCollab = Boolean(collabYdoc && collabProvider && collabUserName && collabUserColor)
    const base = [
      StarterKit.configure({
        heading: false,
        link: false,
        underline: false,
        ...(hasCollab ? { undoRedo: false } : {}),
      }),
      Heading.configure({ levels: [1, 2, 3] }),
      TextAlign.configure({
        types: ['heading', 'paragraph'],
        alignments: ['left', 'center', 'right', 'justify'],
      }),
      TextStyle,
      FontSize,
      FontFamily.configure({
        types: ['textStyle'],
      }),
      Color,
      Underline,
      PortalHighlight,
      Link.configure({
        openOnClick: false,
        autolink: true,
        defaultProtocol: 'https',
        HTMLAttributes: {
          target: '_blank',
          rel: 'noopener noreferrer',
        },
      }),
      TaskList.configure({
        HTMLAttributes: { class: 'buildin-task-list' },
      }),
      TaskItem.configure({
        nested: true,
        HTMLAttributes: { class: 'buildin-task-item' },
      }),
      LineHeight,
      ParagraphIndent,
      TabHandler,
      BuildinToggle,
      DocumentImage,
      DocumentLink,
      ...portalTableExtensions,
      BlockReorder,
    ]
    if (!collabYdoc || !collabProvider || !collabUserName || !collabUserColor) return base
    return [
      ...base,
      Collaboration.configure({ document: collabYdoc }),
      CollaborationCaret.configure({
        provider: collabProvider,
        user: { name: collabUserName, color: collabUserColor },
        selectionRender: (user) => ({
          nodeName: 'span',
          class: 'collaboration-carets__selection',
          style: `background-color: color-mix(in srgb, ${user.color} 28%, transparent)`,
        }),
      }),
    ]
  }, [collabYdoc, collabProvider, collabUserName, collabUserColor])

  const editor = useEditor(
    {
      extensions,
      content: collaboration ? undefined : content,
      editable: true,
      onUpdate: ({ editor: ed }) => {
        const html = ed.getHTML()
        lastHtmlRef.current = html
        rememberEmittedRichHtml(selfEmittedHtmlRef.current, html)
        onChange(html)
      },
      editorProps: {
        attributes: {
          class: 'rich-text-prosemirror',
          'aria-keyshortcuts': 'Alt+ArrowUp Alt+ArrowDown',
        },
        handleClick: (_view, _pos, event) => interceptRichTextLinkClick(event),
        handleDOMEvents: {
          mousedown: (_view, event) => {
            lastPointerRef.current = { x: event.clientX, y: event.clientY }
            return false
          },
        },
        handleKeyDown: (_view, event) => {
          if (isBuildinToggleTitleInputTarget(event.target)) {
            return true
          }
          if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
            event.preventDefault()
            onLinkShortcutRef.current?.()
            return true
          }
          return false
        },
        handlePaste: (_view, event) => {
          if (!entityTypeRef.current) return false
          const clipboard = event.clipboardData
          if (!clipboard) return false
          const files = imageFilesFromClipboard(clipboard)
          if (files.length === 0) return false
          event.preventDefault()
          void uploadImagesRef.current(files)
          return true
        },
      },
    },
    [extensions],
  )

  const uploadImages = useCallback(
    async (files: File[]) => {
      const imageFiles = files.filter((f) => f.type.startsWith('image/'))
      if (imageFiles.length === 0) return
      if (editor && entityType && entityId) {
        await uploadAndInsertRichTextImages(editor, imageFiles, entityType, entityId)
      } else {
        pendingUploadsRef.current.push(...imageFiles)
      }
    },
    [editor, entityType, entityId],
  )

  useEffect(() => {
    uploadImagesRef.current = uploadImages
  }, [uploadImages])

  useEffect(() => {
    if (!editor || editor.isDestroyed) return
    if (!entityType || !entityId || pendingUploadsRef.current.length === 0) return
    if (flushingUploadsRef.current) return
    flushingUploadsRef.current = true
    const files = pendingUploadsRef.current.splice(0)
    void uploadAndInsertRichTextImages(editor, files, entityType, entityId).finally(() => {
      flushingUploadsRef.current = false
      if (pendingUploadsRef.current.length > 0) {
        void uploadImages(pendingUploadsRef.current.splice(0))
      }
    })
  }, [editor, entityType, entityId, uploadImages])

  useEffect(() => {
    if (!editor || editor.isDestroyed) return
    const enteringEdit = editable && !prevEditableRef.current
    prevEditableRef.current = editable
    editor.setEditable(editable)
    const clickMappedPos = lastPointerRef.current
      ? mapClickCoordsToDocPos(
          (coords) => editor.view.posAtCoords(coords),
          lastPointerRef.current,
        )
      : null
    if (enteringEdit) {
      lastPointerRef.current = null
    }
    applyResolvedRichTextFocus(
      editor,
      resolveRichTextFocusTarget({
        editable,
        autoFocus,
        editorAlreadyFocused: editor.isFocused,
        enteringEdit,
        clickMappedPos,
        docSize: editor.state.doc.content.size,
        nativeCaretInToggleBody: isNativeCaretInToggleBody(editor.view.dom),
      }),
    )
  }, [editor, editable, autoFocus])

  useEffect(() => {
    if (!editor) return
    const bump = () => onFormatTickRef.current?.()
    const bumpOnTransaction = ({ transaction }: { transaction: Transaction }) => {
      if (!transaction.docChanged && transaction.getMeta(columnResizingPluginKey) !== undefined) {
        return
      }
      bump()
    }
    editor.on('selectionUpdate', bump)
    editor.on('transaction', bumpOnTransaction)
    return () => {
      editor.off('selectionUpdate', bump)
      editor.off('transaction', bumpOnTransaction)
    }
  }, [editor])

  useEffect(() => {
    const wasOn = Boolean(prevCollaborationRef.current)
    const isOn = Boolean(collaboration)
    const sameDoc = isSameRichTextCollaboration(prevCollaborationRef.current, collaboration)
    prevCollaborationRef.current = collaboration
    if (sameDoc) return
    if (!wasOn && isOn) {
      pendingCollabSeedHtmlRef.current = lastHtmlRef.current || null
    } else if (wasOn && !isOn) {
      pendingCollabSeedHtmlRef.current = null
    }
  }, [collaboration])

  useEffect(() => {
    if (!editor || editor.isDestroyed || !collaboration) return
    const seed = pendingCollabSeedHtmlRef.current
    if (!seed) return
    pendingCollabSeedHtmlRef.current = null
    if (!shouldSeedCollabEditorFromLocalHtml(seed, editor.getHTML())) return
    editor.commands.setContent(seed)
    applyResolvedRichTextFocus(
      editor,
      resolveRichTextFocusTarget({
        editable,
        autoFocus,
        editorAlreadyFocused: editor.isFocused,
        enteringEdit: false,
        clickMappedPos: null,
        docSize: editor.state.doc.content.size,
        nativeCaretInToggleBody: isNativeCaretInToggleBody(editor.view.dom),
      }),
    )
  }, [editor, collaboration, editable, autoFocus])

  useEffect(() => {
    if (!editor || editor.isDestroyed) return
    // Collab: не перетирать Y.Doc внешним REST body
    if (collaboration) return
    const next = content || '<p></p>'
    if (!shouldApplyExternalRichHtml(selfEmittedHtmlRef.current, editor.getHTML(), next)) {
      return
    }
    const safeNext = sanitizeRichHtml(next)
    const wasFocused = editor.isFocused
    const prevSelection = wasFocused ? editor.state.selection : null
    editor.commands.setContent(safeNext, { emitUpdate: false })
    lastHtmlRef.current = editor.getHTML()
    selfEmittedHtmlRef.current.clear()
    if (wasFocused && prevSelection) {
      const docSize = editor.state.doc.content.size
      const from = Math.min(prevSelection.from, docSize)
      const to = Math.min(prevSelection.to, docSize)
      editor.commands.setTextSelection({ from, to })
      editor.commands.focus(undefined, { scrollIntoView: false })
    }
    requestAnimationFrame(() => onFormatTickRef.current?.())
  }, [editor, content, collaboration])

  return { editor, uploadImages }
}

function applyResolvedRichTextFocus(
  editor: NonNullable<ReturnType<typeof useEditor>>,
  target: RichTextFocusTarget,
): void {
  if (target.type === 'none') return
  requestAnimationFrame(() => {
    if (editor.isDestroyed) return
    if (target.type === 'pos') {
      editor.chain().setTextSelection(target.pos).focus(undefined, { scrollIntoView: false }).run()
      return
    }
    editor.commands.focus('end', { scrollIntoView: false })
  })
}

export function applyFontFamily(editor: ReturnType<typeof useEditor>, value: string) {
  if (!editor) return
  if (!value) {
    editor.chain().focus().unsetFontFamily().run()
    return
  }
  if (!ALLOWED_FONTS.includes(value)) return
  editor.chain().focus().setFontFamily(value).run()
}
