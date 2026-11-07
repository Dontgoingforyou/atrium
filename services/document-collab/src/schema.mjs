/**
 * Набор расширений для HTML↔Y.Doc.
 * Должен совпадать со схемой RichTextEditor
 * (`frontend/src/components/tasks/richText/useRichTextEditor.ts`),
 * без Collaboration / CollaborationCaret / TabHandler / TableRowResize.
 */
import { Color } from '@tiptap/extension-color'
import FontFamily from '@tiptap/extension-font-family'
import Heading from '@tiptap/extension-heading'
import Highlight from '@tiptap/extension-highlight'
import Link from '@tiptap/extension-link'
import { TaskItem } from '@tiptap/extension-list'
import TaskList from '@tiptap/extension-task-list'
import TextAlign from '@tiptap/extension-text-align'
import { TextStyle } from '@tiptap/extension-text-style'
import Underline from '@tiptap/extension-underline'
import StarterKit from '@tiptap/starter-kit'

import {
  BuildinToggle,
  DocumentImage,
  DocumentLink,
  FontSize,
  LineHeight,
  ParagraphIndent,
  portalTableExtensions,
} from './schema-nodes.mjs'

export const tiptapExtensions = [
  StarterKit.configure({
    heading: false,
    link: false,
    underline: false,
    undoRedo: false,
  }),
  Heading.configure({ levels: [1, 2, 3] }),
  TextAlign.configure({
    types: ['heading', 'paragraph'],
    alignments: ['left', 'center', 'right', 'justify'],
  }),
  TextStyle,
  FontSize,
  FontFamily.configure({ types: ['textStyle'] }),
  Color,
  Underline,
  Highlight.configure({ multicolor: true }),
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
  BuildinToggle,
  DocumentImage,
  DocumentLink,
  ...portalTableExtensions,
]
