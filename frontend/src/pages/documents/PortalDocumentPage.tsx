import { useRef } from 'react'
import { useLocation, useParams } from 'react-router'
import { useQueryClient } from '@tanstack/react-query'

import { DocumentComments } from '../../components/documents/DocumentComments'
import { TaskDetailPanel } from '../../components/tasks/detail/TaskDetailPanel'
import { DocumentFiles } from '../../components/documents/DocumentFiles'
import { DocumentHistoryDrawer } from '../../components/documents/DocumentHistoryDrawer'
import { DocumentTitleRow } from '../../components/documents/DocumentTitleRow'
import {
  DocumentBodySection,
  type DocumentBodySectionHandle,
} from '../../components/documents/DocumentBodySection'
import { DocumentChildDocumentsSection } from '../../components/documents/DocumentChildDocumentsSection'
import { DocumentTagsSection } from '../../components/documents/DocumentTagsSection'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { DocumentEditStickyChrome } from '../../components/documents/DocumentEditStickyChrome'
import { PageViewersBanner } from '../../components/common/PageViewersBanner'
import { useOpenDocumentWebSocket } from '../../hooks/useDocumentRealtimeWebSocket'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { usePortalDocumentPageData } from './usePortalDocumentPageData'
import { usePortalDocumentPageController } from './usePortalDocumentPageController'
import shell from '@/styles/modules/documents/PortalDocumentShell.module.css'
import aside from '@/styles/modules/documents/PortalDocumentAside.module.css'

export function PortalDocumentPage() {
  const { documentId } = useParams<{ documentId: string }>()
  const { key: locationKey } = useLocation()
  if (!documentId) return <p className="text-muted">Не указан документ.</p>

  return <PortalDocumentPageLoaded key={locationKey} documentId={documentId} />
}

function PortalDocumentPageLoaded({ documentId }: { documentId: string }) {
  const data = usePortalDocumentPageData(documentId)
  const qc = useQueryClient()
  const notifyToast = useNotifyToast()

  const viewers = useOpenDocumentWebSocket(data.document ? documentId : null, {
    parentDocumentId: data.document?.parent_document_id,
  })

  if (data.isError) {
    return (
      <div>
        <p className="text-danger">{userFacingMessageFromUnknown(data.error)}</p>
        <button type="button" className={shell.retryBtn} onClick={data.reloadDocument}>
          Повторить
        </button>
      </div>
    )
  }
  if (!data.document) {
    if (data.isPending || data.isFetching) return <p className={shell.loading}>Загрузка…</p>
    return (
      <div>
        <p className="text-muted">Не удалось загрузить документ.</p>
        <button type="button" className={shell.retryBtn} onClick={data.reloadDocument}>
          Повторить
        </button>
      </div>
    )
  }

  return (
    <InlineDocumentPage
      documentId={documentId}
      doc={data.document}
      canEditDocuments={data.canEditDocuments}
      currentUserSub={data.currentUserSub}
      isPortalAdmin={data.isPortalAdmin}
      resolveUserSub={data.resolveUserSub}
      avatarBySub={data.avatarBySub}
      loadPortalUsers={data.loadPortalUsers}
      qc={qc}
      notifyToast={notifyToast}
      viewers={viewers}
    />
  )
}

type PageProps = {
  documentId: string
  doc: NonNullable<ReturnType<typeof usePortalDocumentPageData>['document']>
  canEditDocuments: boolean
  currentUserSub: string
  isPortalAdmin: boolean
  resolveUserSub: (s: string) => string
  avatarBySub: Record<string, string | undefined>
  loadPortalUsers: boolean
  qc: ReturnType<typeof useQueryClient>
  notifyToast: ReturnType<typeof useNotifyToast>
  viewers: import('../../components/common/PageViewersBanner').PageViewer[]
}

