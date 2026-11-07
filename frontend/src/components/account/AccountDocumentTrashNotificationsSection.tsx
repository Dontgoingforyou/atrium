import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ACCOUNT_PREFERENCES_QUERY_KEY, getAccountPreferences, patchAccountPreferences } from '../../api/accountApi'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import shared from '@/styles/modules/account/AccountSettingsPage.module.css'

export function AccountDocumentTrashNotificationsSection() {
  const qc = useQueryClient()
  const notify = useNotifyToast()
  const prefsQ = useQuery({
    queryKey: ACCOUNT_PREFERENCES_QUERY_KEY,
    queryFn: getAccountPreferences,
  })

  const saveMut = useMutation({
    mutationFn: (notify_document_trash: boolean) =>
      patchAccountPreferences({ notify_document_trash }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ACCOUNT_PREFERENCES_QUERY_KEY })
    },
    onError: (e) => notify(userFacingMessageFromUnknown(e)),
  })

  const enabled = prefsQ.data?.notify_document_trash ?? true

  return (
    <section className={shared.section} aria-labelledby="account-trash-heading">
      <h2 id="account-trash-heading" className="section-heading">
        Корзина документов
      </h2>
      <p className={shared.lead}>
        Уведомление в колокольчике и Telegram, когда документ перемещают в корзину (только для администраторов).
      </p>
      {prefsQ.isPending && !prefsQ.data ? (
        <p className={shared.lead}>Загрузка…</p>
      ) : prefsQ.isError ? (
        <p className={shared.lead}>Не удалось загрузить настройку.</p>
      ) : (
        <label className={shared.checkboxLabel}>
          <input
            type="checkbox"
            checked={enabled}
            disabled={saveMut.isPending}
            onChange={() => saveMut.mutate(!enabled)}
          />
          <span>Уведомлять о перемещении документов в корзину</span>
        </label>
      )}
    </section>
  )
}
