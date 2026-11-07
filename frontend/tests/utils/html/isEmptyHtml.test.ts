import { describe, expect, it } from 'vitest'
import { isEmptyHtml } from '@/utils/html/isEmptyHtml'

describe('isEmptyHtml', () => {
  it('возвращает true для пустой строки', () => {
    expect(isEmptyHtml('')).toBe(true)
  })

  it('возвращает true для пустого параграфа <p></p>', () => {
    expect(isEmptyHtml('<p></p>')).toBe(true)
  })

  it('возвращает true для HTML только с пробелами', () => {
    expect(isEmptyHtml(' ')).toBe(true)
    expect(isEmptyHtml('  \n  ')).toBe(true)
  })

  it('возвращает true для пустого toggle «Новый раздел»', () => {
    expect(
      isEmptyHtml(
        '<details class="buildin-toggle" open><summary>Новый раздел</summary><div class="buildin-toggle-body"><p></p></div></details>',
      ),
    ).toBe(true)
  })

  it('возвращает false для toggle с текстом в теле', () => {
    expect(
      isEmptyHtml(
        '<details class="buildin-toggle" open><summary>Новый раздел</summary><div class="buildin-toggle-body"><p>Текст</p></div></details>',
      ),
    ).toBe(false)
  })

  it('возвращает false для toggle с изменённым заголовком', () => {
    expect(
      isEmptyHtml(
        '<details class="buildin-toggle" open><summary>Раздел 1</summary><div class="buildin-toggle-body"><p></p></div></details>',
      ),
    ).toBe(false)
  })

  it('возвращает false для строки с текстом', () => {
    expect(isEmptyHtml('<p>Текст</p>')).toBe(false)
  })

  it('возвращает false для HTML с содержимым', () => {
    expect(isEmptyHtml('<p>Задача выполнена</p>')).toBe(false)
  })

  it('возвращает false для непустого тега с атрибутами', () => {
    expect(isEmptyHtml('<p class="foo">текст</p>')).toBe(false)
  })

  it('возвращает false для HTML только с изображением', () => {
    expect(
      isEmptyHtml(
        '<figure class="buildin-figure" data-align="center"><img class="buildin-inline-image" src="/api/v1/portal/rich-media/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/file" alt=""></figure>',
      ),
    ).toBe(false)
  })

  it('возвращает false для HTML с img без текста', () => {
    expect(isEmptyHtml('<p><img src="https://example.com/a.png" alt=""></p>')).toBe(false)
  })
})
