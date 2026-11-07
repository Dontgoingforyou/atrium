export type BuildinToggleChrome = {
  root: HTMLDivElement
  header: HTMLDivElement
  arrow: HTMLButtonElement
  titleInput: HTMLInputElement
  deleteBtn: HTMLButtonElement
  bodySlot: HTMLDivElement
  bodyClip: HTMLDivElement
  contentDOM: HTMLDivElement
}

export function createBuildinToggleChrome(title: string): BuildinToggleChrome {
  const root = document.createElement('div')
  root.className = 'buildin-toggle'
  root.contentEditable = 'false'

  const header = document.createElement('div')
  header.className = 'buildin-toggle-header'

  const arrow = document.createElement('button')
  arrow.type = 'button'
  arrow.className = 'buildin-toggle-arrow'
  arrow.title = 'Свернуть или раскрыть блок'
  arrow.setAttribute('aria-label', 'Свернуть или раскрыть блок')
  arrow.tabIndex = -1
  arrow.textContent = '▶'

  const titleInput = document.createElement('input')
  titleInput.type = 'text'
  titleInput.className = 'buildin-toggle-title-input'
  titleInput.value = title
  titleInput.placeholder = 'Заголовок'

  const deleteBtn = document.createElement('button')
  deleteBtn.type = 'button'
  deleteBtn.className = 'buildin-toggle-delete'
  deleteBtn.title = 'Удалить блок'
  deleteBtn.setAttribute('aria-label', 'Удалить раскрывающийся блок')
  deleteBtn.textContent = '×'

  header.append(arrow, titleInput, deleteBtn)

  const bodySlot = document.createElement('div')
  bodySlot.className = 'buildin-toggle-body-slot'

  const bodyClip = document.createElement('div')
  bodyClip.className = 'buildin-toggle-body-clip'

  const contentDOM = document.createElement('div')
  contentDOM.className = 'buildin-toggle-body'
  contentDOM.contentEditable = 'true'
  bodyClip.appendChild(contentDOM)
  bodySlot.appendChild(bodyClip)
  root.append(header, bodySlot)

  return { root, header, arrow, titleInput, deleteBtn, bodySlot, bodyClip, contentDOM }
}
