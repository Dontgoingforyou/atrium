import { useRef } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'

import { uploadMyAvatar } from '../../api/usersApi'
import { patchPortalUserInCache } from '../../api/queryKeys'
import { useAuthStore } from '../../store/authStore'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { UserAvatar } from '../ui/UserAvatar'
import shared from '@/styles/modules/account/AccountSettingsPage.module.css'
import styles from '@/styles/modules/account/AccountAvatarSection.module.css'

// Зеркалит backend app.services.avatar_upload_common.AVATAR_MAX_BYTES —
// отказать заведомо слишком большому файлу до отправки, чтобы не гонять 20 МБ впустую.
const AVATAR_MAX_BYTES = 20 * 1024 * 1024

export function AccountAvatarSection() {
  const user = useAuthStore((s) => s.user)
  const patchUser = useAuthStore((s) => s.patchUser)
  const qc = useQueryClient()
  const notify = useNotifyToast()

  const fileInputRef = useRef<HTMLInputElement>(null)

  const avatarMut = useMutation({
    mutationFn: (file: File) => uploadMyAvatar(file),
    onSuccess: (data) => {
      patchUser({
        avatar_url: data.avatar_url,
        avatar_focal_x: null,
        avatar_focal_y: null,
      })
      if (user?.sub) {
        patchPortalUserInCache(qc, user.sub, {
          avatar_url: data.avatar_url,
          avatar_focal_x: null,
          avatar_focal_y: null,
        })
      }
    },
    onError: (e) => notify(userFacingMessageFromUnknown(e)),
  })

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    e.target.value = ''
    if (!f) return
    if (f.size > AVATAR_MAX_BYTES) {
      notify(`Файл слишком большой — до ${AVATAR_MAX_BYTES / (1024 * 1024)} МБ`)
      return
    }
    avatarMut.mutate(f)
  }

  return (
    <section className={`${shared.section} ${shared.sectionFirst}`} aria-labelledby="account-avatar-heading">
      <h2 id="account-avatar-heading" className="section-heading">
        Аватар
      </h2>
      <div className={styles.avatarRow}>
        <UserAvatar
          size={64}
          label={user?.full_name || user?.email || user?.username || '—'}
          imageUrl={user?.avatar_url}
          loading="eager"
          onClick={() => fileInputRef.current?.click()}
          title="Нажмите, чтобы сменить аватар"
        />
        <div>
          <button
            type="button"
            className={`btn-secondary ${styles.changeBtn}`}
            disabled={avatarMut.isPending}
            onClick={() => fileInputRef.current?.click()}
          >
            {avatarMut.isPending ? 'Загрузка…' : 'Сменить аватар'}
          </button>
          <p className={`${shared.metaText} ${styles.avatarHint}`}>
            JPG, PNG, WebP или GIF
          </p>
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        className={styles.hiddenFileInput}
        aria-hidden
        tabIndex={-1}
        onChange={handleFileChange}
      />
    </section>
  )
}
