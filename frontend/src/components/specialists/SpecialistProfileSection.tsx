import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isApiConflictError } from '../../api/apiConflict'
import { getSpecialistProfile, patchSpecialistProfile } from '../../api/specialists/specialistsApi'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { normalizeHttpUrl } from '../../utils/html/normalizeHttpUrl'
import { invalidatePortalSearchQueries } from '@/utils/search/invalidatePortalSearch'
import { formatBirthdate } from '../../domain/specialists/specialistFormat'
import { specialistProfileQueryKey } from '../../pages/specialists/specialistQueryKeys'
import { IconPencil } from '../icons/portalIcons'
import styles from '@/styles/modules/specialists/SpecialistDetailModal.module.css'
import profileStyles from '@/styles/modules/specialists/SpecialistProfileFields.module.css'

// ---------------------------------------------------------------------------
// Inline-редактируемое поле (стиль form-label)
// ---------------------------------------------------------------------------

type InlineFieldProps = {
  label: string
  value: string
  displayValue?: string
  type?: 'text' | 'date'
  placeholder?: string
  maxLength?: number
  canEdit: boolean
  saving?: boolean
  onSave: (val: string | null) => void
}

function InlineField({
  label, value, displayValue, type = 'text', placeholder, maxLength, canEdit, saving, onSave,
}: InlineFieldProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (editing) inputRef.current?.focus()
  }, [editing])

  function start() {
    setDraft(value)
    setEditing(true)
  }

  function commit() {
    setEditing(false)
    if (draft !== value) onSave(draft || null)
  }

  function handleKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') commit()
    if (e.key === 'Escape') { setEditing(false); setDraft(value) }
  }

  const shown = displayValue ?? (value || '—')

  return (
    <div className="form-label">
      <span className="form-label-text">{label}</span>
      <div
        className={`form-input ${canEdit ? profileStyles.fieldInputEditable : styles.fieldInputReadonly}`}
        onClick={!editing && canEdit ? start : undefined}
        title={!editing && canEdit ? 'Нажмите для редактирования' : undefined}
        role={!editing && canEdit ? 'button' : undefined}
        aria-label={!editing && canEdit ? `Редактировать ${label}` : undefined}
        tabIndex={!editing && canEdit ? 0 : undefined}
        onKeyDown={!editing && canEdit ? (e) => { if (e.key === 'Enter' || e.key === ' ') start() } : undefined}
      >
        {editing ? (
          <input
            ref={inputRef}
            type={type}
            className={profileStyles.fieldInlineInput}
            value={draft}
            placeholder={placeholder}
            maxLength={maxLength}
            disabled={saving}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={handleKey}
          />
        ) : (
          <span className={!value ? styles.fieldPlaceholder : profileStyles.fieldValueText}>{shown}</span>
        )}
        {canEdit ? <span className={profileStyles.pencilIcon} aria-hidden><IconPencil /></span> : null}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Секция профиля
// ---------------------------------------------------------------------------

export function SpecialistProfileSection({ specialistSub, canWrite }: {
  specialistSub: string
  canWrite: boolean
}) {
  const queryClient = useQueryClient()
  const profileQk = specialistProfileQueryKey(specialistSub)

  const { data: profile, isPending, isError, error } = useQuery({
    queryKey: profileQk,
    queryFn: () => getSpecialistProfile(specialistSub),
  })

  const [fieldError, setFieldError] = useState('')

  const saveMutation = useMutation({
    mutationFn: (
      data: Partial<{ birthdate: string | null; location: string | null; telegram: string | null }>,
    ) => {
      if (!profile) throw new Error('Профиль ещё не загружен')
      return patchSpecialistProfile(specialistSub, {
        ...data,
        expected_version: profile.version,
      })
    },
    onSuccess: () => {
      setFieldError('')
      void queryClient.invalidateQueries({ queryKey: profileQk })
      invalidatePortalSearchQueries(queryClient)
    },
    onError: (e: unknown) => {
      setFieldError(userFacingMessageFromUnknown(e))
      if (isApiConflictError(e)) {
        void queryClient.invalidateQueries({ queryKey: profileQk })
      }
    },
  })

  if (isPending) return <p className="text-muted">Загрузка…</p>
  if (isError) return <p className="text-danger">{userFacingMessageFromUnknown(error)}</p>

  const birthdateDisplay = formatBirthdate(profile?.birthdate)

  return (
    <div className={profileStyles.profileFields}>
      {fieldError && <p className="form-error">{fieldError}</p>}

      <div className="form-label">
        <span className="form-label-text">ФИО</span>
        <div className={`form-input ${styles.fieldInputReadonly}`}>{profile?.full_name ?? '—'}</div>
      </div>

      <div className="form-label">
        <span className="form-label-text">Email</span>
        <div className={`form-input ${styles.fieldInputReadonly}`}>{profile?.email ?? '—'}</div>
      </div>

      <div className="form-label">
        <span className="form-label-text">Дата рождения</span>
        <div className={`form-input ${styles.fieldInputReadonly}`}>
          {birthdateDisplay || '—'}
        </div>
      </div>

      <div className="form-label">
        <span className="form-label-text">Направление</span>
        <div className={`form-input ${styles.fieldInputReadonly}`}>
          {profile?.direction_title || '—'}
        </div>
      </div>

      <InlineField
        label="Город"
        value={profile?.location ?? ''}
        displayValue={profile?.location || '—'}
        placeholder="Город"
        maxLength={255}
        canEdit={canWrite && !profile?.jira_issue_key}
        saving={saveMutation.isPending}
        onSave={(val) => saveMutation.mutate({ location: val })}
      />

      <div className="form-label">
        <span className="form-label-text">Telegram</span>
        <div className={`form-input ${styles.fieldInputReadonly}`}>
          {(() => {
            const raw = profile?.telegram ?? null
            const href = raw ? normalizeHttpUrl(raw) : null
            if (!raw) return '—'
            if (!href) return <span>{raw}</span>
            return (
              <a href={href} target="_blank" rel="noopener noreferrer">
                {raw.replace(/^https:\/\/t\.me\//, 't.me/')}
              </a>
            )
          })()}
        </div>
      </div>
    </div>
  )
}
