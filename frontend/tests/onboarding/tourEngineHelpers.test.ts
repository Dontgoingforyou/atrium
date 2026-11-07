// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'

import {
  locationMatchesHref,
  resolveTourOpenHref,
  routeMatches,
} from '../../src/onboarding/tourEngineHelpers'

describe('routeMatches', () => {
  it('returns true when step has no route', () => {
    expect(routeMatches('/tasks', '', undefined)).toBe(true)
    expect(routeMatches('/tasks', '?x=1', undefined)).toBe(true)
  })

  it('matches path without query', () => {
    expect(routeMatches('/tasks', '?any=1', '/tasks')).toBe(true)
    expect(routeMatches('/documents', '', '/tasks')).toBe(false)
  })

  it('matches path and required query params', () => {
    expect(routeMatches('/calendar', '?event=ev-1', '/calendar?event=ev-1')).toBe(true)
    expect(routeMatches('/calendar', '?event=ev-1&edit=1', '/calendar?event=ev-1')).toBe(true)
    expect(routeMatches('/calendar', '?event=other', '/calendar?event=ev-1')).toBe(false)
    expect(routeMatches('/calendar', '', '/calendar?event=ev-1')).toBe(false)
  })

  it('ignores extra current query params not required by step', () => {
    expect(routeMatches('/tasks', '?tab=board&page=2', '/tasks?tab=board')).toBe(true)
  })

  it('treats /analytics index as /analytics/timesheets (index redirect)', () => {
    expect(routeMatches('/analytics/timesheets', '', '/analytics')).toBe(true)
    expect(routeMatches('/analytics', '', '/analytics/timesheets')).toBe(true)
    expect(routeMatches('/analytics/reports', '', '/analytics')).toBe(false)
    expect(routeMatches('/analytics/timesheets', '?tab=report', '/analytics')).toBe(true)
  })
})

describe('locationMatchesHref', () => {
  it('matches pathname only when href has no query', () => {
    expect(locationMatchesHref('/tasks', '?anything', '/tasks')).toBe(true)
    expect(locationMatchesHref('/documents', '', '/tasks')).toBe(false)
  })

  it('matches pathname and required query', () => {
    expect(locationMatchesHref('/calendar', '?event=ev-1', '/calendar?event=ev-1')).toBe(true)
    expect(locationMatchesHref('/calendar', '?event=ev-1&edit=1', '/calendar?event=ev-1')).toBe(
      true,
    )
    expect(locationMatchesHref('/calendar', '?event=other', '/calendar?event=ev-1')).toBe(false)
  })

  it('handles search with or without leading ?', () => {
    expect(locationMatchesHref('/tasks', 'tab=board', '/tasks?tab=board')).toBe(true)
    expect(locationMatchesHref('/tasks', '?tab=board', '/tasks?tab=board')).toBe(true)
  })

  it('treats /analytics index as /analytics/timesheets', () => {
    expect(locationMatchesHref('/analytics/timesheets', '', '/analytics')).toBe(true)
    expect(locationMatchesHref('/analytics', '', '/analytics/timesheets')).toBe(true)
    expect(locationMatchesHref('/analytics/reports', '', '/analytics')).toBe(false)
  })
})

describe('resolveTourOpenHref', () => {
  it('returns href of anchor with absolute path', () => {
    const a = document.createElement('a')
    a.setAttribute('href', '/documents/abc')
    expect(resolveTourOpenHref(a)).toBe('/documents/abc')
  })

  it('returns null for external/javascript anchors', () => {
    const a = document.createElement('a')
    a.setAttribute('href', 'https://example.com/x')
    expect(resolveTourOpenHref(a)).toBeNull()
    a.setAttribute('href', 'javascript:void(0)')
    expect(resolveTourOpenHref(a)).toBeNull()
  })

  it('rejects protocol-relative and backslash paths', () => {
    const a = document.createElement('a')
    a.setAttribute('href', '//evil.example/phish')
    expect(resolveTourOpenHref(a)).toBeNull()
    a.setAttribute('href', '/\\evil')
    expect(resolveTourOpenHref(a)).toBeNull()
    const div = document.createElement('div')
    div.setAttribute('data-tour-route', '//evil.example')
    expect(resolveTourOpenHref(div)).toBeNull()
  })

  it('falls back to data-tour-route on non-anchor element', () => {
    const div = document.createElement('div')
    div.setAttribute('data-tour-route', '/tasks')
    expect(resolveTourOpenHref(div)).toBe('/tasks')
  })

  it('returns null when neither anchor href nor data-tour-route is a path', () => {
    const div = document.createElement('div')
    expect(resolveTourOpenHref(div)).toBeNull()
    div.setAttribute('data-tour-route', 'https://nope')
    expect(resolveTourOpenHref(div)).toBeNull()
  })
})
