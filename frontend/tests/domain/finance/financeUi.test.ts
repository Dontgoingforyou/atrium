import { describe, expect, it } from 'vitest'
import {
  CONTRACT_STATUS_LABELS,
  CONTRACT_TYPE_LABELS,
  COUNTERPARTY_TYPE_LABELS,
  INVOICE_STATUS_LABELS,
  INVOICE_TYPE_LABELS,
  PAYMENT_CATEGORY_LABELS,
  PROCUREMENT_STATUS_COLORS,
  PROCUREMENT_STATUS_LABELS,
} from '../../../src/domain/finance/financeUi'

describe('CONTRACT_STATUS_LABELS', () => {
  it('возвращает правильные метки', () => {
    expect(CONTRACT_STATUS_LABELS).toEqual({
      draft: 'Черновик',
      active: 'Активный',
      completed: 'Завершён',
      cancelled: 'Отменён',
    })
  })
})

describe('CONTRACT_TYPE_LABELS / INVOICE_TYPE_LABELS', () => {
  it('типы договора и счёта', () => {
    expect(CONTRACT_TYPE_LABELS).toEqual({ active: 'Действующий', template: 'Шаблон' })
    expect(INVOICE_TYPE_LABELS).toEqual({ invoice: 'Счёт', act: 'Акт' })
  })
})

describe('INVOICE_STATUS_LABELS', () => {
  it('возвращает правильные метки', () => {
    expect(INVOICE_STATUS_LABELS).toEqual({
      draft: 'Черновик',
      sent: 'Отправлен',
      paid: 'Оплачен',
      overdue: 'Просрочен',
      cancelled: 'Отменён',
    })
  })
})

describe('COUNTERPARTY_TYPE_LABELS', () => {
  it('возвращает правильные метки', () => {
    expect(COUNTERPARTY_TYPE_LABELS).toEqual({
      vendor: 'Поставщик',
      client: 'Клиент',
      partner: 'Партнёр',
    })
  })
})

describe('PAYMENT_CATEGORY_LABELS', () => {
  it('возвращает правильные метки', () => {
    expect(PAYMENT_CATEGORY_LABELS).toEqual({
      contract: 'По договору',
      admin_expense: 'Адм. расходы',
      other: 'Прочее',
    })
  })
})

describe('PROCUREMENT_STATUS_LABELS', () => {
  it('возвращает правильные метки', () => {
    expect(PROCUREMENT_STATUS_LABELS).toEqual({
      draft: 'Черновик',
      pending_approval: 'На согласовании',
      approved: 'Утверждена',
      rejected: 'Отклонена',
      in_progress: 'В работе',
      completed: 'Завершена',
      cancelled: 'Отменена',
    })
  })
})

describe('PROCUREMENT_STATUS_COLORS', () => {
  it('нейтральные статусы не имеют цвета', () => {
    expect(PROCUREMENT_STATUS_COLORS.draft).toBeUndefined()
    expect(PROCUREMENT_STATUS_COLORS.pending_approval).toBeUndefined()
  })

  it('семантика цветов approval/reject/progress', () => {
    expect(PROCUREMENT_STATUS_COLORS.approved).toContain('color-success')
    expect(PROCUREMENT_STATUS_COLORS.completed).toContain('color-success')
    expect(PROCUREMENT_STATUS_COLORS.rejected).toContain('color-danger')
    expect(PROCUREMENT_STATUS_COLORS.in_progress).toContain('color-primary')
    expect(PROCUREMENT_STATUS_COLORS.approved).not.toBe(PROCUREMENT_STATUS_COLORS.rejected)
  })
})
