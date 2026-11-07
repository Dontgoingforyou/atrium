import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getSpecialistJira,
  linkSpecialistJira,
  searchJiraSpecialists,
  syncSpecialistJira,
  unlinkSpecialistJira,
} from '../../api/specialists/specialistsApi'
import { useScheduleDeleteWithUndo } from '../../hooks/useScheduleDeleteWithUndo'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { normalizeHttpUrl } from '../../utils/html/normalizeHttpUrl'
import type { JiraSearchHit, SpecialistJiraState } from '../../types/specialist'
import {
  SPECIALISTS_LIST_QUERY_KEY,
  specialistJiraQueryKey,
  specialistJiraSearchQueryKey,
  specialistLinksQueryKey,
  specialistProfileQueryKey,
} from '../../pages/specialists/specialistQueryKeys'
import styles from '@/styles/modules/specialists/SpecialistDetailModal.module.css'
import jiraStyles from '@/styles/modules/specialists/SpecialistJira.module.css'
import { formatSyncedAt } from '../../domain/specialists/specialistFormat'

type Props = {
  specialistSub: string
}

function FieldValue({ value, kind }: { value: string | null; kind: string }) {
  if (!value) {
    return <span className={styles.fieldPlaceholder}>Не заполнено</span>
  }
  if (kind === 'url') {
    const href = normalizeHttpUrl(value)
    if (!href) {
      return <span>{value}</span>
    }
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className={jiraStyles.jiraFieldLink}>
        {value}
      </a>
    )
  }
  return <span>{value}</span>
}

