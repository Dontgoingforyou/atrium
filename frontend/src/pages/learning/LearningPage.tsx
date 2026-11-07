import { useState, type KeyboardEvent } from 'react'
import { MaterialsTab } from './MaterialsTab'
import { ChecklistsTab } from './ChecklistsTab'
import { QuizzesTab } from './QuizzesTab'
import tabStyles from '@/styles/modules/common/Tabs.module.css'

/** UI раздела заморожен (`/learning` → `/`); не подключать в роутер без продуктовой задачи. */
const TABS = ['materials', 'checklists', 'quizzes'] as const
type Tab = (typeof TABS)[number]

const TAB_LABELS: Record<Tab, string> = {
  materials: 'Материалы',
  checklists: 'Чек-листы',
  quizzes: 'Тесты',
}

export function LearningPage() {
  const [tab, setTab] = useState<Tab>('materials')

  function handleTabKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    const idx = TABS.indexOf(tab)
    if (idx < 0) return
    if (e.key === 'ArrowRight') {
      e.preventDefault()
      setTab(TABS[(idx + 1) % TABS.length])
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault()
      setTab(TABS[(idx - 1 + TABS.length) % TABS.length])
    } else if (e.key === 'Home') {
      e.preventDefault()
      setTab(TABS[0])
    } else if (e.key === 'End') {
      e.preventDefault()
      setTab(TABS[TABS.length - 1])
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Обучение</h1>
      </div>
      <div
        className={tabStyles.tabs}
        role="tablist"
        aria-label="Разделы обучения"
        onKeyDown={handleTabKeyDown}
      >
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            tabIndex={tab === t ? 0 : -1}
            className={`${tabStyles.tab} ${tab === t ? tabStyles.tabActive : ''}`}
            onClick={() => setTab(t)}
          >
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>
      {tab === 'materials' && <MaterialsTab />}
      {tab === 'checklists' && <ChecklistsTab />}
      {tab === 'quizzes' && <QuizzesTab />}
    </div>
  )
}
