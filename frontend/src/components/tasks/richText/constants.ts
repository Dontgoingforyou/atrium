/** Дефолт маркера (совпадает с --color-rich-text-highlight в tokens.css). */
export const RICH_TEXT_DEFAULT_HIGHLIGHT_COLOR = '#fef08a'
/** Дефолт пикера цвета текста в тулбаре. */
export const RICH_TEXT_DEFAULT_TEXT_COLOR = '#2563eb'

export const FONT_SIZE_OPTIONS: { label: string; value: string }[] = [
  { label: '8', value: '8px' },
  { label: '9', value: '9px' },
  { label: '10', value: '10px' },
  { label: '11', value: '11px' },
  { label: '12', value: '12px' },
  { label: '14', value: '14px' },
  { label: '16', value: '16px' },
  { label: '18', value: '18px' },
  { label: '20', value: '20px' },
  { label: '24', value: '24px' },
  { label: '28', value: '28px' },
  { label: '32', value: '32px' },
]

export const FONT_FAMILY_OPTIONS: { label: string; value: string }[] = [
  { label: 'По умолчанию', value: '' },
  { label: 'Arial', value: 'Arial, sans-serif' },
  { label: 'Georgia', value: 'Georgia, serif' },
  { label: 'Times New Roman', value: '"Times New Roman", serif' },
  { label: 'Courier New', value: '"Courier New", monospace' },
]

export const LINE_HEIGHT_OPTIONS: { label: string; value: string }[] = [
  { label: 'Одинарный', value: '1' },
  { label: '1,15', value: '1.15' },
  { label: '1,5', value: '1.5' },
  { label: 'Двойной', value: '2' },
]

export const PARAGRAPH_STYLE_OPTIONS: { label: string; value: string }[] = [
  { label: 'Обычный текст', value: 'paragraph' },
  { label: 'Заголовок 1', value: 'h1' },
  { label: 'Заголовок 2', value: 'h2' },
  { label: 'Заголовок 3', value: 'h3' },
]

export const ALIGNMENT_OPTIONS = [
  { value: 'left' as const, title: 'По левому краю — текст слева' },
  { value: 'center' as const, title: 'По центру' },
  { value: 'right' as const, title: 'По правому краю' },
  {
    value: 'justify' as const,
    title: 'По ширине — растягивает строки с пробелами; на одном длинном слове как «слева»',
  },
]
