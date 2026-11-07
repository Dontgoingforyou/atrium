import { describe, expect, it } from 'vitest'

import { filesFromDataTransfer } from '@/pages/chats/filesFromDataTransfer'

function item(kind: string, file: File | null): DataTransferItem {
  return {
    kind,
    type: file?.type ?? '',
    getAsFile: () => file,
  } as DataTransferItem
}

describe('filesFromDataTransfer', () => {
  it('берёт dt.files, если список непустой', () => {
    const a = new File(['a'], 'a.txt', { type: 'text/plain' })
    const dt = {
      files: [a] as unknown as FileList,
      items: [] as unknown as DataTransferItemList,
    } as DataTransfer
    expect(filesFromDataTransfer(dt)).toEqual([a])
  })

  it('собирает File из items, если files пуст', () => {
    const a = new File(['a'], 'a.txt', { type: 'text/plain' })
    const dt = {
      files: [] as unknown as FileList,
      items: [item('file', a), item('string', null)] as unknown as DataTransferItemList,
    } as DataTransfer
    expect(filesFromDataTransfer(dt)).toEqual([a])
  })

  it('пропускает items без getAsFile', () => {
    const dt = {
      files: [] as unknown as FileList,
      items: [item('file', null)] as unknown as DataTransferItemList,
    } as DataTransfer
    expect(filesFromDataTransfer(dt)).toEqual([])
  })
})
