import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, Outlet, useLocation, useNavigate } from 'react-router'

import { PORTAL_CHATS_ALL_QUERY_KEY, patchPortalUserInCache } from '../../api/queryKeys'
import { useClassicScrollbarInset } from '../../hooks/useClassicScrollbarInset'
import { useNavigationTreeQuery } from '../../hooks/usePortalNavigation'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { installNotificationAudioBrowserUnlock } from '../../utils/notifications/notificationSound'
import { installUiSoundPointerListeners } from '../../utils/sound/uiSounds'
import { useAuthStore } from '../../store/authStore'
import { isTimesheetOnlyUser, isUserManagerOrAdmin } from '@/domain/auth/authRoles'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { MentionNotificationsBell } from './MentionNotificationsBell'
import { PortalRealtimeFeatures } from './PortalRealtimeFeatures'
import { ThemeToggle } from './ThemeToggle'
import { ChangelogButton } from './ChangelogButton'
import { PortalDocumentsNavSections } from './PortalDocumentsNavSections'
import { GlobalSearchField } from '../search/GlobalSearchField'
import { GuidedTourHost } from '../../onboarding/GuidedTourHost'
import { GuidedTourRestartNavButton } from '../../onboarding/GuidedTourRestartNavButton'
import { UserAvatar } from '../ui/UserAvatar'
import { listChats } from '../../api/chat/chatApi'
import { uploadMyAvatar } from '../../api/usersApi'
import type { Chat } from '../../types/chat'
import { DelayedActionProvider } from '../../contexts/DelayedActionContext'
import { SpaNavigateRegistrar } from './SpaNavigateRegistrar'
import { getHomeDashboardRestore } from '../../pages/tasks/taskBackNav'
import styles from '@/styles/modules/layout/AppLayout.module.css'
import narrowStyles from '@/styles/modules/layout/AppLayoutNarrow.module.css'
import { useAppNavDrawer } from './useAppNavDrawer'

export function AppLayout() {
  return (
    <DelayedActionProvider>
      <AppLayoutInner />
    </DelayedActionProvider>
  )
}

