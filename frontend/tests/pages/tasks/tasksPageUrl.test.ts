import { describe, expect, it } from 'vitest'
import {
  buildMyOverdueTasksPath,
  buildTasksPageUrlWithTask,
  buildTeamAssigneeOpenTasksPath,
  buildTeamAssigneeOverdueTasksPath,
  buildTeamDoneThisMonthTasksPath,
  buildTeamNoAssigneeTasksPath,
  buildTeamOpenTasksPath,
  buildTeamOverdueTasksPath,
  computeEffectiveTaskScope,
  parseAssigneeSubs,
  parseAssigneeSubsFromSearchParams,
  parseDoneThisMonthFromSearchParams,
  parseKpiOpenFromSearchParams,
  parseNoAssigneeFromSearchParams,
  parseOverdueOnlyFromSearchParams,
  parseTaskIdFromSearchParams,
  parseTaskPrioritiesFromSearchParams,
  parseTaskStatusesFromSearchParams,
  parseTaskTagIdsFromSearchParams,
  parseTaskScopeFromUrl,
  parseTasksView,
  setTruthySearchParam,
  urlIndicatesTeamScope,
} from '../../../src/pages/tasks/tasksPageUrl'
import { setRepeatedSearchParam } from '../../../src/utils/searchParamsUtils'

