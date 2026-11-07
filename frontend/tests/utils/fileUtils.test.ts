import { describe, expect, it } from 'vitest'

import { fileChipIcon, fileIcon, formatBytes } from '../../src/utils/fileUtils'

describe('formatBytes', () => {
  it('Б / КБ / МБ', () => {
    expect(formatBytes(0)).toBe('0 Б')
    expect(formatBytes(500)).toBe('500 Б')
    expect(formatBytes(1023)).toBe('1023 Б')
    expect(formatBytes(1024)).toBe('1.0 КБ')
    expect(formatBytes(2048)).toBe('2.0 КБ')
    expect(formatBytes(2 * 1024 * 1024)).toBe('2.0 МБ')
  })
})

describe('fileIcon / fileChipIcon', () => {
  it('маппит content_type на эмодзи', () => {
    expect(fileIcon('image/png')).toBe('🖼')
    expect(fileIcon('application/pdf')).toBe('📕')
    expect(fileIcon('application/msword')).toBe('📝')
    expect(fileIcon('application/vnd.ms-excel')).toBe('📊')
    expect(fileIcon('application/vnd.ms-powerpoint')).toBe('📈')
    expect(fileIcon('video/mp4')).toBe('🎬')
    expect(fileIcon('audio/mpeg')).toBe('🎵')
    expect(fileIcon('application/zip')).toBe('🗜')
    expect(fileIcon('application/x-rar-compressed')).toBe('🗜')
    expect(fileIcon('text/plain')).toBe('📄')
    expect(fileIcon('application/octet-stream')).toBe('📄')
  })

  it('fileChipIcon делегирует в fileIcon', () => {
    const file = { type: 'image/jpeg' } as File
    expect(fileChipIcon(file)).toBe('🖼')
  })
})
