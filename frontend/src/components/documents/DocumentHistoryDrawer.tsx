import type { UseQueryResult } from '@tanstack/react-query'
import { DocumentHistoryBlock } from './DocumentHistoryBlock'
import type { PortalDocumentHistory } from '../../types/document'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { RightDrawer } from '../ui/RightDrawer'

type Props = {
  historyQuery: UseQueryResult<PortalDocumentHistory[]>
  resolveUserSub: (s: string) => string
  entered: boolean
  onClose: () => void
  onTransitionEnd: (e: React.TransitionEvent<HTMLElement>) => void
}

export function DocumentHistoryDrawer({
  historyQuery,
  resolveUserSub,
  entered,
  onClose,
  onTransitionEnd,
}: Props) {
  return (
    <RightDrawer
      ariaLabel="История изменений документа"
      title="История изменений"
      entered={entered}
      onClose={onClose}
      onTransitionEnd={onTransitionEnd}
    >
      {historyQuery.isPending ? (
        <p className="text-muted">Загрузка истории…</p>
      ) : historyQuery.isError ? (
        <p className="text-danger">{userFacingMessageFromUnknown(historyQuery.error)}</p>
      ) : (
        <DocumentHistoryBlock entries={historyQuery.data ?? []} resolveUserSub={resolveUserSub} />
      )}
    </RightDrawer>
  )
}