describe('tasksPageUrl', () => {
  it('parseTasksView', () => {
    expect(parseTasksView(null)).toBe('kanban')
    expect(parseTasksView('')).toBe('kanban')
    expect(parseTasksView('list')).toBe('list')
    expect(parseTasksView('kanban')).toBe('kanban')
    expect(parseTasksView('board')).toBe('kanban')
    expect(parseTasksView('LIST')).toBe('kanban')
  })

  it('parseTaskScopeFromUrl', () => {
    expect(parseTaskScopeFromUrl(null)).toBe('my')
    expect(parseTaskScopeFromUrl('team')).toBe('team')
    expect(parseTaskScopeFromUrl('all')).toBe('my')
    expect(parseTaskScopeFromUrl('TEAM')).toBe('my')
  })

  it('parseTaskIdFromSearchParams — только UUID', () => {
    const id = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
    expect(parseTaskIdFromSearchParams(new URLSearchParams(`task=${id}`))).toBe(id)
    expect(parseTaskIdFromSearchParams(new URLSearchParams('task='))).toBeNull()
    expect(parseTaskIdFromSearchParams(new URLSearchParams('task=not-uuid'))).toBeNull()
    expect(parseTaskIdFromSearchParams(new URLSearchParams('task=../x'))).toBeNull()
    expect(
      parseTaskIdFromSearchParams(new URLSearchParams(`task=${id}/extra`)),
    ).toBeNull()
  })

  it('parseTaskPrioritiesFromSearchParams — whitelist', () => {
    const p = new URLSearchParams('priority=high&priority=nope&priority=low&priority=MEDIUM')
    expect(parseTaskPrioritiesFromSearchParams(p)).toEqual(['high', 'low'])
  })

  it('buildTasksPageUrlWithTask кодирует id', () => {
    expect(buildTasksPageUrlWithTask('a/b')).toBe('/tasks/a%2Fb')
  })

  it('parseAssigneeSubs', () => {
    expect(parseAssigneeSubs(null)).toEqual([])
    expect(parseAssigneeSubs('user-1')).toEqual(['user-1'])
  })

  it('parseTaskStatusesAndTagIds', () => {
    const p = new URLSearchParams('status=todo&status=done&tag_id=a&tag_id=b')
    expect(parseTaskStatusesFromSearchParams(p)).toEqual(['todo', 'done'])
    expect(parseTaskTagIdsFromSearchParams(p)).toEqual(['a', 'b'])
  })

  it('urlIndicatesTeamScope', () => {
    expect(urlIndicatesTeamScope('team')).toBe(true)
    expect(urlIndicatesTeamScope(null)).toBe(false)
  })

  it('parseAssigneeSubsFromSearchParams: приоритет повторяющегося assignee_sub над легаси assignee', () => {
    const repeated = new URLSearchParams('assignee_sub=u1&assignee_sub=u2')
    expect(parseAssigneeSubsFromSearchParams(repeated)).toEqual(['u1', 'u2'])

    const legacy = new URLSearchParams('assignee=u1')
    expect(parseAssigneeSubsFromSearchParams(legacy)).toEqual(['u1'])

    expect(parseAssigneeSubsFromSearchParams(new URLSearchParams())).toEqual([])
  })

  it('assignee_sub переживает round-trip запись в URL (персистентность фильтра при обновлении)', () => {
    let params = new URLSearchParams('scope=team')
    params = setRepeatedSearchParam(params, 'assignee_sub', ['u1', 'u2'])
    params.delete('assignee')

    expect(parseAssigneeSubsFromSearchParams(params)).toEqual(['u1', 'u2'])

    params = setRepeatedSearchParam(params, 'assignee_sub', ['u3'])
    expect(parseAssigneeSubsFromSearchParams(params)).toEqual(['u3'])
  })

  it('parseOverdueOnlyFromSearchParams', () => {
    expect(parseOverdueOnlyFromSearchParams(new URLSearchParams())).toBe(false)
    expect(parseOverdueOnlyFromSearchParams(new URLSearchParams('overdue=1'))).toBe(true)
    expect(parseOverdueOnlyFromSearchParams(new URLSearchParams('overdue=true'))).toBe(true)
    expect(parseOverdueOnlyFromSearchParams(new URLSearchParams('overdue=0'))).toBe(false)
    expect(parseOverdueOnlyFromSearchParams(new URLSearchParams('overdue=yes'))).toBe(false)
  })

  it('buildTeamOverdueTasksPath', () => {
    expect(buildTeamOverdueTasksPath()).toBe('/tasks?scope=team&overdue=1')
  })

  it('buildMyOverdueTasksPath', () => {
    expect(buildMyOverdueTasksPath()).toBe('/tasks?overdue=1')
  })

  it('buildTeamAssigneeOverdueTasksPath — команда, просроченные, один исполнитель', () => {
    const path = buildTeamAssigneeOverdueTasksPath('alice')
    const params = new URLSearchParams(path.slice(path.indexOf('?')))
    expect(path.startsWith('/tasks?')).toBe(true)
    expect(params.get('scope')).toBe('team')
    expect(params.get('overdue')).toBe('1')
    expect(params.get('assignee')).toBe('alice')
    expect(params.getAll('status')).toEqual([])
  })

  it('buildTeamAssigneeOverdueTasksPath кодирует спецсимволы assignee', () => {
    const path = buildTeamAssigneeOverdueTasksPath('user/sub+1')
    const params = new URLSearchParams(path.slice(path.indexOf('?')))
    expect(params.get('assignee')).toBe('user/sub+1')
    expect(params.get('scope')).toBe('team')
    expect(params.get('overdue')).toBe('1')
  })

  it('buildTeamAssigneeOpenTasksPath добавляет повторяющийся status', () => {
    const path = buildTeamAssigneeOpenTasksPath('alice', ['todo', 'in_progress'])
    const params = new URLSearchParams(path.slice(path.indexOf('?')))
    expect(path.startsWith('/tasks?')).toBe(true)
    expect(params.get('scope')).toBe('team')
    expect(params.get('assignee')).toBe('alice')
    expect(params.getAll('status')).toEqual(['todo', 'in_progress'])
  })

  it('buildTeamAssigneeOpenTasksPath без открытых колонок — без status', () => {
    const path = buildTeamAssigneeOpenTasksPath('alice', [])
    const params = new URLSearchParams(path.slice(path.indexOf('?')))
    expect(params.get('scope')).toBe('team')
    expect(params.get('assignee')).toBe('alice')
    expect(params.getAll('status')).toEqual([])
  })

  it('buildTeamAssigneeOpenTasksPath кодирует assignee', () => {
    const path = buildTeamAssigneeOpenTasksPath('user/sub+1', ['todo'])
    const params = new URLSearchParams(path.slice(path.indexOf('?')))
    expect(params.get('assignee')).toBe('user/sub+1')
    expect(params.getAll('status')).toEqual(['todo'])
  })

  it('parseDoneThisMonthFromSearchParams', () => {
    expect(parseDoneThisMonthFromSearchParams(new URLSearchParams())).toBe(false)
    expect(parseDoneThisMonthFromSearchParams(new URLSearchParams('done_this_month=1'))).toBe(true)
    expect(parseDoneThisMonthFromSearchParams(new URLSearchParams('done_this_month=true'))).toBe(true)
    expect(parseDoneThisMonthFromSearchParams(new URLSearchParams('done_this_month=0'))).toBe(false)
    expect(parseDoneThisMonthFromSearchParams(new URLSearchParams('done_this_month=yes'))).toBe(false)
  })

  it('parseNoAssigneeFromSearchParams', () => {
    expect(parseNoAssigneeFromSearchParams(new URLSearchParams())).toBe(false)
    expect(parseNoAssigneeFromSearchParams(new URLSearchParams('no_assignee=1'))).toBe(true)
    expect(parseNoAssigneeFromSearchParams(new URLSearchParams('no_assignee=true'))).toBe(true)
    expect(parseNoAssigneeFromSearchParams(new URLSearchParams('no_assignee=0'))).toBe(false)
    expect(parseNoAssigneeFromSearchParams(new URLSearchParams('no_assignee=yes'))).toBe(false)
  })

  it('parseKpiOpenFromSearchParams', () => {
    expect(parseKpiOpenFromSearchParams(new URLSearchParams())).toBe(false)
    expect(parseKpiOpenFromSearchParams(new URLSearchParams('kpi_open=1'))).toBe(true)
    expect(parseKpiOpenFromSearchParams(new URLSearchParams('kpi_open=true'))).toBe(true)
    expect(parseKpiOpenFromSearchParams(new URLSearchParams('kpi_open=0'))).toBe(false)
    expect(parseKpiOpenFromSearchParams(new URLSearchParams('kpi_open=yes'))).toBe(false)
  })

  it('buildTeamOpenTasksPath — KPI-открытые без status= колонок', () => {
    expect(buildTeamOpenTasksPath()).toBe('/tasks?scope=team&kpi_open=1')
    expect(buildTeamOpenTasksPath()).not.toMatch(/status=/)
  })

  it('buildTeamDoneThisMonthTasksPath', () => {
    expect(buildTeamDoneThisMonthTasksPath()).toBe('/tasks?scope=team&done_this_month=1')
  })

  it('buildTeamNoAssigneeTasksPath', () => {
    expect(buildTeamNoAssigneeTasksPath()).toBe('/tasks?scope=team&no_assignee=1')
  })

  it('setTruthySearchParam ставит и снимает флаг', () => {
    const on = setTruthySearchParam(new URLSearchParams('scope=team'), 'done_this_month', true)
    expect(on.get('done_this_month')).toBe('1')
    expect(on.get('scope')).toBe('team')
    const off = setTruthySearchParam(on, 'done_this_month', false)
    expect(off.get('done_this_month')).toBeNull()
    expect(off.get('scope')).toBe('team')
  })

  it('computeEffectiveTaskScope', () => {
    expect(computeEffectiveTaskScope({ urlTeam: false, taskScope: 'my', canUseTeamScope: false })).toBe('my')
    expect(computeEffectiveTaskScope({ urlTeam: true, taskScope: 'my', canUseTeamScope: false })).toBe('my')
    expect(computeEffectiveTaskScope({ urlTeam: true, taskScope: 'my', canUseTeamScope: true })).toBe('team')
    expect(computeEffectiveTaskScope({ urlTeam: false, taskScope: 'team', canUseTeamScope: true })).toBe('team')
    expect(computeEffectiveTaskScope({ urlTeam: false, taskScope: 'my', canUseTeamScope: true })).toBe('my')
  })
})
