import { DayCalendarPicker } from './DayCalendarPicker'
import dayPickerStyles from '@/styles/modules/common/DayCalendarPicker.module.css'

type Props = {
  dateFrom: string
  dateTo: string
  onChange: (from: string, to: string) => void
  pickerClassName?: string
  rowClassName?: string
  placeholder?: string
}

export function DateRangePicker({
  dateFrom,
  dateTo,
  onChange,
  pickerClassName,
  rowClassName,
  placeholder = 'Не выбрано',
}: Props) {
  const pickerClass = [dayPickerStyles.fixedWidth, pickerClassName].filter(Boolean).join(' ')
  function handleFromChange(from: string) {
    if (dateTo && from > dateTo) {
      onChange(from, from)
      return
    }
    onChange(from, dateTo)
  }

  function handleToChange(to: string) {
    if (dateFrom && to < dateFrom) {
      onChange(to, to)
      return
    }
    onChange(dateFrom, to)
  }

  return (
    <div className={rowClassName ?? 'filter-bar'}>
      <DayCalendarPicker
        label="С"
        value={dateFrom}
        maxDate={dateTo || undefined}
        onChange={handleFromChange}
        className={pickerClass}
        placeholder={placeholder}
      />
      <DayCalendarPicker
        label="По"
        value={dateTo}
        minDate={dateFrom || undefined}
        onChange={handleToChange}
        className={pickerClass}
        placeholder={placeholder}
      />
    </div>
  )
}