function AppLayoutInner() {
  const location = useLocation()
  const navigate = useNavigate()
  const isChatsRoute = location.pathname.startsWith('/chats')
  const isDocumentPageRoute = /\/documents\/[^/]+/.test(location.pathname)
  const isSearchPage = location.pathname === '/search'
  const user = useAuthStore((s) => s.user)
  const patchUser = useAuthStore((s) => s.patchUser)
  const logout = useAuthStore((s) => s.logout)
  const qc = useQueryClient()
  const notify = useNotifyToast()
  const avatarFileRef = useRef<HTMLInputElement>(null)
  const mainRef = useRef<HTMLElement>(null)
  useClassicScrollbarInset(mainRef, !isChatsRoute, location.key)

  // isDeveloper вычисляется до хуков — используется как флаг enabled.
  // При наличии нескольких ролей (students + outstaff / admin) приоритет у старшей роли.
  const timesheetOnly = user
    ? isTimesheetOnlyUser(user)
    : false
  const showSpecialistsNav = user
    ? isUserManagerOrAdmin(user)
    : false

  const {
    data: navTree,
    isLoading: navLoading,
    isError: navError,
    refetch: refetchNav,
  } = useNavigationTreeQuery()
  const [bellOpen, setBellOpen] = useState(false)
  const menuBtnRef = useRef<HTMLButtonElement>(null)
  const asideRef = useRef<HTMLElement>(null)
  const nav = useAppNavDrawer(location.pathname, menuBtnRef, asideRef)

  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem('cosmolet:sidebar_collapsed') === '1'
    } catch {
      return false
    }
  })

  const navHidden = nav.narrow ? !nav.drawerOpen : sidebarCollapsed

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => {
      const next = !prev
      try {
        localStorage.setItem('cosmolet:sidebar_collapsed', next ? '1' : '0')
      } catch {
        /* ignore */
      }
      return next
    })
  }, [])

  const avatarMut = useMutation({
    mutationFn: (file: File) => uploadMyAvatar(file),
    onSuccess: (data) => {
      patchUser({
        avatar_url: data.avatar_url,
        avatar_focal_x: null,
        avatar_focal_y: null,
      })
      if (user?.sub) {
        patchPortalUserInCache(qc, user.sub, {
          avatar_url: data.avatar_url,
          avatar_focal_x: null,
          avatar_focal_y: null,
        })
      }
    },
    onError: (e) => notify(userFacingMessageFromUnknown(e)),
  })

  useEffect(() => {
    installNotificationAudioBrowserUnlock()
    installUiSoundPointerListeners()
  }, [])

  useEffect(() => {
    const restore = getHomeDashboardRestore(location.state)
    const top = restore?.homeScrollTop
    if (location.pathname === '/' && typeof top === 'number') {
      requestAnimationFrame(() => {
        mainRef.current?.scrollTo({ top })
      })
      return
    }
    if (document.documentElement.getAttribute('data-guided-tour') === '1') {
      return
    }
    mainRef.current?.scrollTo({ top: 0 })
  }, [location.key, location.pathname, location.state])

  // Данные уже в кеше от FloatingDmWidget — лишнего сетевого запроса не будет
  const { data: allChats = [], isError: chatsError, error: chatsErr } = useQuery<Chat[]>({
    queryKey: PORTAL_CHATS_ALL_QUERY_KEY,
    queryFn: () => listChats({ limit: 500 }),
    enabled: Boolean(user) && !timesheetOnly,
    staleTime: 60_000,
  })

  useEffect(() => {
    if (chatsError) notify(userFacingMessageFromUnknown(chatsErr))
  }, [chatsError, chatsErr, notify])

  const totalUnread = useMemo(
    () => allChats.reduce((sum, c) => sum + (c.unread_count ?? 0), 0),
    [allChats],
  )

  async function onLogout() {
    await logout()
    window.location.href = '/login'
  }

  function navClass(path: string, exact = false) {
    const active = exact ? location.pathname === path : location.pathname.startsWith(path)
    return active ? `${styles.navLink} ${styles.navLinkActive}` : styles.navLink
  }

  function renderNavSections(canEdit: boolean, useDraggable: boolean) {
    return (
      <PortalDocumentsNavSections
        navTree={navTree ?? []}
        navLoading={navLoading}
        navError={navError}
        onRetry={() => void refetchNav()}
        canEdit={canEdit}
        useDraggable={useDraggable}
      />
    )
  }

  return (
    <>
      <SpaNavigateRegistrar />
      <div className={styles.layout}>
      {nav.drawerModal ? (
        <div
          className={narrowStyles.backdrop}
          role="presentation"
          onClick={nav.close}
        />
      ) : null}
      <div className={`${styles.sidebarWrapper} ${narrowStyles.sidebarHost}`}>
        <aside
          ref={asideRef}
          id={nav.navId}
          className={[
            styles.sidebar,
            sidebarCollapsed ? styles.sidebarCollapsed : '',
            narrowStyles.sidebar,
            nav.drawerOpen ? narrowStyles.sidebarOpen : '',
          ]
            .filter(Boolean)
            .join(' ')}
          aria-hidden={navHidden}
          inert={navHidden ? true : undefined}
          role={nav.drawerModal ? 'dialog' : undefined}
          aria-modal={nav.drawerModal ? true : undefined}
          aria-label={nav.drawerModal ? 'Меню' : undefined}
          onClick={nav.onSidebarClick}
        >
          <div className={styles.sidebarHeader}>
            <Link to="/" className={styles.logo} aria-label="Cosmolet">
              <img
                src="/brand-waves.svg"
                alt=""
                className={styles.logoIcon}
                width={28}
                height={28}
              />
              <span className={styles.logoText}>Cosmolet</span>
            </Link>
          </div>
          <nav className={styles.nav}>
          {timesheetOnly ? (
            // Timesheet-only (АУ / студенты): таймшиты + developer-docs
            <>
              <Link
                to="/analytics/timesheets"
                className={navClass('/analytics/timesheets')}
                data-tour="nav-timesheets"
              >
                Таймшиты
              </Link>
              <GuidedTourRestartNavButton />
              {renderNavSections(false, false)}
            </>
          ) : (
            // Менеджер и администратор видят полное меню
            <>
              <Link to="/" className={navClass('/', true)}>
                Главная
              </Link>
              <Link to="/tasks" className={navClass('/tasks')}>
                Задачи
              </Link>
              {showSpecialistsNav ? (
                <Link to="/specialists" className={navClass('/specialists')} data-tour="nav-specialists">
                  Специалисты
                </Link>
              ) : null}
              <Link to="/chats" className={navClass('/chats')} data-tour="nav-chats">
                Чаты
                {totalUnread > 0 && (
                  <span className={styles.navBadge}>{totalUnread > 99 ? '99+' : totalUnread}</span>
                )}
              </Link>
              <Link to="/calendar" className={navClass('/calendar')} data-tour="nav-calendar">
                Календарь
              </Link>
              <Link to="/tags" className={navClass('/tags')} data-tour="nav-tags">
                Теги
              </Link>
              <Link
                to="/analytics/timesheets"
                className={navClass('/analytics')}
                data-tour="nav-analytics"
              >
                Аналитика
              </Link>
              <Link to="/account" className={navClass('/account')}>
                Аккаунт
              </Link>
              {showSpecialistsNav ? (
                <Link to="/p/trash" className={navClass('/p/trash')} data-tour="nav-trash">
                  Корзина документов
                </Link>
              ) : null}
              {user?.is_portal_admin ? (
                <button
                  type="button"
                  onClick={() => navigate('/admin-bridge')}
                  className={styles.navBtn}
                  data-tour="nav-admin"
                >
                  Панель администратора
                </button>
              ) : null}
              {renderNavSections(showSpecialistsNav, showSpecialistsNav)}
            </>
          )}
          </nav>
        </aside>
        <button
          type="button"
          className={
            [
              styles.sidebarToggleBtn,
              sidebarCollapsed ? styles.sidebarCollapsedToggle : '',
              narrowStyles.edgeToggle,
            ]
              .filter(Boolean)
              .join(' ')
          }
          onClick={toggleSidebar}
          title={sidebarCollapsed ? 'Развернуть меню' : 'Свернуть меню'}
          aria-label={sidebarCollapsed ? 'Развернуть боковое меню' : 'Свернуть боковое меню'}
        >
          {sidebarCollapsed ? '›' : '‹'}
        </button>
      </div>
      <div className={styles.content}>
        <header className={`${styles.header} ${narrowStyles.header}`}>
          <button
            ref={menuBtnRef}
            type="button"
            className={narrowStyles.menuBtn}
            aria-expanded={nav.drawerOpen}
            aria-controls={nav.navId}
            onClick={nav.toggle}
          >
            Меню
          </button>
          {!timesheetOnly && !isSearchPage && <GlobalSearchField />}
          <div className={`${styles.userArea} ${narrowStyles.userArea}`}>
            {!timesheetOnly && <ChangelogButton />}
            <ThemeToggle />
            {!timesheetOnly && (
              <MentionNotificationsBell
                open={bellOpen}
                onToggle={() => setBellOpen((v) => !v)}
              />
            )}
            <input
              ref={avatarFileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              className={styles.avatarFileInput}
              aria-hidden
              tabIndex={-1}
              onChange={(e) => {
                const f = e.target.files?.[0]
                e.target.value = ''
                if (f) avatarMut.mutate(f)
              }}
            />
            <UserAvatar
              size="md"
              label={user?.full_name || user?.email || user?.username || '—'}
              imageUrl={user?.avatar_url}
              loading="eager"
              onClick={() => avatarFileRef.current?.click()}
              title="Нажмите, чтобы сменить аватар"
            />
            <span className={`${styles.userDisplay} ${narrowStyles.userDisplay}`} title={user?.full_name || user?.email || undefined}>
              {user?.full_name || user?.email || '—'}
            </span>
            <button type="button" className={styles.logoutBtn} onClick={onLogout}>
              Выход
            </button>
          </div>
        </header>
        <main
          ref={mainRef}
          data-portal-main
          className={
            [
              styles.main,
              isChatsRoute ? '' : narrowStyles.main,
              isChatsRoute ? styles.mainChatsFull : '',
              isDocumentPageRoute ? styles.mainDocumentsFlush : '',
            ]
              .filter(Boolean)
              .join(' ')
          }
        >
          <div
            className={isChatsRoute ? `${styles.pageTransitionFill}` : undefined}
          >
            <Outlet />
          </div>
        </main>
      </div>
      {!timesheetOnly && <PortalRealtimeFeatures />}
      <GuidedTourHost />
    </div>
    </>
  )
}
