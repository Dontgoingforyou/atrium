import { useNavigationTreeWebSocket } from '../../hooks/useDocumentRealtimeWebSocket'
import { usePortalInboxWebSocket } from '../../hooks/usePortalInboxWebSocket'
import { usePresenceHeartbeat } from '../../hooks/usePresenceHeartbeat'
import { ChatInboxToastLayer } from '../chat/common/ChatInboxToastLayer'
import { FloatingDmWidget } from '../chat/widget/FloatingDmWidget'

/**
 * Хуки и UI реального времени, недоступные пользователям с ролью «students»
 * (IDP-группа students = ограниченный доступ, только таймшиты).
 * Монтируется в AppLayout только для не-students.
 */
export function PortalRealtimeFeatures() {
  usePortalInboxWebSocket()
  useNavigationTreeWebSocket()
  usePresenceHeartbeat()

  return (
    <>
      <ChatInboxToastLayer />
      <FloatingDmWidget />
    </>
  )
}
