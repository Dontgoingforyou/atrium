import { TagUsageDrawer } from '../../components/tags/TagUsageDrawer'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { TagsCreateForm } from './TagsCreateForm'
import { TagsTable } from './TagsTable'
import { useTagsPageController } from './useTagsPageController'
import styles from '@/styles/modules/tags/TagsPage.module.css'

export function TagsPage() {
  const ctrl = useTagsPageController()

  return (
    <div className={styles.page}>
      <div className="page-header">
        <h1 className="page-title">Теги</h1>
        {ctrl.canManageTags && !ctrl.showCreate ? (
          <button
            type="button"
            className={`btn-primary ${styles.pageBtn} ${styles.pageHeaderCreateBtn}`}
            data-tour="tags-create"
            onClick={() => ctrl.setShowCreate(true)}
          >
            + Создать тег
          </button>
        ) : null}
      </div>

      {ctrl.canManageTags && ctrl.showCreate ? (
        <TagsCreateForm
          name={ctrl.createName}
          color={ctrl.createColor}
          error={ctrl.createError}
          pending={ctrl.createPending}
          onNameChange={ctrl.setCreateName}
          onColorChange={ctrl.setCreateColor}
          onSubmit={ctrl.handleCreateSubmit}
          onCancel={ctrl.resetCreateForm}
        />
      ) : null}

      {ctrl.isLoading ? (
        <p className="text-muted" data-tour="tags-table">
          Загрузка…
        </p>
      ) : ctrl.isError ? (
        <p className="text-danger" data-tour="tags-table">
          {userFacingMessageFromUnknown(ctrl.error)}
        </p>
      ) : ctrl.tags.length === 0 ? (
        <p className={styles.emptyState} data-tour="tags-table">
          Тегов пока нет
        </p>
      ) : (
        <div data-tour="tags-table">
          <TagsTable
            tags={ctrl.tags}
            canManageTags={ctrl.canManageTags}
            editState={ctrl.editState}
            editError={ctrl.editError}
            updatePending={ctrl.updatePending}
            onStartEdit={ctrl.startEdit}
            onEditNameChange={ctrl.setEditName}
            onEditColorChange={ctrl.setEditColor}
            onSaveEdit={ctrl.handleSaveEdit}
            onCancelEdit={ctrl.cancelEdit}
            onRequestDelete={ctrl.requestDelete}
            onQuickColorChange={ctrl.handleQuickColorChange}
            onViewUsages={ctrl.openUsageDrawer}
          />
        </div>
      )}

      {ctrl.tagPendingDelete ? (
        <ConfirmDialog
          open
          title="Удалить тег?"
          message={`Тег «${ctrl.tagPendingDelete.name}» будет удалён без возможности восстановления.`}
          confirmLabel="Удалить"
          cancelLabel="Отмена"
          destructive
          confirmSound="error"
          disabled={ctrl.deletePending}
          onConfirm={ctrl.confirmDelete}
          onCancel={ctrl.cancelDelete}
        >
          {ctrl.deleteError ? (
            <p className="form-error" role="alert">
              {ctrl.deleteError}
            </p>
          ) : null}
          <button type="button" className={styles.viewLinksBtn} onClick={ctrl.handleViewLinksFromDelete}>
            Посмотреть связи
          </button>
        </ConfirmDialog>
      ) : null}

      {ctrl.usageDrawerOpen && ctrl.usageTag ? (
        <TagUsageDrawer
          tag={ctrl.usageTag}
          usagesQuery={ctrl.usagesQuery}
          entered={ctrl.usageDrawerEntered}
          onClose={ctrl.closeUsageDrawer}
          onTransitionEnd={ctrl.handleUsageDrawerTransitionEnd}
        />
      ) : null}
    </div>
  )
}
