import { describe, expect, it, vi } from 'vitest'

vi.mock('@/api/rawClient', () => ({
  authenticatedFetch: vi.fn(),
}))

vi.mock('@/utils/downloadBlob', () => ({
  filenameFromContentDisposition: vi.fn(() => 'bench_dashboard.csv'),
  triggerBlobDownload: vi.fn(),
}))

import { authenticatedFetch } from '@/api/rawClient'
import { buildBenchQuery, exportBenchDashboard, fetchBenchDashboard } from '@/api/bench/benchApi'
import { benchDashboardQueryKey, PORTAL_BENCH_DASHBOARD_ROOT_QUERY_KEY } from '@/api/bench/benchQueryKeys'
import { triggerBlobDownload } from '@/utils/downloadBlob'

describe('buildBenchQuery', () => {
  it('собирает фильтры и пропускает неполный период', () => {
    expect(buildBenchQuery({ year: 2026, specializations: ['iOS'], month: 1 })).toBe(
      'year=2026&specialization=iOS&month=1',
    )
    expect(buildBenchQuery({ specializations: ['iOS', 'Android'] })).toBe(
      'specialization=iOS&specialization=Android',
    )
    expect(buildBenchQuery({ dateFrom: '2026-01-01' })).toBe('')
    expect(buildBenchQuery({ dateFrom: '2026-01-01', dateTo: '2026-01-31' })).toBe(
      'date_from=2026-01-01&date_to=2026-01-31',
    )
  })
})

describe('benchDashboardQueryKey', () => {
  it('не использует литерал ключа в компоненте — корень стабилен', () => {
    const key = benchDashboardQueryKey({ year: 2025 })
    expect(key[0]).toBe(PORTAL_BENCH_DASHBOARD_ROOT_QUERY_KEY[0])
    expect(key[1]).toBe('bench')
    expect(key[3]).toEqual({ year: 2025 })
  })
})

describe('benchApi', () => {
  it('fetchBenchDashboard ходит в dashboard с query', async () => {
    vi.mocked(authenticatedFetch).mockResolvedValue(
      new Response(JSON.stringify({ years: [2025], cards: { offers: 1 } }), { status: 200 }),
    )
    const body = await fetchBenchDashboard({ year: 2025 })
    expect(authenticatedFetch).toHaveBeenCalledWith('/portal/bench/dashboard?year=2025')
    expect(body.years).toEqual([2025])
  })

  it('exportBenchDashboard скачивает файл и бросает на 403', async () => {
    vi.mocked(authenticatedFetch).mockResolvedValueOnce(
      new Response(new Blob(['csv']), {
        status: 200,
        headers: { 'Content-Disposition': 'attachment; filename="bench_dashboard.csv"' },
      }),
    )
    await exportBenchDashboard({ year: 2025 }, 'csv')
    expect(triggerBlobDownload).toHaveBeenCalled()

    vi.mocked(authenticatedFetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ code: 'forbidden', message: 'Нет прав' }), { status: 403 }),
    )
    await expect(exportBenchDashboard({}, 'xlsx')).rejects.toThrow()
  })
})
