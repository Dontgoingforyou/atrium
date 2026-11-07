import styles from '@/styles/modules/tasks/RichTextEditor.module.css'

/** Lightbox для изображений в TipTap NodeView (без React). */
export function openRichTextImageLightbox(src: string, alt = ''): void {
  const overlay = document.createElement('div')
  overlay.className = styles.lightbox
  overlay.setAttribute('role', 'dialog')
  overlay.setAttribute('aria-modal', 'true')
  overlay.setAttribute('aria-label', alt || 'Изображение')

  const closeBtn = document.createElement('button')
  closeBtn.type = 'button'
  closeBtn.className = styles.lightboxClose
  closeBtn.setAttribute('aria-label', 'Закрыть')
  closeBtn.textContent = '×'

  const img = document.createElement('img')
  img.src = src
  img.alt = alt
  img.className = styles.lightboxImg

  function close() {
    document.removeEventListener('keydown', onKey)
    overlay.remove()
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === 'Escape') close()
  }

  overlay.addEventListener('click', close)
  closeBtn.addEventListener('click', (e) => {
    e.stopPropagation()
    close()
  })
  img.addEventListener('click', (e) => e.stopPropagation())

  overlay.appendChild(closeBtn)
  overlay.appendChild(img)
  document.body.appendChild(overlay)
  document.addEventListener('keydown', onKey)
}
