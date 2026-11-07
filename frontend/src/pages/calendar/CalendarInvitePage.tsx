import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import { acceptCalendarInvite } from '../../api/calendar/calendarApi'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'

export function CalendarInvitePage() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  useEffect(() => {
    if (!token) return
    let cancelled = false
    void (async () => {
      try {
        const res = await acceptCalendarInvite(token)
        if (cancelled) return
        setDone(true)
        if (res.event_id) {
          navigate(`/calendar?event=${res.event_id}`, { replace: true })
        } else if (res.calendar_id) {
          navigate(`/calendar?calendar=${res.calendar_id}`, { replace: true })
        } else {
          navigate('/calendar', { replace: true })
        }
      } catch (e) {
        if (!cancelled) setError(userFacingMessageFromUnknown(e))
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token, navigate])

  if (error) {
    return (
      <div className="page-header">
        <h1 className="page-title">Приглашение</h1>
        <p role="alert">{error}</p>
      </div>
    )
  }
  return (
    <div className="page-header">
      <h1 className="page-title">Приглашение</h1>
      <p>{done ? 'Готово' : 'Принимаем приглашение…'}</p>
    </div>
  )
}
