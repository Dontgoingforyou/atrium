import { describe, expect, it } from 'vitest'

import {
  advanceGuidedTourStep,
  canShowContextualTourHints,
  canSkipEntireGuidedTour,
  filterGuidedTourSteps,
  preventGuidedTourOrphans,
  resolveGuidedTourSkipLabel,
  resolveTourStepNavigationKind,
  retreatGuidedTourStep,
  shouldAutoStartGuidedTour,
  skipGuidedTourStep,
  stepNeedsTourCreateFormPage,
  stepNeedsTourDocument,
  stepNeedsTourTaskDetailPage,
  tourAnchorSelector,
  tourTaskDetailAnchorForStep,
  type GuidedTourStepDef,
} from '../../../src/domain/onboarding/guidedTour'
import {
  clampPopoverInViewport,
  fitPopoverAwayFromTarget,
  POPOVER_H,
  POPOVER_W,
  pickPopoverPlacement,
  popoverPosition,
  rectFullyInViewport,
  VIEWPORT_PAD,
} from '../../../src/utils/guidedTourLayout'
import { resolveGuidedTourSteps } from '../../../src/onboarding/steps'

describe('guidedTour domain', () => {
  it('tourAnchorSelector builds data-tour selector', () => {
    expect(tourAnchorSelector('global-search')).toBe('[data-tour="global-search"]')
  })

  it('classifies create-form and task-detail tour steps', () => {
    expect(stepNeedsTourCreateFormPage({ id: 'tasks-create-form' })).toBe(true)
    expect(stepNeedsTourCreateFormPage({ id: 'tasks-create-title' })).toBe(true)
    expect(stepNeedsTourCreateFormPage({ id: 'tasks-detail-subtasks' })).toBe(false)
    expect(stepNeedsTourTaskDetailPage({ id: 'tasks-detail-links' })).toBe(true)
    expect(stepNeedsTourTaskDetailPage({ id: 'tasks-create-form' })).toBe(false)
    expect(tourTaskDetailAnchorForStep('tasks-detail-files')).toBe('task-detail-files')
    expect(tourTaskDetailAnchorForStep('tasks-create-form')).toBeNull()
  })

  it('shouldAutoStartGuidedTour respects completed flag', () => {
    expect(shouldAutoStartGuidedTour(false)).toBe(true)
    expect(shouldAutoStartGuidedTour(true)).toBe(false)
  })

  it('filterGuidedTourSteps drops steps when when() is false', () => {
    const steps: GuidedTourStepDef[] = [
      { id: 'a', title: 'A', body: 'a' },
      { id: 'b', title: 'B', body: 'b', when: (ctx) => ctx.isPortalAdmin },
    ]
    expect(filterGuidedTourSteps(steps, {
      isPortalAdmin: false,
      isManagerOrAdmin: false,
      isTimesheetOnly: false,
    }).map((s) => s.id)).toEqual(['a'])
    expect(filterGuidedTourSteps(steps, {
      isPortalAdmin: true,
      isManagerOrAdmin: true,
      isTimesheetOnly: false,
    }).map((s) => s.id)).toEqual(['a', 'b'])
  })

  it('MVP steps differ for regular / manager / admin', () => {
    const regular = resolveGuidedTourSteps({
      isPortalAdmin: false,
      isManagerOrAdmin: false,
      isTimesheetOnly: false,
    })
    expect(regular.some((s) => s.id === 'home-new-task')).toBe(false)
    expect(regular.some((s) => s.id === 'home-admin-dashboard')).toBe(false)
    expect(regular.some((s) => s.id === 'home-manager-panel')).toBe(false)
    expect(regular.some((s) => s.id === 'tasks-scope')).toBe(false)
    expect(regular.some((s) => s.id === 'nav-specialists')).toBe(false)
    expect(regular.some((s) => s.id === 'specialists-kanban')).toBe(false)
    expect(regular.some((s) => s.id === 'nav-trash')).toBe(false)
    expect(regular.some((s) => s.id === 'trash-purge')).toBe(false)
    expect(regular.some((s) => s.id === 'nav-admin')).toBe(false)
    expect(regular.some((s) => s.id === 'tags-create')).toBe(false)
    expect(regular.some((s) => s.id === 'search')).toBe(true)
    expect(regular.some((s) => s.id === 'nav-chats')).toBe(true)
    expect(regular.some((s) => s.id === 'chats-sidebar')).toBe(true)
    expect(regular.some((s) => s.id === 'chats-composer')).toBe(true)
    expect(regular.some((s) => s.id === 'chats-messages')).toBe(true)
    expect(regular.some((s) => s.id === 'nav-calendar')).toBe(true)
    expect(regular.some((s) => s.id === 'calendar-create-event')).toBe(true)
    expect(regular.some((s) => s.id === 'calendar-day-cell')).toBe(true)
    expect(regular.some((s) => s.id === 'nav-tags')).toBe(true)
    expect(regular.some((s) => s.id === 'tags-table')).toBe(true)
    expect(regular.some((s) => s.id === 'nav-analytics')).toBe(true)
    expect(regular.find((s) => s.id === 'analytics-tabs')?.route).toBe('/analytics/timesheets')
    expect(regular.some((s) => s.id === 'analytics-summary-tasks')).toBe(false)
    expect(regular.some((s) => s.id === 'analytics-summary-timesheets')).toBe(true)
    expect(regular.some((s) => s.id === 'analytics-reports-filters')).toBe(true)
    expect(regular.some((s) => s.id === 'analytics-timesheets-month')).toBe(false)
    expect(regular.some((s) => s.id === 'nav-documents')).toBe(true)
    expect(regular.some((s) => s.id === 'document-body')).toBe(true)
    expect(regular.some((s) => s.id === 'documents-create')).toBe(false)

    const manager = resolveGuidedTourSteps({
      isPortalAdmin: false,
      isManagerOrAdmin: true,
      isTimesheetOnly: false,
    })
    expect(manager.some((s) => s.id === 'home-manager-panel')).toBe(true)
    expect(manager.some((s) => s.id === 'home-admin-dashboard')).toBe(false)
    expect(manager.some((s) => s.id === 'home-new-task')).toBe(false)
    const managerMyTasks = manager.findIndex((s) => s.id === 'home-my-tasks')
    expect(manager[managerMyTasks + 1]?.id).toBe('home-manager-panel')
    expect(manager.some((s) => s.id === 'tasks-scope')).toBe(true)
    expect(manager.some((s) => s.id === 'nav-specialists')).toBe(true)
    expect(manager.some((s) => s.id === 'specialists-kanban')).toBe(true)
    expect(manager.some((s) => s.id === 'nav-trash')).toBe(true)
    expect(manager.some((s) => s.id === 'trash-hint')).toBe(true)
    expect(manager.some((s) => s.id === 'trash-purge')).toBe(false)
    expect(manager.some((s) => s.id === 'tags-create')).toBe(true)
    expect(manager.some((s) => s.id === 'analytics-timesheets-list')).toBe(true)
    expect(manager.some((s) => s.id === 'documents-create')).toBe(true)
    expect(manager.some((s) => s.id === 'nav-admin')).toBe(false)

    const admin = resolveGuidedTourSteps({
      isPortalAdmin: true,
      isManagerOrAdmin: true,
      isTimesheetOnly: false,
    })
    expect(admin.some((s) => s.id === 'home-new-task')).toBe(true)
    expect(admin.some((s) => s.id === 'home-admin-dashboard')).toBe(true)
    expect(admin.some((s) => s.id === 'home-manager-panel')).toBe(false)
    expect(admin.some((s) => s.id === 'tasks-scope')).toBe(true)
    expect(admin.some((s) => s.id === 'nav-admin')).toBe(true)
    expect(admin.some((s) => s.id === 'trash-purge')).toBe(true)
    expect(admin.some((s) => s.id === 'specialists-filters')).toBe(true)
    expect(admin.some((s) => s.id === 'tasks-kanban-card')).toBe(true)
    expect(admin.some((s) => s.id === 'tasks-kanban-column-header')).toBe(true)
  })

  it('timesheet-only steps cover AU contour without full portal sections', () => {
    const au = resolveGuidedTourSteps({
      isPortalAdmin: false,
      isManagerOrAdmin: false,
      isTimesheetOnly: true,
    })
    expect(au.some((s) => s.id === 'nav-timesheets')).toBe(true)
    expect(au.some((s) => s.id === 'timesheets-actions')).toBe(true)
    expect(au.find((s) => s.id === 'timesheets-actions')?.selector).toContain(
      'analytics-timesheets-actions',
    )
    expect(au.some((s) => s.id === 'timesheets-report')).toBe(true)
    expect(au.find((s) => s.id === 'timesheets-report')?.route).toBe('/analytics/timesheets?tab=report')
    expect(au.some((s) => s.id === 'nav-documents')).toBe(true)
    expect(au.some((s) => s.id === 'document-body')).toBe(true)
    expect(au.some((s) => s.id === 'document-tags')).toBe(false)
    expect(au.some((s) => s.id === 'nav-chats')).toBe(false)
    expect(au.some((s) => s.id === 'tasks-create')).toBe(false)
    expect(au.some((s) => s.id === 'tasks-create-title')).toBe(false)
    expect(au.some((s) => s.id === 'tasks-detail-subtasks')).toBe(false)
    expect(au.some((s) => s.id === 'nav-guided-tour')).toBe(true)
  })

  it('role matrix: create-form fields, trash purge, specialists только у manager/admin', () => {
    const regular = resolveGuidedTourSteps({
      isPortalAdmin: false,
      isManagerOrAdmin: false,
      isTimesheetOnly: false,
    })
    const manager = resolveGuidedTourSteps({
      isPortalAdmin: false,
      isManagerOrAdmin: true,
      isTimesheetOnly: false,
    })
    const admin = resolveGuidedTourSteps({
      isPortalAdmin: true,
      isManagerOrAdmin: true,
      isTimesheetOnly: false,
    })
    expect(regular.some((s) => s.id === 'tasks-create-form')).toBe(true)
    expect(regular.find((s) => s.id === 'tasks-create-form')?.route).toBe('/tasks/new')
    const formFieldIds = [
      'tasks-create-title',
      'tasks-create-assignees',
      'tasks-create-priority',
      'tasks-create-due',
      'tasks-create-tags',
      'tasks-create-description',
    ] as const
    const detailSectionIds = [
      'tasks-detail-subtasks',
      'tasks-detail-comments',
      'tasks-detail-links',
      'tasks-detail-files',
    ] as const
    for (const id of formFieldIds) {
      expect(regular.some((s) => s.id === id)).toBe(false)
      expect(manager.some((s) => s.id === id)).toBe(true)
      expect(admin.some((s) => s.id === id)).toBe(true)
    }
    for (const id of detailSectionIds) {
      expect(regular.some((s) => s.id === id)).toBe(false)
      expect(manager.some((s) => s.id === id)).toBe(true)
      expect(admin.some((s) => s.id === id)).toBe(true)
    }
    expect(manager.some((s) => s.id === 'specialists-kanban-card')).toBe(true)
    expect(regular.some((s) => s.id === 'specialists-kanban-card')).toBe(false)
    expect(manager.find((s) => s.id === 'trash-purge')).toBeUndefined()
    expect(admin.some((s) => s.id === 'trash-purge')).toBe(true)
    expect(manager.find((s) => s.id === 'trash-hint')?.body ?? '').toContain('Восстановить')
    expect(manager.find((s) => s.id === 'trash-hint')?.body ?? '').not.toContain('Удалить навсегда')
    expect(admin.find((s) => s.id === 'trash-hint')?.body ?? '').toContain('Удалить навсегда')
    expect(regular.find((s) => s.id === 'chats-composer')?.preferPlacement).toBe('top')
    expect(regular.find((s) => s.id === 'tasks-create-form')?.preferPlacement).toBe('top')
    expect(regular.find((s) => s.id === 'chats-messages')?.revealHover).toBe(true)
  })

  it('preventGuidedTourOrphans keeps short words with next token', () => {
    expect(preventGuidedTourOrphans('режимы «По тексту» и «По смыслу»')).toContain('«По\u00a0тексту»')
    expect(preventGuidedTourOrphans('режимы «По тексту» и «По смыслу»')).toContain('«По\u00a0смыслу»')
    expect(preventGuidedTourOrphans('документах и других')).toBe('документах и\u00a0других')
    expect(preventGuidedTourOrphans('«+ Диалог» и «+ Группа»')).toContain('«+\u00a0Диалог»')
    expect(preventGuidedTourOrphans('«+ Диалог» и «+ Группа»')).toContain('«+\u00a0Группа»')
  })

  it('resolveTourStepNavigationKind: demo-chat не блокирует openFromSelector документов', () => {
    expect(
      resolveTourStepNavigationKind({
        hasDemoChatId: true,
        needsChatHref: true,
        hasOpenFromSelector: true,
      }),
    ).toBe('demo-chat')
    expect(
      resolveTourStepNavigationKind({
        hasDemoChatId: true,
        needsChatHref: false,
        hasOpenFromSelector: true,
      }),
    ).toBe('open-from-selector')
    expect(
      resolveTourStepNavigationKind({
        hasDemoChatId: false,
        needsChatHref: false,
        hasOpenFromSelector: true,
      }),
    ).toBe('open-from-selector')
    expect(
      resolveTourStepNavigationKind({
        hasDemoChatId: true,
        needsChatHref: false,
        hasOpenFromSelector: false,
      }),
    ).toBe('none')
  })

  it('stepNeedsTourDocument covers document detail steps', () => {
    expect(stepNeedsTourDocument({ id: 'document-title' })).toBe(true)
    expect(stepNeedsTourDocument({ id: 'document-tags' })).toBe(true)
    expect(stepNeedsTourDocument({ id: 'document-body' })).toBe(true)
    expect(stepNeedsTourDocument({ id: 'document-comments' })).toBe(true)
    expect(stepNeedsTourDocument({ id: 'account-restart' })).toBe(false)
    expect(stepNeedsTourDocument({ id: 'documents-create' })).toBe(false)
  })

  it('canSkipEntireGuidedTour for manager/admin and timesheet-only', () => {
    expect(canSkipEntireGuidedTour({ isManagerOrAdmin: true, isTimesheetOnly: false })).toBe(true)
    expect(canSkipEntireGuidedTour({ isManagerOrAdmin: false, isTimesheetOnly: true })).toBe(true)
    expect(canSkipEntireGuidedTour({ isManagerOrAdmin: false, isTimesheetOnly: false })).toBe(false)
  })

  it('canShowContextualTourHints only for manager/admin without AU', () => {
    expect(canShowContextualTourHints({ isManagerOrAdmin: true, isTimesheetOnly: false })).toBe(true)
    expect(canShowContextualTourHints({ isManagerOrAdmin: false, isTimesheetOnly: true })).toBe(false)
    expect(canShowContextualTourHints({ isManagerOrAdmin: true, isTimesheetOnly: true })).toBe(false)
  })

  it('resolveGuidedTourSkipLabel distinguishes entire tour vs one step', () => {
    expect(resolveGuidedTourSkipLabel(true)).toBe('Пропустить обучение')
    expect(resolveGuidedTourSkipLabel(false)).toBe('Пропустить шаг')
  })

  it('advance / retreat / skip runtime helpers', () => {
    const steps: GuidedTourStepDef[] = [
      { id: 'a', title: 'A', body: 'a' },
      { id: 'b', title: 'B', body: 'b' },
    ]
    const state = { phase: 'running' as const, stepIndex: 0, steps }
    const advanced = advanceGuidedTourStep(state)
    expect(advanced.stepIndex).toBe(1)
    const retreated = retreatGuidedTourStep(advanced)
    expect(retreated.stepIndex).toBe(0)
    expect(retreatGuidedTourStep(retreated)).toBe(retreated)
    const skipped = skipGuidedTourStep(retreated)
    expect(skipped.stepIndex).toBe(1)
    const done = advanceGuidedTourStep(skipped)
    expect(done.phase).toBe('done')
  })

  it('advance/retreat/skip вне running — no-op', () => {
    const steps: GuidedTourStepDef[] = [{ id: 'a', title: 'A', body: 'a' }]
    for (const phase of ['idle', 'welcome', 'done'] as const) {
      const state = { phase, stepIndex: 0, steps }
      expect(advanceGuidedTourStep(state)).toBe(state)
      expect(retreatGuidedTourStep(state)).toBe(state)
      expect(skipGuidedTourStep(state)).toBe(state)
    }
  })
})

