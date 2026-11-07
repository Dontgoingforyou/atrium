import { forwardRef, useRef } from 'react'

import type { PortalUser } from '../../../types/chat'
import { useMentionCombobox } from '../../common/useMentionCombobox'

type Props = Omit<
  React.TextareaHTMLAttributes<HTMLTextAreaElement>,
  'value' | 'onChange' | 'ref'
> & {
  value: string
  onChange: (next: string) => void
  users: PortalUser[]
  onPickMention: (sub: string) => void
  textareaClassName: string
}

/**
 * Поле ввода с автодополнением @упоминаний участников.
 */
export const MentionAwareTextarea = forwardRef<HTMLTextAreaElement, Props>(
  function MentionAwareTextarea(
    { value, onChange, users, onPickMention, textareaClassName, ...rest },
    ref,
  ) {
    const innerRef = useRef<HTMLTextAreaElement>(null)
    const setRefs = (el: HTMLTextAreaElement | null) => {
      innerRef.current = el
      if (typeof ref === 'function') {
        ref(el)
      } else if (ref) {
        ref.current = el
      }
    }

    const { handleChange, mentionList, mentionWrapClass } = useMentionCombobox({
      textareaRef: innerRef,
      value,
      onChange,
      users,
      onPick: onPickMention,
      withAvatar: true,
    })

    return (
      <div className={mentionWrapClass}>
        <textarea
          ref={setRefs}
          value={value}
          onChange={handleChange}
          className={textareaClassName}
          {...rest}
        />
        {mentionList}
      </div>
    )
  },
)
