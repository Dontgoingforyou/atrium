import { describe, expect, it } from 'vitest'
import {
  ANALYTICS_NAV_FROM,
  HOME_DASHBOARD_NAV_FROM,
  analyticsNavState,
  buildTaskOpenNavState,
  getHomeDashboardRestore,
  getTasksReturnTo,
  homeDashboardNavState,
  isAnalyticsNav,
  isHomeDashboardNav,
  pickTaskBackNavState,
  resolveTaskBackNav,
} from '../../../src/pages/tasks/taskBackNav'

describe('taskBackNav', () => {
  it('homeDashboardNavState возвращает константу from', () => {
    expect(homeDashboardNavState()).toEqual({ from: HOME_DASHBOARD_NAV_FROM })
  })

  it('analyticsNavState возвращает константу from', () => {
    expect(analyticsNavState()).toEqual({ from: ANALYTICS_NAV_FROM })
  })

  it('isHomeDashboardNav распознаёт state с дашборда', () => {
    expect(isHomeDashboardNav({ from: HOME_DASHBOARD_NAV_FROM })).toBe(true)
    expect(isHomeDashboardNav({ from: 'other' })).toBe(false)
    expect(isHomeDashboardNav(null)).toBe(false)
    expect(isHomeDashboardNav(undefined)).toBe(false)
  })

  it('isAnalyticsNav распознаёт state из аналитики', () => {
    expect(isAnalyticsNav({ from: ANALYTICS_NAV_FROM })).toBe(true)
    expect(isAnalyticsNav({ from: HOME_DASHBOARD_NAV_FROM })).toBe(false)
    expect(isAnalyticsNav(null)).toBe(false)
  })

  it('pickTaskBackNavState отфильтровывает чужой state', () => {
    expect(pickTaskBackNavState({ from: HOME_DASHBOARD_NAV_FROM, extra: 1 })).toEqual(
      homeDashboardNavState(),
    )
    expect(pickTaskBackNavState({ from: ANALYTICS_NAV_FROM, extra: 1 })).toEqual(analyticsNavState())
    expect(pickTaskBackNavState({ foo: 'bar' })).toBeUndefined()
  })

  it('buildTaskOpenNavState сохраняет scope=team со списка задач', () => {
    expect(
      buildTaskOpenNavState({
        pathname: '/tasks',
        search: '?scope=team',
        state: null,
      }),
    ).toEqual({ tasksReturnTo: '/tasks?scope=team' })
  })

  it('buildTaskOpenNavState пробрасывает tasksReturnTo между карточками задач', () => {
    expect(
      buildTaskOpenNavState({
        pathname: '/tasks/sub-1',
        search: '',
        state: { tasksReturnTo: '/tasks?scope=team&view=kanban' },
      }),
    ).toEqual({ tasksReturnTo: '/tasks?scope=team&view=kanban' })
  })

  it('buildTaskOpenNavState совмещает возврат на список и from дашборда', () => {
    expect(
      buildTaskOpenNavState({
        pathname: '/tasks',
        search: '?scope=team',
        state: homeDashboardNavState(),
      }),
    ).toEqual({
      from: HOME_DASHBOARD_NAV_FROM,
      tasksReturnTo: '/tasks?scope=team',
    })
  })

  it('getTasksReturnTo принимает только безопасные пути /tasks…', () => {
    expect(getTasksReturnTo({ tasksReturnTo: '/tasks?scope=team' })).toBe('/tasks?scope=team')
    expect(getTasksReturnTo({ tasksReturnTo: '/tasks/abc' })).toBe('/tasks/abc')
    expect(getTasksReturnTo({ tasksReturnTo: '/tasks' })).toBe('/tasks')
    expect(getTasksReturnTo({ tasksReturnTo: '/analytics' })).toBeUndefined()
    expect(getTasksReturnTo({ tasksReturnTo: '/taskscript' })).toBeUndefined()
    expect(getTasksReturnTo({ tasksReturnTo: '/tasks/../admin' })).toBeUndefined()
    expect(getTasksReturnTo({ tasksReturnTo: 'https://evil/tasks' })).toBeUndefined()
    expect(getTasksReturnTo({ tasksReturnTo: '//evil.com' })).toBeUndefined()
    expect(getTasksReturnTo({ tasksReturnTo: 1 as unknown as string })).toBeUndefined()
    expect(getTasksReturnTo(null)).toBeUndefined()
  })

  it('resolveTaskBackNav выбирает подпись и путь', () => {
    expect(resolveTaskBackNav(homeDashboardNavState())).toEqual({
      label: '← Вернуться к дашборду',
      to: '/',
      state: { from: HOME_DASHBOARD_NAV_FROM },
    })
    expect(resolveTaskBackNav(analyticsNavState())).toEqual({
      label: '← Вернуться в раздел аналитики',
      to: '/analytics/timesheets',
    })
    expect(resolveTaskBackNav(undefined)).toEqual({
      label: '← Задачи',
      to: '/tasks',
    })
    expect(
      resolveTaskBackNav({
        from: HOME_DASHBOARD_NAV_FROM,
        tasksReturnTo: '/tasks?scope=team',
      }),
    ).toEqual({
      label: '← Задачи',
      to: '/tasks?scope=team',
    })
  })

  it('homeDashboardNavState сохраняет restore-поля', () => {
    expect(
      homeDashboardNavState({
        homeAssigneeSub: 'u1',
        homeScrollTop: 120,
        homeListMode: 'overdue',
        homeStatusKeys: ['todo'],
      }),
    ).toEqual({
      from: HOME_DASHBOARD_NAV_FROM,
      homeAssigneeSub: 'u1',
      homeScrollTop: 120,
      homeListMode: 'overdue',
      homeStatusKeys: ['todo'],
    })
  })

  it('resolveTaskBackNav без tasksReturnTo идёт на дашборд даже если в сыром state есть возврат на список', () => {
    expect(
      resolveTaskBackNav(
        pickTaskBackNavState({
          from: HOME_DASHBOARD_NAV_FROM,
          tasksReturnTo: '/tasks?scope=team',
          homeAssigneeSub: 'u1',
        }),
      ),
    ).toEqual({
      label: '← Вернуться к дашборду',
      to: '/',
      state: {
        from: HOME_DASHBOARD_NAV_FROM,
        homeAssigneeSub: 'u1',
      },
    })
  })

  it('resolveTaskBackNav пробрасывает restore на дашборд', () => {
    const restore = {
      from: HOME_DASHBOARD_NAV_FROM,
      homeAssigneeSub: 'ksyu',
      homeScrollTop: 400,
    }
    expect(resolveTaskBackNav(restore)).toEqual({
      label: '← Вернуться к дашборду',
      to: '/',
      state: {
        from: HOME_DASHBOARD_NAV_FROM,
        homeAssigneeSub: 'ksyu',
        homeScrollTop: 400,
      },
    })
  })

  it('getHomeDashboardRestore отбрасывает битые поля', () => {
    expect(
      getHomeDashboardRestore({
        from: HOME_DASHBOARD_NAV_FROM,
        homeScrollTop: Number.NaN,
        homeListMode: 'weird' as 'open',
        homeStatusKeys: [1 as unknown as string],
      }),
    ).toEqual({})
    expect(
      getHomeDashboardRestore({
        from: HOME_DASHBOARD_NAV_FROM,
        homeAssigneeSub: 'u1',
        homeScrollTop: 10,
        homeListMode: 'open',
        homeStatusKeys: ['todo'],
      }),
    ).toEqual({
      homeAssigneeSub: 'u1',
      homeScrollTop: 10,
      homeListMode: 'open',
      homeStatusKeys: ['todo'],
    })
  })
})