export function SpecialistJiraSection({ specialistSub }: Props) {
  const queryClient = useQueryClient()
  const scheduleDeleteWithUndo = useScheduleDeleteWithUndo()
  const jiraQk = specialistJiraQueryKey(specialistSub)

  const { data: jiraState, isPending, isError, error } = useQuery({
    queryKey: jiraQk,
    queryFn: () => getSpecialistJira(specialistSub),
  })

  const [searchQ, setSearchQ] = useState('')
  const [debouncedQ, setDebouncedQ] = useState('')
  const [actionError, setActionError] = useState('')

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedQ(searchQ.trim()), 300)
    return () => window.clearTimeout(t)
  }, [searchQ])

  const { data: searchHits, isFetching: searchLoading } = useQuery({
    queryKey: specialistJiraSearchQueryKey(debouncedQ),
    queryFn: () => searchJiraSpecialists(debouncedQ),
    enabled: debouncedQ.length >= 2 && !jiraState?.jira_issue_key,
  })

  const invalidateAll = () => {
    void queryClient.invalidateQueries({ queryKey: jiraQk })
    void queryClient.invalidateQueries({ queryKey: specialistProfileQueryKey(specialistSub) })
    void queryClient.invalidateQueries({ queryKey: specialistLinksQueryKey(specialistSub) })
    void queryClient.invalidateQueries({ queryKey: SPECIALISTS_LIST_QUERY_KEY })
  }

  const linkMutation = useMutation({
    mutationFn: (issueKey: string) => linkSpecialistJira(specialistSub, issueKey),
    onSuccess: () => {
      setActionError('')
      setSearchQ('')
      invalidateAll()
    },
    onError: (e: unknown) => setActionError(userFacingMessageFromUnknown(e)),
  })

  const syncMutation = useMutation({
    mutationFn: () => syncSpecialistJira(specialistSub),
    onSuccess: () => {
      setActionError('')
      invalidateAll()
    },
    onError: (e: unknown) => setActionError(userFacingMessageFromUnknown(e)),
  })

  const unlinkMutation = useMutation({
    mutationFn: () => unlinkSpecialistJira(specialistSub),
    onSuccess: () => {
      setActionError('')
      invalidateAll()
    },
    onError: (e: unknown) => setActionError(userFacingMessageFromUnknown(e)),
  })

  function scheduleUnlink() {
    const snapshot = queryClient.getQueryData<SpecialistJiraState>(jiraQk)
    queryClient.setQueryData<SpecialistJiraState | undefined>(jiraQk, (prev) =>
      prev ? { ...prev, jira_issue_key: null, jira_browse_url: null, jira_synced_at: null, groups: [] } : prev,
    )
    scheduleDeleteWithUndo({
      message: 'Специалист отвязан от Jira',
      optimistic: () => {},
      revert: () => {
        if (snapshot) queryClient.setQueryData(jiraQk, snapshot)
      },
      commit: () => unlinkMutation.mutate(),
    })
  }

  if (isPending) return <p className="text-muted">Загрузка…</p>
  if (isError) return <p className="text-danger">{userFacingMessageFromUnknown(error)}</p>

  const linked = Boolean(jiraState?.jira_issue_key)
  const busy = linkMutation.isPending || syncMutation.isPending || unlinkMutation.isPending

  return (
    <div className={jiraStyles.jiraSection}>
      {actionError && <p className="form-error">{actionError}</p>}

      {linked ? (
        <>
          <div className={jiraStyles.jiraLinkedHeader}>
            <span className={jiraStyles.jiraBadge}>{jiraState?.jira_issue_key}</span>
            {(() => {
              const href = jiraState?.jira_browse_url ? normalizeHttpUrl(jiraState.jira_browse_url) : null
              if (!href) return null
              return (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={jiraStyles.jiraExternalLink}
                >
                  Открыть в Jira
                </a>
              )
            })()}
          </div>
          <p className={jiraStyles.jiraSyncedAt}>
            Последняя синхронизация: {formatSyncedAt(jiraState?.jira_synced_at ?? null)}
          </p>
          <div className={jiraStyles.jiraActions}>
            <button
              type="button"
              className="btn-primary"
              disabled={busy}
              onClick={() => syncMutation.mutate()}
            >
              {syncMutation.isPending ? 'Обновление…' : 'Обновить из Jira'}
            </button>
            <button
              type="button"
              className="btn-secondary"
              disabled={busy}
              onClick={scheduleUnlink}
            >
              Отвязать
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="text-muted">Найдите карточку специалиста в Jira по ФИО (кириллица).</p>
          <input
            type="search"
            className="form-input"
            placeholder="Поиск в Jira…"
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            disabled={busy}
          />
          {searchLoading && <p className="text-muted">Поиск…</p>}
          {searchHits && searchHits.length === 0 && debouncedQ.length >= 2 && (
            <p className="text-muted">Ничего не найдено</p>
          )}
          {searchHits && searchHits.length > 0 && (
            <ul className={jiraStyles.jiraSearchList}>
              {searchHits.map((hit: JiraSearchHit) => (
                <li key={hit.issue_key} className={jiraStyles.jiraSearchItem}>
                  <div className={jiraStyles.jiraSearchMeta}>
                    <strong>{hit.issue_key}</strong>
                    <span>{hit.summary}</span>
                    {hit.status_name ? <span className="text-muted">{hit.status_name}</span> : null}
                  </div>
                  <button
                    type="button"
                    className="btn-primary btn-sm"
                    disabled={busy}
                    onClick={() => linkMutation.mutate(hit.issue_key)}
                  >
                    Привязать
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      {linked && jiraState?.groups && jiraState.groups.length > 0 ? (
        <div className={jiraStyles.jiraFieldGroups}>
          {jiraState.groups.map((group) => (
            <section key={group.key} className={jiraStyles.jiraFieldGroup}>
              <h4 className={jiraStyles.jiraGroupTitle}>{group.label}</h4>
              {group.fields.map((field) => (
                <div key={field.id} className="form-label">
                  <span className="form-label-text">{field.label}</span>
                  <div className={`form-input ${styles.fieldInputReadonly}`}>
                    <FieldValue value={field.value} kind={field.kind} />
                  </div>
                </div>
              ))}
            </section>
          ))}
        </div>
      ) : null}
    </div>
  )
}
