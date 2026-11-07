import { useEffect, useState } from 'react'
import Picker from '@emoji-mart/react'
import i18nRu from '@emoji-mart/data/i18n/ru.json'
import type { EmojiMartData } from '@emoji-mart/data'

import { loadEmojiMartDataWithRuSearch } from '../../../utils/emojiDataRuLazy'
import styles from '@/styles/modules/chat/MessageInputEmojiPanel.module.css'

type Props = {
  theme: 'light' | 'dark'
  onEmojiSelect: (data: { native: string }) => void
  /** Ширина сетки эмодзи (по умолчанию — компактно для чата). */
  perLine?: number
  className?: string
}

export default function MessageInputEmojiPanel({
  theme,
  onEmojiSelect,
  perLine = 9,
  className,
}: Props) {
  const [data, setData] = useState<EmojiMartData | null>(null)

  useEffect(() => {
    let cancelled = false
    void loadEmojiMartDataWithRuSearch().then((d) => {
      if (!cancelled) setData(d)
    })
    return () => {
      cancelled = true
    }
  }, [])

  if (!data) {
    return <div className={[styles.loading, className].filter(Boolean).join(' ')}>Загрузка…</div>
  }

  return (
    <div className={className}>
    <Picker
      data={data}
      i18n={i18nRu}
      locale="ru"
      set="native"
      theme={theme}
      dynamicWidth={false}
      perLine={perLine}
      emojiSize={24}
      emojiButtonSize={36}
      maxFrequentRows={2}
      previewPosition="none"
      onEmojiSelect={onEmojiSelect}
    />
    </div>
  )
}
