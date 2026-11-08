import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { PortalUserShort } from '../../api/usersApi'
import { listPortalStudentSpecialists } from '../../api/usersApi'
import { SearchableMultiPicker } from './SearchableMultiPicker'
import type { SearchablePickerOption } from './searchablePickerUtils'
import { getUserDisplayLabel } from '../../utils/userLabel'
import { renderUserOption } from './userPickerOption'
import { specialistStudentsFilterQueryKey } from '@/pages/specialists/specialistQueryKeys'

interface SpecialistMultiPickerProps {
  value: string[]
  onChange: (subs: string[]) => void
  placeholder?: string
  chipsPosition?: 'below' | 'right'
}

/** Мультипикер специалистов — тот же UX, что UserMultiPicker на задачах. */
export function SpecialistMultiPicker({
  value,
  onChange,
  placeholder = 'Все — начните вводить имя…',
  chipsPosition,
}: SpecialistMultiPickerProps) {
  const { data, isPending, isError } = useQuery({
    queryKey: specialistStudentsFilterQueryKey(),
    queryFn: () => listPortalStudentSpecialists({ limit: 200, skip: 0 }),
    staleTime: 60_000,
  })

  const users = useMemo(() => data?.items ?? [], [data?.items])

  const options: SearchablePickerOption[] = useMemo(
    () =>
      users.map((u) => ({
        value: u.sub,
        label: getUserDisplayLabel(u),
        secondary: u.email,
      })),
    [users],
  )

  const userBySub = useMemo(() => {
    const m = new Map<string, PortalUserShort>()
    for (const u of users) {
      m.set(u.sub, u)
    }
    return m
  }, [users])

  return (
    <SearchableMultiPicker
      value={value}
      onChange={onChange}
      options={options}
      placeholder={placeholder}
        loading={isPending}
        error={isError}
        minDropdownWidth={420}
      chipsAriaLabel="Выбранные специалисты"
      chipsPosition={chipsPosition}
      renderOption={(opt, pick, a11y) => renderUserOption(opt, pick, a11y, userBySub.get(opt.value))}
    />
  )
}
