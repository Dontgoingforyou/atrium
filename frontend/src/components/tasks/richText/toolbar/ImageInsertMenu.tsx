import { useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { Editor } from '@tiptap/react'
import {
  Image as ImageIcon,
  MagnifyingGlass,
  UploadSimple,
} from '@phosphor-icons/react'
import styles from '@/styles/modules/tasks/RichTextEditorToolbar.module.css'
import { useAnchoredMenuPosition } from '@/hooks/useAnchoredMenuPosition'
import { useClickOutside } from '@/hooks/useClickOutside'
import { useMenuKeyboardNav } from '@/hooks/useMenuKeyboardNav'
import { userFacingMessageFromUnknown } from '@/utils/apiUserMessage'
import { insertDocumentImage } from '../extensions/tiptapImageExtension'
import { ImageUrlDialog } from './ImageUrlDialog'

type Props = {
  editor: Editor | null
  entityType?: 'task' | 'document'
  entityId?: string
  uploadImages?: (files: File[]) => void | Promise<void>
}

const MENU_WIDTH = 208

export function ImageInsertMenu({ editor, entityType, entityId, uploadImages }: Props) {
  const [open, setOpen] = useState(false)
  const [urlDialogOpen, setUrlDialogOpen] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [uploading, setUploading] = useState(false)
  const wrapRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const menuPos = useAnchoredMenuPosition(open, triggerRef, MENU_WIDTH, menuRef)

  useClickOutside(open, [wrapRef, menuRef], () => setOpen(false), 'mousedown')
  const { handleMenuKeyDown, handleTriggerKeyDown } = useMenuKeyboardNav(
    open,
    setOpen,
    triggerRef,
    menuRef,
  )

  const canUpload = Boolean(entityType && entityId)

  function closeMenu() {
    setOpen(false)
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? [])
    e.target.value = ''
    if (files.length === 0 || !editor || !uploadImages) return
    setUploading(true)
    setUploadError('')
    try {
      await uploadImages(files)
      closeMenu()
    } catch (err) {
      setUploadError(userFacingMessageFromUnknown(err))
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className={styles.menuWrap} ref={wrapRef}>
      <button
        ref={triggerRef}
        type="button"
        tabIndex={-1}
        title="Изображение"
        aria-label="Изображение"
        aria-haspopup="menu"
        aria-expanded={open}
        className={`${styles.toolbarBtn} ${open ? styles.toolbarBtnActive : ''}`}
        onMouseDown={(e) => {
          e.preventDefault()
          setOpen((v) => !v)
        }}
        onKeyDown={handleTriggerKeyDown}
      >
        <ImageIcon size={16} weight="regular" aria-hidden />
      </button>
      {open
        ? createPortal(
            <div
              ref={menuRef}
              className={styles.dropdownMenu}
              role="menu"
              aria-label="Вставить изображение"
              style={{ position: 'fixed', top: menuPos.top, left: menuPos.left }}
              onKeyDown={handleMenuKeyDown}
            >
              <button
                type="button"
                role="menuitem"
                className={styles.dropdownItem}
                disabled={!canUpload || uploading}
                title={
                  canUpload
                    ? 'Только фото и скриншоты: JPEG, PNG, GIF или WebP'
                    : 'Сначала сохраните задачу или документ, чтобы загрузить изображение'
                }
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  if (!canUpload) return
                  fileRef.current?.click()
                }}
              >
                <UploadSimple size={18} aria-hidden />
                <span>Загрузить с компьютера</span>
              </button>
              <button
                type="button"
                role="menuitem"
                className={styles.dropdownItem}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  closeMenu()
                  setUrlDialogOpen(true)
                }}
              >
                <MagnifyingGlass size={18} aria-hidden />
                <span>Найти в интернете</span>
              </button>
              {uploadError ? <p className={styles.dropdownError}>{uploadError}</p> : null}
            </div>,
            document.body,
          )
        : null}
      <input
        ref={fileRef}
        type="file"
        accept="image/jpeg,image/png,image/gif,image/webp"
        multiple
        className={styles.hiddenFileInput}
        onChange={(e) => void handleFileChange(e)}
      />
      <ImageUrlDialog
        open={urlDialogOpen}
        onClose={() => setUrlDialogOpen(false)}
        onInsert={(url) => {
          if (editor) insertDocumentImage(editor, url)
        }}
      />
    </div>
  )
}
