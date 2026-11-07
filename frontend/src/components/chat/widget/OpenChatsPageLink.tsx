import { Link } from 'react-router'

import { chatsPageHref } from '@/utils/chat/chatsNavigation'

type Props = {
  chatId?: string | null
  className?: string
  onNavigate?: () => void
  children?: React.ReactNode
}

export function OpenChatsPageLink({
  chatId,
  className,
  onNavigate,
  children = 'Открыть в чатах',
}: Props) {
  return (
    <Link to={chatsPageHref(chatId)} className={className} onClick={onNavigate}>
      {children}
    </Link>
  )
}
