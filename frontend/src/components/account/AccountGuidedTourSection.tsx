import { useRestartGuidedTour } from '../../onboarding/useRestartGuidedTour'
import styles from '@/styles/modules/account/AccountSettingsPage.module.css'

export function AccountGuidedTourSection() {
  const { restart, isPending } = useRestartGuidedTour()

  return (
    <section className={styles.section} aria-labelledby="account-guided-tour-heading">
      <h2 id="account-guided-tour-heading" className="section-heading">
        Обучение
      </h2>
      <div className={styles.stack}>
        <p className={styles.lead}>
          Повторно пройти интерактивный тур по основным разделам портала. Данные при обучении не
          изменяются.
        </p>
        <button
          type="button"
          className={`btn-secondary ${styles.actionBtn} ${styles.tourRestartBtn}`}
          data-tour="account-restart-tour"
          disabled={isPending}
          onClick={() => restart()}
        >
          {isPending ? 'Запуск…' : 'Пройти обучение заново'}
        </button>
      </div>
    </section>
  )
}
