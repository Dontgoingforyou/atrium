// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'
import { sanitizeRichHtml } from '@/utils/html/sanitizeRichHtml'

describe('sanitizeRichHtml', () => {
  it('allows portal rich-media path and https images', () => {
    const id = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
    const html = `<p><img src="/api/v1/portal/rich-media/${id}/file" /><img src="https://cdn.example.com/a.png" /></p>`
    const out = sanitizeRichHtml(html)
    expect(out).toContain(`/api/v1/portal/rich-media/${id}/file`)
    expect(out).toContain('https://cdn.example.com/a.png')
  })

  it('strips javascript: links and data: images', () => {
    const html =
      '<p><a href="javascript:alert(1)">x</a><img src="data:image/png;base64,abc" /></p>'
    const out = sanitizeRichHtml(html)
    expect(out).not.toContain('javascript:')
    expect(out).not.toContain('data:')
  })

  it('adds target blank for https links', () => {
    const html = '<p><a href="https://example.com/path">link</a></p>'
    const out = sanitizeRichHtml(html)
    expect(out).toContain('target="_blank"')
    expect(out).toContain('rel="noopener noreferrer"')
  })

  it('allows mark highlight', () => {
    const html = '<p><mark style="background-color: #fef08a">x</mark></p>'
    const out = sanitizeRichHtml(html)
    expect(out).toContain('<mark')
    expect(out).toContain('background-color')
  })

  it('strips uppercase DATA: and javascript: with leading whitespace', () => {
    const html = '<p><img src="  DATA:image/png;base64,abc" /><img src="JavaScript:alert(1)" /></p>'
    const out = sanitizeRichHtml(html)
    expect(out.toLowerCase()).not.toContain('data:image')
    expect(out.toLowerCase()).not.toContain('javascript:')
  })

  it('does not register duplicate hooks across repeated imports', () => {
    // Повторный вызов sanitizeRichHtml не должен удваивать обработку атрибутов:
    // target=_blank для внешней https-ссылки должен быть установлен ровно один раз.
    const html = '<p><a href="https://example.com/path">link</a></p>'
    sanitizeRichHtml(html)
    const out = sanitizeRichHtml(html)
    const targetMatches = out.match(/target="_blank"/g) ?? []
    expect(targetMatches).toHaveLength(1)
  })

  it('strips lightbox/overlay class names used for UI spoofing', () => {
    const html = '<div class="rich-text-image-lightbox"><p class="buildin-task-item">x</p></div>'
    const out = sanitizeRichHtml(html)
    expect(out).not.toContain('rich-text-image-lightbox')
    expect(out).toContain('buildin-task-item')
  })

  it('keeps portal-doc-link and buildin-* classes', () => {
    const html =
      '<p><a class="portal-doc-link" href="/documents/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" data-document-id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee">Doc</a></p>' +
      '<ul class="buildin-task-list"><li class="buildin-task-item">a</li></ul>'
    const out = sanitizeRichHtml(html)
    expect(out).toContain('portal-doc-link')
    expect(out).toContain('buildin-task-list')
    expect(out).toContain('buildin-task-item')
  })

  it('strips transparent color and zero font-size spoofing', () => {
    const html = '<p style="color: transparent; font-size: 0px">hidden</p>'
    const out = sanitizeRichHtml(html)
    expect(out.toLowerCase()).not.toContain('transparent')
    expect(out.toLowerCase()).not.toMatch(/font-size:\s*0/)
  })

  it('strips script tags and onerror handlers', () => {
    const html =
      '<p>ok<script>alert(1)</script><img src="https://cdn.example.com/a.png" onerror="alert(2)" /></p>'
    const out = sanitizeRichHtml(html)
    expect(out.toLowerCase()).not.toContain('<script')
    expect(out.toLowerCase()).not.toContain('onerror')
    expect(out).toContain('https://cdn.example.com/a.png')
  })

  it('strips http images (only https / portal path)', () => {
    const out = sanitizeRichHtml('<p><img src="http://insecure.example/a.png" /></p>')
    expect(out).not.toContain('http://insecure.example')
  })
})