describe('guidedTourLayout', () => {
  it('picks side with more free space', () => {
    const nearTopLeft = { top: 10, left: 10, right: 110, bottom: 60, width: 100, height: 50 }
    expect(pickPopoverPlacement(nearTopLeft, { width: 800, height: 600 })).toBe('right')
    const nearBottom = { top: 500, left: 350, right: 450, bottom: 550, width: 100, height: 50 }
    expect(pickPopoverPlacement(nearBottom, { width: 800, height: 600 })).toBe('top')
  })

  it('honours preferPlacement when there is enough space', () => {
    const nearTopRight = { top: 12, left: 740, right: 780, bottom: 52, width: 40, height: 40 }
    expect(pickPopoverPlacement(nearTopRight, { width: 800, height: 600 }, 'left')).toBe('left')
  })

  it('clamps popover inside viewport and avoids covering target on the right', () => {
    const target = { top: 0, left: 0, right: 40, bottom: 40, width: 40, height: 40 }
    const pos = popoverPosition(target, 'bottom', { width: 400, height: 300 })
    expect(pos.left).toBeGreaterThanOrEqual(8)
    expect(pos.top).toBeGreaterThanOrEqual(8)

    const bell = { top: 8, left: 760, right: 800, bottom: 48, width: 40, height: 40 }
    const leftPos = popoverPosition(bell, 'left', { width: 800, height: 600 })
    expect(leftPos.left + POPOVER_W).toBeLessThanOrEqual(bell.left - 6)

    const nearBottom = { top: 820, left: 200, right: 520, bottom: 880, width: 320, height: 60 }
    const topPos = popoverPosition(nearBottom, 'top', { width: 900, height: 900 })
    expect(topPos.top).toBeGreaterThanOrEqual(8)
    expect(topPos.top + POPOVER_H).toBeLessThanOrEqual(900 - 8)
  })

  it('aligns popover to the left edge of a wide target (top/bottom)', () => {
    const wide = { top: 200, left: 240, right: 1200, bottom: 360, width: 960, height: 160 }
    const bottomPos = popoverPosition(wide, 'bottom', { width: 1400, height: 1100 })
    expect(bottomPos.left).toBe(wide.left - 6)
    expect(bottomPos.top).toBeGreaterThanOrEqual(wide.bottom + 6)
    const topWide = { top: 500, left: 240, right: 1200, bottom: 660, width: 960, height: 160 }
    const topPos = popoverPosition(topWide, 'top', { width: 1400, height: 1100 })
    expect(topPos.left).toBe(topWide.left - 6)
    expect(topPos.top + POPOVER_H).toBeLessThanOrEqual(topWide.top - 6)

    const narrow = { top: 100, left: 400, right: 480, bottom: 140, width: 80, height: 40 }
    const narrowPos = popoverPosition(narrow, 'bottom', { width: 1400, height: 900 })
    // Центр узкого якоря с учётом TOUR_SPOTLIGHT_PAD (6).
    expect(narrowPos.left).toBe(240)
  })

  it('clampPopoverInViewport keeps the plaque inside the viewport', () => {
    const fitted = clampPopoverInViewport(
      { top: 800, left: 10 },
      { width: 400, height: 300 },
      { width: 900, height: 900 },
    )
    expect(fitted.top + 300).toBeLessThanOrEqual(900 - VIEWPORT_PAD)
    expect(fitted.top).toBeGreaterThanOrEqual(VIEWPORT_PAD)
  })

  it('places popover beside a tall target, not on top of the form', () => {
    const tallForm = { top: 40, left: 240, right: 1200, bottom: 860, width: 960, height: 820 }
    const pos = popoverPosition(tallForm, 'bottom', { width: 1400, height: 900 })
    expect(pos.top).toBe(VIEWPORT_PAD)
    expect(pos.left).toBe(VIEWPORT_PAD)
    expect(pos.top + POPOVER_H).toBeLessThanOrEqual(900 - VIEWPORT_PAD)
  })

  it('keeps plaque below a wide short target without overlapping the hole', () => {
    const bar = { top: 120, left: 240, right: 1200, bottom: 200, width: 960, height: 80 }
    const pos = popoverPosition(bar, 'bottom', { width: 1400, height: 900 })
    expect(pos.top).toBeGreaterThanOrEqual(bar.bottom + 6)
  })

  it('fitPopoverAwayFromTarget moves a clamped plaque off a tall form', () => {
    const form = { top: 40, left: 240, right: 1200, bottom: 860, width: 960, height: 820 }
    const fitted = fitPopoverAwayFromTarget(
      { top: 16, left: 240 },
      { width: 400, height: 280 },
      { width: 1400, height: 900 },
      form,
    )
    expect(fitted.left).toBe(VIEWPORT_PAD)
  })

  it('keeps last-step button and plaque inside a short viewport', () => {
    const viewport = { width: 1440, height: 800 }
    const button = { top: 680, left: 320, right: 640, bottom: 728, width: 320, height: 48 }
    expect(rectFullyInViewport(button, viewport)).toBe(true)
    const clipped = { top: 760, left: 320, right: 640, bottom: 820, width: 320, height: 60 }
    expect(rectFullyInViewport(clipped, viewport)).toBe(false)
    const pos = popoverPosition(
      { ...button, right: button.right, bottom: button.bottom },
      'top',
      viewport,
    )
    expect(pos.top).toBeGreaterThanOrEqual(VIEWPORT_PAD)
    expect(pos.top + POPOVER_H).toBeLessThanOrEqual(viewport.height - VIEWPORT_PAD)
    expect(pos.top + POPOVER_H).toBeLessThanOrEqual(button.top)
  })
})
