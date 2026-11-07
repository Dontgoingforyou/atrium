import { describe, expect, it } from 'vitest'

import { htmlToPlainTextExcerpt } from '@/utils/html/richTextPlainText'

describe('htmlToPlainTextExcerpt', () => {
  it('пусто → пустая строка', () => {
    expect(htmlToPlainTextExcerpt(null)).toBe('')
    expect(htmlToPlainTextExcerpt('   ')).toBe('')
  })

  it('снимает теги и обрезает', () => {
    expect(htmlToPlainTextExcerpt('<p>Привет <b>мир</b></p>')).toBe('Привет мир')
    expect(htmlToPlainTextExcerpt('<p>' + 'x'.repeat(200) + '</p>', 10)).toBe('xxxxxxxxxx…')
  })

  it('только изображение → Изображение', () => {
    expect(htmlToPlainTextExcerpt('<img src="/a.png" />')).toBe('Изображение')
  })
})
