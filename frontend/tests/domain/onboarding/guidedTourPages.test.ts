import { describe, expect, it } from 'vitest'

import {
  canShowContextualTourHints,
  resolveGuidedTourHintDismissLabel,
} from '../../../src/domain/onboarding/guidedTour'
import {
  canonicalTourPathname,
  resolveLocationTourPageId,
  resolveTourPageId,
  seenStepIdsAfterLinearComplete,
  seenStepIdsAfterLinearSkip,
  shouldClearHintFreeze,
  shouldStartContextualHint,
  tourLocationKey,
  unseenStepsForPage,
  type GuidedTourPageId,
} from '../../../src/domain/onboarding/guidedTourPages'
import { resolveGuidedTourSteps } from '../../../src/onboarding/steps'
import type { GuidedTourStepDef } from '../../../src/domain/onboarding/guidedTour'

function step(id: string, route?: string): GuidedTourStepDef {
  return { id, title: id, body: id, route }
}

describe('guidedTourPages', () => {
  it('canonicalTourPathname maps analytics index to timesheets', () => {
    expect(canonicalTourPathname('/analytics')).toBe('/analytics/timesheets')
    expect(canonicalTourPathname('/analytics/timesheets')).toBe('/analytics/timesheets')
    expect(canonicalTourPathname('/analytics/reports')).toBe('/analytics/reports')
  })

  it('resolveTourPageId maps route and detail ids', () => {
    expect(resolveTourPageId(step('search', '/'))).toBe('home')
    expect(resolveTourPageId(step('advanced-search', '/search'))).toBe('search')
    expect(resolveTourPageId(step('tasks-filters', '/tasks?view=kanban'))).toBe('tasks-kanban')
    expect(resolveTourPageId(step('tasks-create-form', '/tasks/new'))).toBe('tasks-create')
    expect(resolveTourPageId(step('tasks-detail-comments'))).toBe('tasks-detail')
    expect(resolveTourPageId(step('specialists-view', '/specialists?view=kanban'))).toBe('specialists')
    expect(resolveTourPageId(step('chats-sidebar', '/chats'))).toBe('chats')
    expect(resolveTourPageId(step('calendar-grid', '/calendar'))).toBe('calendar')
    expect(resolveTourPageId(step('tags-table', '/tags'))).toBe('tags')
    expect(resolveTourPageId(step('analytics-tabs', '/analytics'))).toBe('analytics-timesheets')
    expect(resolveTourPageId(step('analytics-tabs', '/analytics/timesheets'))).toBe(
      'analytics-timesheets',
    )
    expect(resolveTourPageId(step('analytics-timesheets-list', '/analytics/timesheets'))).toBe(
      'analytics-timesheets',
    )
    expect(resolveTourPageId(step('analytics-reports-table', '/analytics/reports'))).toBe(
      'analytics-reports',
    )
    expect(resolveTourPageId(step('trash-list', '/p/trash'))).toBe('trash')
    expect(resolveTourPageId(step('document-body'))).toBe('document')
    expect(resolveTourPageId(step('account-restart', '/account'))).toBe('account')
  })

  it('resolveLocationTourPageId distinguishes tasks create / detail / kanban', () => {
    expect(resolveLocationTourPageId('/', '')).toBe('home')
    expect(resolveLocationTourPageId('/search', '')).toBe('search')
    expect(resolveLocationTourPageId('/tasks', '?view=kanban')).toBe('tasks-kanban')
    expect(resolveLocationTourPageId('/tasks', '')).toBe('tasks-kanban')
    expect(resolveLocationTourPageId('/tasks/new', '')).toBe('tasks-create')
    expect(resolveLocationTourPageId('/tasks/abc-1', '')).toBe('tasks-detail')
    expect(resolveLocationTourPageId('/specialists', '?view=kanban')).toBe('specialists')
    expect(resolveLocationTourPageId('/chats', '')).toBe('chats')
    expect(resolveLocationTourPageId('/calendar', '')).toBe('calendar')
    expect(resolveLocationTourPageId('/tags', '')).toBe('tags')
    expect(resolveLocationTourPageId('/analytics', '')).toBe('analytics-timesheets')
    expect(resolveLocationTourPageId('/analytics/timesheets', '')).toBe('analytics-timesheets')
    expect(resolveLocationTourPageId('/analytics/reports', '')).toBe('analytics-reports')
    expect(resolveLocationTourPageId('/p/trash', '')).toBe('trash')
    expect(resolveLocationTourPageId('/documents/doc-1', '')).toBe('document')
    expect(resolveLocationTourPageId('/p/hr/documents/doc-1', '')).toBe('document')
    expect(resolveLocationTourPageId('/account', '')).toBe('account')
    expect(resolveLocationTourPageId('/unknown', '')).toBeNull()
  })

  it('unseenStepsForPage hides seen ids and other pages', () => {
    const steps = [
      step('search', '/'),
      step('chats-sidebar', '/chats'),
      step('chats-new', '/chats'),
    ]
    const unseen = unseenStepsForPage(steps, new Set(['chats-sidebar']), 'chats')
    expect(unseen.map((s) => s.id)).toEqual(['chats-new'])
  })

  it('skip from welcome leaves seen empty; skip at index keeps 0..N', () => {
    const steps = [step('a', '/'), step('b', '/search'), step('c', '/chats')]
    expect(seenStepIdsAfterLinearSkip(steps, 'welcome', 0)).toEqual([])
    expect(seenStepIdsAfterLinearSkip(steps, 'running', 1)).toEqual(['a', 'b'])
  })

  it('linear complete marks all step ids so unseen is empty on any page', () => {
    const managerSteps = resolveGuidedTourSteps({
      isPortalAdmin: false,
      isManagerOrAdmin: true,
      isTimesheetOnly: false,
    })
    const seen = new Set(seenStepIdsAfterLinearComplete(managerSteps))
    const pages: GuidedTourPageId[] = [
      'home',
      'search',
      'tasks-kanban',
      'tasks-create',
      'tasks-detail',
      'chats',
      'document',
      'account',
    ]
    for (const pageId of pages) {
      expect(unseenStepsForPage(managerSteps, seen, pageId)).toEqual([])
    }
  })

  it('canShowContextualTourHints only for manager/admin, not timesheet-only or regular', () => {
    expect(canShowContextualTourHints({ isManagerOrAdmin: true, isTimesheetOnly: false })).toBe(true)
    expect(canShowContextualTourHints({ isManagerOrAdmin: false, isTimesheetOnly: false })).toBe(false)
    expect(canShowContextualTourHints({ isManagerOrAdmin: false, isTimesheetOnly: true })).toBe(false)
    expect(canShowContextualTourHints({ isManagerOrAdmin: true, isTimesheetOnly: true })).toBe(false)
  })

  it('hint dismiss label is Закрыть, not skip-entire', () => {
    expect(resolveGuidedTourHintDismissLabel()).toBe('Закрыть')
  })

  it('tourLocationKey нормализует search', () => {
    expect(tourLocationKey('/chats', '')).toBe('/chats')
    expect(tourLocationKey('/tasks', '?view=kanban')).toBe('/tasks?view=kanban')
    expect(tourLocationKey('/tasks', 'view=kanban')).toBe('/tasks?view=kanban')
  })

  it('shouldStartContextualHint respects freeze, role and idle', () => {
    const base = {
      tourCompleted: true,
      canShowHints: true,
      phase: 'idle' as const,
      locationKey: '/chats',
      frozenLocationKeys: [] as string[],
      unseenCount: 2,
    }
    expect(shouldStartContextualHint(base)).toBe(true)
    expect(shouldStartContextualHint({ ...base, tourCompleted: false })).toBe(false)
    expect(shouldStartContextualHint({ ...base, canShowHints: false })).toBe(false)
    expect(shouldStartContextualHint({ ...base, phase: 'running' })).toBe(false)
    expect(shouldStartContextualHint({ ...base, unseenCount: 0 })).toBe(false)
    expect(shouldStartContextualHint({ ...base, frozenLocationKeys: ['/', '/chats'] })).toBe(false)
    expect(shouldClearHintFreeze(['/'], '/chats')).toBe(true)
    expect(shouldClearHintFreeze(['/', '/chats'], '/chats')).toBe(false)
  })
})
