import type { Area } from 'react-easy-crop'

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.addEventListener('load', () => resolve(img))
    img.addEventListener('error', reject)
    img.crossOrigin = 'anonymous'
    img.src = src
  })
}

/** Обрезать область изображения в квадратный PNG (~512px). */
export async function cropAvatarImage(
  imageSrc: string,
  pixelCrop: Area,
  outputSize = 512,
): Promise<Blob> {
  const image = await loadImage(imageSrc)
  const canvas = document.createElement('canvas')
  canvas.width = outputSize
  canvas.height = outputSize
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    throw new Error('Canvas недоступен')
  }
  ctx.drawImage(
    image,
    pixelCrop.x,
    pixelCrop.y,
    pixelCrop.width,
    pixelCrop.height,
    0,
    0,
    outputSize,
    outputSize,
  )
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error('Не удалось обрезать изображение'))
          return
        }
        resolve(blob)
      },
      'image/png',
      0.92,
    )
  })
}

export function blobToAvatarFile(blob: Blob, originalName: string): File {
  const base = originalName.replace(/\.[^.]+$/, '') || 'avatar'
  return new File([blob], `${base}-cropped.png`, { type: 'image/png' })
}
