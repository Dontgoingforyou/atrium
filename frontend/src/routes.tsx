import type { ComponentType } from 'react'
import { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate } from 'react-router'
import { RouterProvider } from 'react-router/dom'

import { RequireAuth } from './components/auth/RequireAuth'
import { RequireManagerOrAdmin } from './components/auth/RequireManagerOrAdmin'
import { RedirectDevelopers } from './components/auth/RedirectDevelopers'
import { RouteErrorFallback } from './components/RouteErrorFallback'
import { AppLayout } from './components/layout/AppLayout'

function lazyPage(loader: () => Promise<unknown>, exportName: string) {
  return lazy(async () => {
    const mod = (await loader()) as Record<string, ComponentType<unknown>>
    return { default: mod[exportName] }
  })
}

const LoginPage = lazyPage(() => import('./pages/LoginPage'), 'LoginPage')
const AuthCallbackPage = lazyPage(() => import('./pages/AuthCallbackPage'), 'AuthCallbackPage')
const HomePage = lazyPage(() => import('./pages/home'), 'HomePage')
const TasksPage = lazyPage(() => import('./pages/tasks'), 'TasksPage')
const TaskDetailPage = lazyPage(() => import('./pages/tasks/TaskDetailPage'), 'TaskDetailPage')
const TaskByNumberRedirect = lazyPage(() => import('./pages/tasks/TaskByNumberRedirect'), 'TaskByNumberRedirect')
const TaskNewPage = lazyPage(() => import('./pages/tasks'), 'TaskNewPage')
const AnalyticsLayout = lazyPage(() => import('./pages/analytics'), 'AnalyticsLayout')
const AnalyticsReportsPage = lazyPage(() => import('./pages/analytics'), 'AnalyticsReportsPage')
const AnalyticsBenchPage = lazyPage(() => import('./pages/analytics'), 'AnalyticsBenchPage')
const TimesheetsPage = lazyPage(() => import('./pages/timesheets'), 'TimesheetsPage')
const SpecialistsPage = lazyPage(() => import('./pages/specialists/SpecialistsPage'), 'SpecialistsPage')
const SearchPage = lazyPage(() => import('./pages/SearchPage'), 'SearchPage')
const AdminPanelBridgePage = lazyPage(() => import('./pages/AdminPanelBridgePage'), 'AdminPanelBridgePage')
const AccountSettingsPage = lazyPage(() => import('./pages/AccountSettingsPage'), 'AccountSettingsPage')
const PortalDocumentPage = lazyPage(() => import('./pages/documents'), 'PortalDocumentPage')
const TrashPage = lazyPage(() => import('./pages/TrashPage'), 'TrashPage')
const TagsPage = lazyPage(() => import('./pages/tags/TagsPage'), 'TagsPage')
const ChatsPage = lazyPage(() => import('./pages/chats'), 'ChatsPage')
const CalendarPage = lazyPage(() => import('./pages/calendar'), 'CalendarPage')
const CalendarInvitePage = lazyPage(() => import('./pages/calendar'), 'CalendarInvitePage')

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/auth/callback', element: <AuthCallbackPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppLayout />,
        errorElement: <RouteErrorFallback />,
        children: [
          // Маршруты, доступные всем авторизованным пользователям
          { path: '/timesheets', element: <Navigate to="/analytics/timesheets" replace /> },
          {
            path: '/analytics',
            element: <AnalyticsLayout />,
            children: [
              { index: true, element: <Navigate to="/analytics/timesheets" replace /> },
              { path: 'timesheets', element: <TimesheetsPage /> },
              { path: 'reports', element: <AnalyticsReportsPage /> },
              {
                path: 'bench',
                element: (
                  <RequireManagerOrAdmin>
                    <AnalyticsBenchPage />
                  </RequireManagerOrAdmin>
                ),
              },
            ],
          },
          // Маршруты, недоступные для студентов (students) — редирект на таймшиты
          {
            element: <RedirectDevelopers />,
            children: [
              { path: '/account', element: <AccountSettingsPage /> },
              { path: '/', element: <HomePage /> },
              { path: '/tasks', element: <TasksPage /> },
              { path: '/tasks/new', element: <TaskNewPage /> },
              { path: '/tasks/task-:taskNumber', element: <TaskByNumberRedirect /> },
              { path: '/tasks/:taskId', element: <TaskDetailPage /> },
              { path: '/specialists', element: <SpecialistsPage /> },
              { path: '/agreements', element: <Navigate to="/" replace /> },
              { path: '/finance', element: <Navigate to="/" replace /> },
              { path: '/learning', element: <Navigate to="/" replace /> },
              { path: '/search', element: <SearchPage /> },
              { path: '/admin-bridge', element: <AdminPanelBridgePage /> },
              { path: '/tags', element: <TagsPage /> },
              { path: '/chats', element: <ChatsPage /> },
              { path: '/calendar', element: <CalendarPage /> },
              { path: '/calendar/invite/:token', element: <CalendarInvitePage /> },
              {
                path: '/p/trash',
                element: (
                  <RequireManagerOrAdmin>
                    <TrashPage />
                  </RequireManagerOrAdmin>
                ),
              },
              { path: '/p/:slug', element: <Navigate to="/" replace /> },
            ],
          },
          { path: '/p/:slug/documents/:documentId', element: <PortalDocumentPage /> },
          { path: '/documents/:documentId', element: <PortalDocumentPage /> },
        ],
      },
    ],
  },
])

export function AppRoutes() {
  return (
    <Suspense fallback={<p className="text-muted">Загрузка…</p>}>
      <RouterProvider router={router} />
    </Suspense>
  )
}