function InlineDocumentPage({
  documentId,
  doc,
  canEditDocuments,
  currentUserSub,
  isPortalAdmin,
  resolveUserSub,
  avatarBySub,
  loadPortalUsers,
  qc,
  notifyToast,
  viewers,
}: PageProps) {
  const bodySectionRef = useRef<DocumentBodySectionHandle>(null)
  const ctrl = usePortalDocumentPageController(documentId, doc, qc, bodySectionRef)

  return (
    <article className={shell.page}>
      <DocumentEditStickyChrome
        breadcrumb={doc.breadcrumb ?? []}
        currentTitle={doc.title}
        toolbarSlotRef={ctrl.setToolbarSlotEl}
        toolbarOpen={ctrl.toolbarChromeOpen}
        viewersSlot={
          <PageViewersBanner
            viewers={viewers}
            currentUserSub={currentUserSub}
            appearance="avatars"
            avatarBySub={avatarBySub}
          />
        }
      />

      <div className={shell.docLayout}>
        <DocumentTitleRow
          documentId={documentId}
          data={doc}
          canEdit={canEditDocuments}
          onSaveTitle={(title) => ctrl.saveMut.mutate({ title })}
          onHistoryOpen={ctrl.historyDrawer.openDrawer}
          onToast={notifyToast}
          onDeleted={ctrl.navigateAfterTrash}
          onDeleteRevert={ctrl.onDeleteRevert}
        />

        <div className={shell.meta}>
          <span className={shell.metaDate}>
            Обновлён {new Date(doc.updated_at).toLocaleString('ru-RU')}
          </span>
        </div>

        <div data-tour="document-tags">
          <DocumentTagsSection
            key={doc.id}
            data={doc}
            canEdit={canEditDocuments}
            onSaveTagIds={(tag_ids) => ctrl.saveMut.mutate({ tag_ids })}
          />
        </div>

        <div data-tour="document-body">
          <DocumentBodySection
            ref={bodySectionRef}
            documentId={doc.id}
            body={doc.body}
            canEdit={canEditDocuments}
            isBodyEditing={ctrl.bodyEditing}
            isSaving={ctrl.saveMut.isPending}
            onSave={(body) => ctrl.saveMut.mutate({ body })}
            onFlushSave={(body) => ctrl.saveMut.mutateAsync({ body })}
            onDirtyChange={ctrl.setBodyDirty}
            onStartEdit={canEditDocuments ? ctrl.startBodyEdit : undefined}
            onRequestEndEdit={canEditDocuments ? ctrl.requestEndBodyEdit : undefined}
            unsavedDialogOpen={ctrl.unsavedExit !== null}
            toolbarSlotEl={ctrl.toolbarSlotEl}
            onToolbarChromeOpen={ctrl.setToolbarChromeOpen}
            currentUserSub={currentUserSub}
            currentUserDisplayName={resolveUserSub(currentUserSub)}
          />
        </div>

        <div className={aside.docAsideContent}>
          <DocumentChildDocumentsSection
            documentId={documentId}
            data={doc}
            canEditDocuments={canEditDocuments}
            currentUserSub={currentUserSub}
          />

          <DocumentFiles
            documentId={documentId}
            currentUserSub={currentUserSub}
            canEditDocuments={canEditDocuments}
            isPortalAdmin={isPortalAdmin}
          />

          <div className={aside.commentsBlock}>
            <TaskDetailPanel
              panelId="document-comments"
              title="Комментарии"
              tourAnchor="document-comments"
            >
              <DocumentComments
                documentId={documentId}
                currentUserSub={currentUserSub}
                resolveUserSub={resolveUserSub}
                canDeleteAny={isPortalAdmin}
                loadPortalUsers={loadPortalUsers}
              />
            </TaskDetailPanel>
          </div>
        </div>
      </div>

      {ctrl.historyDrawer.open && (
        <DocumentHistoryDrawer
          historyQuery={ctrl.historyQuery}
          resolveUserSub={resolveUserSub}
          entered={ctrl.historyDrawer.entered}
          onClose={ctrl.historyDrawer.closeDrawer}
          onTransitionEnd={ctrl.historyDrawer.onTransitionEnd}
        />
      )}

      {ctrl.unsavedExit !== null ? (
        <ConfirmDialog
          open
          title="Несохранённые изменения"
          message={
            ctrl.unsavedExit === 'navigate'
              ? 'Сохранить изменения в документе перед выходом?'
              : 'Сохранить изменения перед выходом из режима правки?'
          }
          confirmLabel="Сохранить"
          discardLabel="Не сохранять"
          cancelLabel={ctrl.unsavedExit === 'navigate' ? 'Остаться' : 'Продолжить правку'}
          disabled={ctrl.unsavedSaving || ctrl.saveMut.isPending}
          onConfirm={() => void ctrl.handleUnsavedSave()}
          onDiscard={ctrl.handleUnsavedDiscard}
          onCancel={ctrl.closeUnsavedDialog}
        />
      ) : null}
    </article>
  )
}
