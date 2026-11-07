import { describe, expect, it } from 'vitest'

import {
  userFacingMessageFromApiFailure,
  userFacingMessageFromUnknown,
} from '../../src/utils/apiUserMessage'

describe('userFacingMessageFromApiFailure', () => {
  it('500 без тела — общая формулировка', () => {
    expect(userFacingMessageFromApiFailure(500, '')).toBe(
      'Сервис временно недоступен. Попробуйте позже.',
    )
  })

  it('5xx с message от API показывает его (например 503 SSO)', () => {
    expect(
      userFacingMessageFromApiFailure(
        503,
        JSON.stringify({ code: 'service_unavailable', message: 'Проверьте SSO_SERVICE_URL' }),
      ),
    ).toBe('Проверьте SSO_SERVICE_URL')
  })

  it('берёт message из JSON для 4xx', () => {
    expect(
      userFacingMessageFromApiFailure(400, JSON.stringify({ code: 'x', message: 'Неверные данные' })),
    ).toBe('Неверные данные')
  })

  it('403 без тела — запасная формулировка', () => {
    expect(userFacingMessageFromApiFailure(403, '')).toBe('Недостаточно прав для этого действия.')
  })

  it('404 с message из API', () => {
    expect(userFacingMessageFromApiFailure(404, '{"message":"Раздел не найден"}')).toBe(
      'Раздел не найден',
    )
  })

  it('401 без тела — сессия истекла', () => {
    expect(userFacingMessageFromApiFailure(401, '')).toBe('Сессия истекла. Войдите снова.')
  })

  it('422 detail[] — msg из Pydantic', () => {
    const body = JSON.stringify({ detail: [{ msg: 'Обязательное поле' }] })
    expect(userFacingMessageFromApiFailure(422, body)).toBe('Обязательное поле')
  })

  it('500 с HTML-телом — generic, не сырой HTML', () => {
    expect(userFacingMessageFromApiFailure(500, '<html>Internal</html>')).toBe(
      'Сервис временно недоступен. Попробуйте позже.',
    )
    expect(userFacingMessageFromApiFailure(500, '<html>Internal</html>')).not.toContain('<html>')
  })
})

describe('userFacingMessageFromUnknown', () => {
  it('Failed to fetch → сеть', () => {
    expect(userFacingMessageFromUnknown(new Error('Failed to fetch'))).toBe(
      'Не удалось связаться с сервером. Проверьте сеть.',
    )
  })

  it('TypeError → сеть', () => {
    expect(userFacingMessageFromUnknown(new TypeError('Failed to fetch'))).toBe(
      'Не удалось связаться с сервером. Проверьте сеть.',
    )
  })

  it('обычный Error — message', () => {
    expect(userFacingMessageFromUnknown(new Error('Уже пользовательский текст'))).toBe(
      'Уже пользовательский текст',
    )
  })
})
