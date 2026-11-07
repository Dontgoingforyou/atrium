export function filesFromDataTransfer(dt: DataTransfer): File[] {
  if (dt.files?.length) {
    return Array.from(dt.files)
  }
  const out: File[] = []
  for (const item of Array.from(dt.items)) {
    if (item.kind === 'file') {
      const f = item.getAsFile()
      if (f) out.push(f)
    }
  }
  return out
}
