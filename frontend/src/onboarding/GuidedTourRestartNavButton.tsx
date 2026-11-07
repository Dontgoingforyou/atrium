import { useRestartGuidedTour } from './useRestartGuidedTour'
import layoutStyles from '@/styles/modules/layout/AppLayout.module.css'

type Props = {
  className?: string
}

export function GuidedTourRestartNavButton({ className }: Props) {
  const { restart, isPending } = useRestartGuidedTour()

  return (
    <button
      type="button"
      className={className ?? layoutStyles.navBtn}
      data-tour="nav-guided-tour"
      disabled={isPending}
      onClick={() => restart()}
      title="Интерактивный тур по таймшитам и документам"
    >
      {isPending ? 'Запуск обучения…' : 'Обучение'}
    </button>
  )
}
