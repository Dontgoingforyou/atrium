import { useCallback, useEffect, useMemo, useState } from 'react'
import Cropper, { type Area } from 'react-easy-crop'
import styles from '@/styles/modules/layout/AvatarFocalPickModal.module.css'
import { blobToAvatarFile, cropAvatarImage } from '@/utils/avatar/cropAvatarImage'
import { userFacingMessageFromUnknown } from '@/utils/apiUserMessage'
import { Modal } from '../ui/Modal'

export type AvatarFocalPickModalProps = {
  open: boolean
  file: File | null
  onClose: () => void
  /** Обрезанный квадратный файл; focal фиксирован 0.5/0.5 после crop. */
  onConfirm: (payload: { file: File; focal: { x: number; y: number } }) => void
}

export function AvatarFocalPickModal({ open, file, onClose, onConfirm }: AvatarFocalPickModalProps) {
  const objectUrl = useMemo(() => {
    if (!file || !open) return null
    return URL.createObjectURL(file)
  }, [file, open])

  useEffect(() => {
    if (!objectUrl) return
    return () => URL.revokeObjectURL(objectUrl)
  }, [objectUrl])

  const [crop, setCrop] = useState({ x: 0, y: 0 })
  const [zoom, setZoom] = useState(1)
  const [croppedAreaPixels, setCroppedAreaPixels] = useState<Area | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) {
      setCrop({ x: 0, y: 0 })
      setZoom(1)
      setCroppedAreaPixels(null)
      setBusy(false)
      setError('')
    }
  }, [open, file])

  const onCropComplete = useCallback((_area: Area, pixels: Area) => {
    setCroppedAreaPixels(pixels)
  }, [])

  async function handleConfirm() {
    if (!file || !objectUrl || !croppedAreaPixels) return
    setBusy(true)
    setError('')
    try {
      const blob = await cropAvatarImage(objectUrl, croppedAreaPixels)
      const croppedFile = blobToAvatarFile(blob, file.name)
      onConfirm({ file: croppedFile, focal: { x: 0.5, y: 0.5 } })
    } catch (e: unknown) {
      setError(userFacingMessageFromUnknown(e))
    } finally {
      setBusy(false)
    }
  }

  if (!open || !file) return null

  return (
    <Modal title="Область аватара" maxWidth={560} onClose={onClose}>
      <p className={styles.hint}>Перетащите и масштабируйте фото — в круг попадёт выбранная область.</p>
      {objectUrl ? (
        <div className={styles.cropContainer}>
          <Cropper
            image={objectUrl}
            crop={crop}
            zoom={zoom}
            aspect={1}
            cropShape="round"
            showGrid={false}
            onCropChange={setCrop}
            onZoomChange={setZoom}
            onCropComplete={onCropComplete}
          />
        </div>
      ) : null}
      <label className={styles.zoomLabel}>
        Масштаб
        <input
          type="range"
          min={1}
          max={3}
          step={0.05}
          value={zoom}
          onChange={(e) => setZoom(Number(e.target.value))}
          className={styles.zoomRange}
        />
      </label>
      {error ? <p className={styles.error}>{error}</p> : null}
      <div className={styles.actions}>
        <button type="button" className={styles.btnSecondary} onClick={onClose} disabled={busy}>
          Отмена
        </button>
        <button
          type="button"
          className={styles.btnPrimary}
          disabled={busy || !croppedAreaPixels}
          onClick={() => void handleConfirm()}
        >
          {busy ? 'Обработка…' : 'Загрузить'}
        </button>
      </div>
    </Modal>
  )
}
