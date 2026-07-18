import { useEffect, useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { sendChatRequest, type SourceItem } from './services/chatApi'
import SourceCard from './components/SourceCard'
import './App.css'

const Icon = ({ name }: { name: 'bell' | 'history' | 'paperclip' | 'arrow' | 'calendar' }) => {
  const paths = {
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></>,
    history: <><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/></>,
    paperclip: <path d="m21.4 11.6-8.9 8.9a6 6 0 0 1-8.5-8.5l9.6-9.6a4 4 0 0 1 5.7 5.7l-9.6 9.6a2 2 0 0 1-2.8-2.8l8.9-8.9"/>,
    calendar: <><rect x="4" y="5" width="16" height="15" rx="2"/><path d="M8 3v4M16 3v4M4 9h16"/></>,
    arrow: <><path d="M12 19V5M6 11l6-6 6 6"/></>,
  }
  return <svg viewBox="0 0 24 24" aria-hidden="true">{paths[name]}</svg>
}

const getLocalIsoDate = () => {
  const now = new Date()
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

const SESSION_KEY = 'compliance-ai-session'
const HISTORY_KEY = 'compliance-ai-history'
const WORKSPACE_KEY = 'compliance-ai-workspace'
const NOTIFICATIONS_KEY = 'compliance-ai-notifications'
type AccountRole = 'manager' | 'employee'

const readSessionRole = (): AccountRole | null => {
  try {
    const raw = window.localStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const session = JSON.parse(raw) as { role?: unknown }
    return session.role === 'manager' || session.role === 'employee' ? session.role : null
  } catch {
    return null
  }
}

const formatDateTime = (date: Date) => {
  const pad = (n: number) => String(n).padStart(2, '0')
  const day = pad(date.getDate())
  const month = pad(date.getMonth() + 1)
  const year = date.getFullYear()
  const hours = pad(date.getHours())
  const minutes = pad(date.getMinutes())
  return `${day}/${month}/${year} ${hours}:${minutes}`
}

const getRelativeTime = (date: Date) => {
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return 'Vừa xong'
  if (minutes < 60) return `${minutes} phút trước`
  if (hours < 24) return `${hours} giờ trước`
  if (days === 1) return 'Hôm qua'
  if (days < 7) return `${days} ngày trước`
  return formatDateTime(date)
}

const loadHistory = (): ConversationEntry[] => {
  try {
    const raw = window.localStorage.getItem(HISTORY_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter((entry): entry is ConversationEntry => {
      if (!entry || typeof entry !== 'object') return false
      const candidate = entry as Partial<ConversationEntry>
      return typeof candidate.id === 'number'
        && typeof candidate.question === 'string'
        && typeof candidate.answer === 'string'
        && typeof candidate.error === 'string'
        && Array.isArray(candidate.sources)
    })
  } catch {
    return []
  }
}

const saveHistory = (history: ConversationEntry[]) => {
  try {
    // Keep only last 50 conversations
    const trimmed = history.slice(-50)
    window.localStorage.setItem(HISTORY_KEY, JSON.stringify(trimmed))
  } catch {
    // Ignore storage errors
  }
}

const InlineText = ({ text }: { text: string }) => <>{text.split(/(\*\*.*?\*\*)/g).map((part, index) => part.startsWith('**') && part.endsWith('**') ? <strong key={index}>{part.slice(2, -2)}</strong> : part)}</>

const FormattedAnswer = ({ content }: { content: string }) => (
  <div className="formatted-answer">
    {content.split('\n').map((rawLine, index) => {
      const line = rawLine.trim()
      if (!line) return <div className="answer-spacer" key={index} />
      if (line.startsWith('### ')) return <h3 key={index}><InlineText text={line.slice(4)} /></h3>
      if (line.startsWith('## ')) return <h2 key={index}><InlineText text={line.slice(3)} /></h2>
      if (line.startsWith('- ')) return <div className="answer-bullet" key={index}><span>•</span><p><InlineText text={line.slice(2)} /></p></div>
      return <p key={index}><InlineText text={line} /></p>
    })}
  </div>
)

type ConversationEntry = {
  id: number
  question: string
  answer: string
  error: string
  sources: SourceItem[]
  conflictWarning: string | null
  requestId: string | null
  latencyMs: number | null
  createdAt?: string
  asOf?: string
  audience?: AccountRole
}

type SavedWorkspace = {
  question: string
  lastQuestion: string
  conversation: ConversationEntry[]
  answer: string
  sources: SourceItem[]
  conflictWarning: string | null
  requestId: string | null
  latencyMs: number | null
  error: string
  asOf: string
  audience: AccountRole
}

type AppNotification = {
  id: number
  title: string
  message: string
  kind: 'success' | 'warning' | 'error'
  createdAt: string
  read: boolean
}

const loadNotifications = (): AppNotification[] => {
  try {
    const raw = window.localStorage.getItem(NOTIFICATIONS_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter((item): item is AppNotification => {
      if (!item || typeof item !== 'object') return false
      const value = item as Partial<AppNotification>
      return typeof value.id === 'number' && typeof value.title === 'string'
        && typeof value.message === 'string' && typeof value.createdAt === 'string'
        && typeof value.read === 'boolean'
        && (value.kind === 'success' || value.kind === 'warning' || value.kind === 'error')
    })
  } catch {
    return []
  }
}

const saveNotifications = (notifications: AppNotification[]) => {
  try {
    window.localStorage.setItem(NOTIFICATIONS_KEY, JSON.stringify(notifications.slice(-50)))
  } catch {
    // Trình duyệt có thể chặn storage.
  }
}

const loadWorkspace = (): Partial<SavedWorkspace> => {
  try {
    const raw = window.localStorage.getItem(WORKSPACE_KEY)
    if (!raw) return {}
    const parsed: unknown = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed as Partial<SavedWorkspace> : {}
  } catch {
    return {}
  }
}

const initialWorkspace = loadWorkspace()

function App() {
  const initialRole = readSessionRole()
  const [isAuthenticated, setIsAuthenticated] = useState(() => window.location.pathname === '/chatbot')
  const [loginName, setLoginName] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [question, setQuestion] = useState(typeof initialWorkspace.question === 'string' ? initialWorkspace.question : '')
  const [lastQuestion, setLastQuestion] = useState(typeof initialWorkspace.lastQuestion === 'string' ? initialWorkspace.lastQuestion : '')
  const [conversation, setConversation] = useState<ConversationEntry[]>(Array.isArray(initialWorkspace.conversation) ? initialWorkspace.conversation : [])
  const [answer, setAnswer] = useState(typeof initialWorkspace.answer === 'string' ? initialWorkspace.answer : '')
  const [sources, setSources] = useState<SourceItem[]>(Array.isArray(initialWorkspace.sources) ? initialWorkspace.sources : [])
  const [conflictWarning, setConflictWarning] = useState<string | null>(typeof initialWorkspace.conflictWarning === 'string' ? initialWorkspace.conflictWarning : null)
  const [requestId, setRequestId] = useState<string | null>(typeof initialWorkspace.requestId === 'string' ? initialWorkspace.requestId : null)
  const [latencyMs, setLatencyMs] = useState<number | null>(typeof initialWorkspace.latencyMs === 'number' ? initialWorkspace.latencyMs : null)
  const [asOf, setAsOf] = useState(typeof initialWorkspace.asOf === 'string' ? initialWorkspace.asOf : getLocalIsoDate)
  const [audience, setAudience] = useState<AccountRole>(initialWorkspace.audience === 'manager' || initialWorkspace.audience === 'employee' ? initialWorkspace.audience : initialRole ?? 'employee')
  const [error, setError] = useState(typeof initialWorkspace.error === 'string' ? initialWorkspace.error : '')
  const [isLoading, setIsLoading] = useState(false)
  const [isProfileOpen, setIsProfileOpen] = useState(false)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [settingsSection, setSettingsSection] = useState<'appearance' | 'security'>('appearance')
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>('light')
  const [fontSize, setFontSize] = useState<'small' | 'medium' | 'large'>('medium')
  const [isPasswordFormOpen, setIsPasswordFormOpen] = useState(false)
  const [displayName, setDisplayName] = useState('FB: SnooAI')
  const [username, setUsername] = useState('eacuncsowe')
  const [isHistoryOpen, setIsHistoryOpen] = useState(false)
  const [chatHistory, setChatHistory] = useState<ConversationEntry[]>([])
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false)
  const [notifications, setNotifications] = useState<AppNotification[]>(loadNotifications)
  const fileInput = useRef<HTMLInputElement>(null)

  const navigate = (path: '/login' | '/chatbot') => {
    window.history.pushState({}, '', path)
    setIsAuthenticated(path === '/chatbot' && readSessionRole() !== null)
  }

  const completeLogin = () => {
    const normalizedName = loginName.trim().toLocaleLowerCase('vi-VN')
    const isManager = ['manager', 'admin', 'quanly', 'quản lý'].includes(normalizedName)
    const role: AccountRole = isManager ? 'manager' : 'employee'
    window.localStorage.setItem(SESSION_KEY, JSON.stringify({ role, signedInAt: new Date().toISOString() }))
    setAudience(role)
    navigate('/chatbot')
  }

  const socialLogin = () => {
    window.localStorage.setItem(SESSION_KEY, JSON.stringify({ role: 'employee', signedInAt: new Date().toISOString() }))
    setAudience('employee')
    navigate('/chatbot')
  }

  const logout = () => {
    window.localStorage.removeItem(SESSION_KEY)
    setIsSettingsOpen(false)
    setIsAuthenticated(false)
    window.history.pushState({}, '', '/login')
  }

  useEffect(() => {
    const syncRouteWithSession = () => {
      setIsAuthenticated(window.location.pathname === '/chatbot')
    }
    if (window.location.pathname !== '/login' && window.location.pathname !== '/chatbot') {
      window.history.replaceState({}, '', '/chatbot')
    }
    syncRouteWithSession()
    window.addEventListener('popstate', syncRouteWithSession)
    return () => window.removeEventListener('popstate', syncRouteWithSession)
  }, [])

  const addToHistory = (entry: ConversationEntry) => {
    setChatHistory((current) => {
      const next = [...current, entry].slice(-50)
      saveHistory(next)
      return next
    })
  }

  const openHistoryEntry = (entry: ConversationEntry) => {
    setConversation([])
    setLastQuestion(entry.question)
    setAnswer(entry.answer)
    setError(entry.error)
    setSources(entry.sources)
    setConflictWarning(entry.conflictWarning ?? null)
    setRequestId(entry.requestId ?? null)
    setLatencyMs(entry.latencyMs ?? null)
    if (entry.asOf) setAsOf(entry.asOf)
    if (entry.audience) setAudience(entry.audience)
    setIsHistoryOpen(false)
  }

  const deleteHistoryEntry = (id: number) => {
    setChatHistory((current) => {
      const next = current.filter((entry) => entry.id !== id)
      saveHistory(next)
      return next
    })
  }

  const clearHistory = () => {
    setChatHistory([])
    saveHistory([])
  }

  const addNotification = (notification: Omit<AppNotification, 'id' | 'createdAt' | 'read'>) => {
    setNotifications((current) => {
      const next = [...current, { ...notification, id: Date.now(), createdAt: new Date().toISOString(), read: false }].slice(-50)
      saveNotifications(next)
      return next
    })
  }

  const markAllNotificationsRead = () => {
    setNotifications((current) => {
      const next = current.map((item) => ({ ...item, read: true }))
      saveNotifications(next)
      return next
    })
  }

  const deleteNotification = (id: number) => {
    setNotifications((current) => {
      const next = current.filter((item) => item.id !== id)
      saveNotifications(next)
      return next
    })
  }

  const clearNotifications = () => {
    setNotifications([])
    saveNotifications([])
  }

  const startNewChat = () => {
    setQuestion('')
    setLastQuestion('')
    setConversation([])
    setAnswer('')
    setSources([])
    setConflictWarning(null)
    setRequestId(null)
    setLatencyMs(null)
    setError('')
    setAsOf(getLocalIsoDate())
  }

  useEffect(() => {
    const updateDate = () => setAsOf(getLocalIsoDate())
    const timer = window.setInterval(updateDate, 60_000)
    return () => window.clearInterval(timer)
  }, [])

  // Load history on mount
  useEffect(() => {
    const history = loadHistory()
    setChatHistory(history)
  }, [])

  useEffect(() => {
    const workspace: SavedWorkspace = {
      question, lastQuestion, conversation, answer, sources, conflictWarning,
      requestId, latencyMs, error, asOf, audience,
    }
    try {
      window.localStorage.setItem(WORKSPACE_KEY, JSON.stringify(workspace))
    } catch {
      // Trình duyệt có thể chặn storage; phiên hiện tại vẫn tiếp tục hoạt động.
    }
  }, [question, lastQuestion, conversation, answer, sources, conflictWarning, requestId, latencyMs, error, asOf, audience])

  const submit = async (event?: FormEvent) => {
    event?.preventDefault()
    const value = question.trim()
    if (!value || isLoading) return
    if (answer || error) {
      setConversation((current) => [...current, {
        id: Date.now(), question: lastQuestion, answer, error, sources,
        conflictWarning, requestId, latencyMs,
      }])
    }
    setLastQuestion(value)
    setError(''); setAnswer(''); setSources([]); setConflictWarning(null); setRequestId(null); setLatencyMs(null); setIsLoading(true)
    try {
      const result = await sendChatRequest(value, { asOf, audience, mode: 'system' })
      setAnswer(result.answer)
      setQuestion('')
      setSources(result.sources)
      setConflictWarning(result.conflictWarning ?? null)
      setRequestId(result.requestId ?? null)
      setLatencyMs(result.latencyMs ?? null)
      addToHistory({
        id: Date.now(), question: value, answer: result.answer, error: '', sources: result.sources,
        conflictWarning: result.conflictWarning ?? null, requestId: result.requestId ?? null,
        latencyMs: result.latencyMs ?? null, createdAt: new Date().toISOString(), asOf, audience,
      })
      if (result.conflictWarning?.trim()) {
        addNotification({ title: 'Phát hiện mâu thuẫn', message: `Câu hỏi “${value}” có quy định cần chú ý.`, kind: 'warning' })
      } else {
        addNotification({ title: 'Tra cứu hoàn tất', message: `Đã xử lý câu hỏi “${value}”.`, kind: 'success' })
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Đã xảy ra lỗi.'
      setError(message)
      addToHistory({
        id: Date.now(), question: value, answer: '', error: message, sources: [],
        conflictWarning: null, requestId: null, latencyMs: null,
        createdAt: new Date().toISOString(), asOf, audience,
      })
      addNotification({ title: 'Tra cứu thất bại', message, kind: 'error' })
    } finally { setIsLoading(false) }
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void submit()
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="login-page">
        <header className="login-header">
          <a className="login-brand" href="#"><span className="shield-mark">◆</span>Trợ lý tuân thủ</a>
          <a className="help-link" href="#help"><span>?</span> Hỗ trợ</a>
        </header>

        <main className="login-main">
          <section className="login-card" aria-labelledby="login-title">
            <h1 id="login-title">Chào mừng quay trở lại</h1>
            <p className="login-subtitle">Đăng nhập để truy cập hệ thống quản trị của<br />tổ chức.</p>
            <form onSubmit={(event) => { event.preventDefault(); completeLogin() }}>
              <label className="login-field">
                <span>Tên đăng nhập</span>
                <input required autoComplete="username" value={loginName} onChange={(event) => setLoginName(event.target.value)} placeholder="Nhập tên đăng nhập của bạn" />
              </label>
              <label className="login-field">
                <span>Mật khẩu</span>
                <input required type="password" autoComplete="current-password" value={loginPassword} onChange={(event) => setLoginPassword(event.target.value)} placeholder="Nhập mật khẩu của bạn" />
              </label>
              <div className="login-options">
                <label><input type="checkbox" /> <span>Ghi nhớ đăng nhập</span></label>
                <a href="#forgot-password">Quên mật khẩu?</a>
              </div>
              <button className="login-submit" type="submit">Đăng nhập</button>
            </form>

            <div className="login-divider"><span>hoặc đăng nhập bằng</span></div>
            <div className="social-login">
              <button type="button" onClick={socialLogin} aria-label="Đăng nhập bằng Google">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 12.2c0-.7-.1-1.3-.2-1.9H12v3.6h4.5a3.9 3.9 0 0 1-1.7 2.5v2.3h2.9c1.7-1.6 2.3-3.8 2.3-6.5Z"/><path d="M12 20c2.2 0 4.1-.7 5.5-2l-2.9-2.3c-.8.5-1.8.9-2.9.9-2.1 0-3.9-1.4-4.6-3.4h-3v2.4A8.3 8.3 0 0 0 12 20Z"/><path d="M7.1 13.2a5 5 0 0 1 0-3.1V7.7h-3a8.3 8.3 0 0 0 0 7.9l3-2.4Z"/><path d="M12 6.7c1.2 0 2.3.4 3.2 1.3l2.4-2.4A8 8 0 0 0 4.1 7.7l3 2.4A5 5 0 0 1 12 6.7Z"/></svg>
                Google
              </button>
              <button type="button" onClick={socialLogin} aria-label="Đăng nhập bằng Microsoft">
                <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="8" height="8"/><rect x="13" y="3" width="8" height="8"/><rect x="3" y="13" width="8" height="8"/><rect x="13" y="13" width="8" height="8"/></svg>
                Microsoft
              </button>
            </div>

            <div className="demo-accounts">
              <div className="demo-divider"><span>Tài khoản Demo</span></div>
              <div className="demo-buttons">
                <button type="button" className="demo-btn employee" onClick={() => { setLoginName('nhanvien'); setLoginPassword('demo'); window.localStorage.setItem(SESSION_KEY, JSON.stringify({ role: 'employee', signedInAt: new Date().toISOString() })); navigate('/chatbot'); }}>
                  <span className="demo-role">Nhân viên</span>
                  <span className="demo-desc">Xem quy định cơ bản</span>
                </button>
                <button type="button" className="demo-btn manager" onClick={() => { setLoginName('quanly'); setLoginPassword('demo'); window.localStorage.setItem(SESSION_KEY, JSON.stringify({ role: 'manager', signedInAt: new Date().toISOString() })); navigate('/chatbot'); }}>
                  <span className="demo-role">Quản lý</span>
                  <span className="demo-desc">Xem đầy đủ quyền hạn</span>
                </button>
              </div>
            </div>
          </section>
        </main>

        <footer className="login-footer">
          <strong>© 2024 Trợ lý tuân thủ. Truy cập an toàn cho tổ chức.</strong>
          <nav><a href="#privacy">Chính sách bảo mật</a><a href="#terms">Điều khoản dịch vụ</a><a href="#security">Công bố bảo mật</a></nav>
        </footer>
      </div>
    )
  }

  return (
    <div className={`app-shell theme-${theme} font-${fontSize}`}>
      <header className="topbar">
        <a className="brand" href="#">Sovereign Compliance AI</a>
        <div className="header-actions">
          <span className={`connection-status account-role-status ${audience}`} title={`Loại tài khoản: ${audience === 'manager' ? 'Quản lý' : 'Nhân viên'}`}><i />{audience === 'manager' ? 'Quản lý' : 'Nhân viên'}</span>
          <div className="notification-menu">
            <button className="icon-button notification-button" type="button" aria-label={`Thông báo, ${notifications.filter((item) => !item.read).length} chưa đọc`} aria-expanded={isNotificationsOpen} onClick={() => setIsNotificationsOpen((open) => !open)}>
              <Icon name="bell" />
              {notifications.some((item) => !item.read) && <span className="notification-count">{Math.min(notifications.filter((item) => !item.read).length, 99)}</span>}
            </button>
            {isNotificationsOpen && <section className="notification-panel" aria-label="Danh sách thông báo">
              <header><div><h2>Thông báo</h2><p>{notifications.filter((item) => !item.read).length} chưa đọc</p></div><button type="button" onClick={markAllNotificationsRead} disabled={!notifications.some((item) => !item.read)}>Đánh dấu đã đọc</button></header>
              {notifications.length === 0 ? <div className="notification-empty"><Icon name="bell" /><strong>Chưa có thông báo</strong><p>Các cập nhật về lượt tra cứu sẽ xuất hiện tại đây.</p></div> : <div className="notification-list">
                {[...notifications].reverse().map((item) => <article className={`notification-item ${item.kind} ${item.read ? 'read' : 'unread'}`} key={item.id}>
                  <i className="notification-dot" />
                  <div><strong>{item.title}</strong><p>{item.message}</p><small>{getRelativeTime(new Date(item.createdAt))}</small></div>
                  <button type="button" onClick={() => deleteNotification(item.id)} aria-label={`Xóa thông báo ${item.title}`}>×</button>
                </article>)}
              </div>}
              {notifications.length > 0 && <footer><button type="button" onClick={clearNotifications}>Xóa tất cả</button></footer>}
            </section>}
          </div>
          <div className="account-menu">
            <span className="account-name">{displayName}</span>
            <button className="avatar" aria-label="Mở menu tài khoản" aria-haspopup="menu"><span>AI</span></button>
            <div className="account-dropdown" role="menu">
              <button type="button" role="menuitem" onClick={() => setIsProfileOpen(true)}>
                <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>
                Hồ sơ cá nhân
              </button>
              <button type="button" role="menuitem" onClick={() => setIsSettingsOpen(true)}>
                <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06a1.7 1.7 0 0 0-2.91 1.21V21h-4v-.08a1.7 1.7 0 0 0-2.91-1.21l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 3.08 14H3v-4h.08a1.7 1.7 0 0 0 1.18-2.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 10 3.08V3h4v.08a1.7 1.7 0 0 0 2.91 1.21l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 20.92 10H21v4h-.08A1.7 1.7 0 0 0 19.4 15Z"/></svg>
                Cài đặt
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="home">
        <section className={`hero ${isLoading || answer || error ? 'has-result' : ''}`}>
          {!isLoading && !answer && !error && <h1>Chào bạn, tôi có thể giúp gì cho<br />{' '}nghiệp vụ của bạn hôm nay?</h1>}
          <div className="query-options">
            <div className="date-picker" aria-label={`Đang xem quy định tại ngày ${asOf}`}><Icon name="calendar" /><span>Đang xem quy định tại ngày</span><strong>{new Intl.DateTimeFormat('en-US').format(new Date(`${asOf}T00:00:00`))}</strong></div>
          </div>
          {conversation.length > 0 && <div className="conversation-history">{conversation.map((entry) => <article className="conversation-turn" key={entry.id}>
            <div className="user-message">{entry.question}</div>
            <div className="assistant-message">
              {entry.error ? <p className="response-error">{entry.error}</p> : <>
                {entry.conflictWarning?.trim() && <div className="conflict-warning"><strong>⚠ Cảnh báo mâu thuẫn</strong><p>{entry.conflictWarning}</p></div>}
                <FormattedAnswer content={entry.answer} />
                {entry.sources.length > 0 && <details className="source-list"><summary>Nguồn tham khảo <span>{entry.sources.length}</span></summary>{entry.sources.map((source, index) => <SourceCard source={source} key={`${source.clauseId}-${index}`} />)}</details>}
                {(entry.requestId || entry.latencyMs !== null) && <div className="response-footer">{entry.requestId && <span>Request ID: {entry.requestId}</span>}{entry.requestId && entry.latencyMs !== null && <i />}{entry.latencyMs !== null && <span>{entry.latencyMs.toLocaleString('vi-VN')} ms</span>}</div>}
              </>}
            </div>
          </article>)}</div>}
          {(isLoading || answer || error) && <div className="current-turn">
          {lastQuestion && <div className="current-question user-message">{lastQuestion}</div>}
          <>
            <section className={`response result-response ${error ? 'response-error' : ''}`} aria-live="polite">
              {isLoading ? <div className="result-loading"><span className="result-spinner" />Đang xử lý yêu cầu...</div> : error ? error : (
                <>
                  {conflictWarning?.trim() && <div className="conflict-warning"><strong>⚠ Cảnh báo mâu thuẫn</strong><p>{conflictWarning}</p></div>}
                  <FormattedAnswer content={answer} />
                  {sources.length > 0 && <details className="source-list"><summary>Nguồn tham khảo <span>{sources.length}</span></summary>{sources.map((source, index) => <SourceCard source={source} key={`${source.clauseId}-${index}`} />)}</details>}
                  {(requestId || latencyMs !== null) && <div className="response-footer">{requestId && <span>Request ID: {requestId}</span>}{requestId && latencyMs !== null && <i />}{latencyMs !== null && <span>{latencyMs.toLocaleString('vi-VN')} ms</span>}</div>}
                </>
              )}
            </section>
          </>
          </div>}
          <form className="prompt-box" onSubmit={submit}>
            <textarea aria-label="Câu hỏi nghiệp vụ" value={question} onChange={(e) => setQuestion(e.target.value)} onKeyDown={onKeyDown} placeholder="Nhập câu hỏi hoặc mô tả tình huống nghiệp vụ..." />
            <div className="prompt-tools">
              <div className="left-tools">
                <button type="button" aria-label="Lịch sử giao dịch" title="Lịch sử giao dịch" onClick={() => setIsHistoryOpen(true)}><Icon name="history" /></button>
                <button type="button" aria-label="Đính kèm tệp" onClick={() => fileInput.current?.click()}><Icon name="paperclip" /></button>
              </div>
              <div className="prompt-actions">
                <button className="new-chat-button" type="button" onClick={startNewChat} disabled={isLoading || (!lastQuestion && conversation.length === 0)} aria-label="Tạo cuộc trò chuyện mới"><span>＋</span> New chat</button>
                <button className="send-button" type="submit" disabled={!question.trim() || isLoading} aria-label="Gửi câu hỏi"><Icon name="arrow" /></button>
              </div>
            </div>
          </form>
          <input ref={fileInput} type="file" hidden />
        </section>
      </main>

      <footer>
        <nav><a href="#privacy">Chính sách bảo mật</a><a href="#terms">Điều khoản dịch vụ</a></nav>
      </footer>

      {isHistoryOpen && (
        <div className="modal-backdrop history-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setIsHistoryOpen(false)
        }}>
          <section className="history-modal" role="dialog" aria-modal="true" aria-labelledby="history-title">
            <header className="history-header">
              <div><h2 id="history-title">Lịch sử giao dịch</h2><p>{chatHistory.length} lượt tra cứu gần nhất</p></div>
              <button type="button" onClick={() => setIsHistoryOpen(false)} aria-label="Đóng lịch sử">×</button>
            </header>
            {chatHistory.length === 0 ? (
              <div className="history-empty"><Icon name="history" /><strong>Chưa có giao dịch nào</strong><p>Các lượt tra cứu sẽ xuất hiện tại đây sau khi bạn gửi câu hỏi.</p></div>
            ) : (
              <div className="history-list">
                {[...chatHistory].reverse().map((entry) => {
                  const createdAt = entry.createdAt ? new Date(entry.createdAt) : new Date(entry.id)
                  const validDate = !Number.isNaN(createdAt.getTime())
                  return <article className="history-item" key={entry.id}>
                    <button className="history-entry" type="button" onClick={() => openHistoryEntry(entry)}>
                      <span className={`history-status ${entry.error ? 'failed' : 'success'}`}>{entry.error ? 'Thất bại' : 'Hoàn tất'}</span>
                      <strong>{entry.question}</strong>
                      <small>{validDate ? getRelativeTime(createdAt) : 'Không rõ thời gian'}{entry.asOf ? ` · Hiệu lực ${new Intl.DateTimeFormat('vi-VN').format(new Date(`${entry.asOf}T00:00:00`))}` : ''}</small>
                    </button>
                    <button className="history-delete" type="button" onClick={() => deleteHistoryEntry(entry.id)} aria-label={`Xóa giao dịch ${entry.question}`}>×</button>
                  </article>
                })}
              </div>
            )}
            {chatHistory.length > 0 && <footer className="history-footer"><button type="button" onClick={clearHistory}>Xóa toàn bộ lịch sử</button></footer>}
          </section>
        </div>
      )}

      {isProfileOpen && (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setIsProfileOpen(false)
        }}>
          <section className="profile-modal" role="dialog" aria-modal="true" aria-labelledby="profile-title">
            <h2 id="profile-title">Edit profile</h2>
            <form onSubmit={(event) => { event.preventDefault(); setIsProfileOpen(false) }}>
              <div className="profile-avatar-wrap">
                <div className="profile-avatar">FS</div>
                <button className="camera-button" type="button" aria-label="Thay đổi ảnh đại diện">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-1-2h-4L9 5H5a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-4Z"/><circle cx="12" cy="12" r="3"/></svg>
                </button>
              </div>

              <label className="profile-field">
                <span>Display name</span>
                <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
              </label>
              <label className="profile-field">
                <span>Username</span>
                <input value={username} onChange={(event) => setUsername(event.target.value)} />
              </label>
              <p className="profile-help">Your profile helps people recognize you in group chats.</p>

              <div className="profile-actions">
                <button className="cancel-button" type="button" onClick={() => setIsProfileOpen(false)}>Cancel</button>
                <button className="save-button" type="submit">Save</button>
              </div>
            </form>
          </section>
        </div>
      )}

      {isSettingsOpen && (
        <div className="settings-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setIsSettingsOpen(false) }}>
          <section className="settings-modal" role="dialog" aria-modal="true" aria-labelledby="settings-title">
            <aside className="settings-sidebar">
              <button className="settings-close" type="button" onClick={() => setIsSettingsOpen(false)} aria-label="Đóng cài đặt">×</button>
              <h2 id="settings-title">Cài đặt</h2>
              <button className={settingsSection === 'appearance' ? 'active' : ''} type="button" onClick={() => setSettingsSection('appearance')}><span>◐</span> Giao diện</button>
              <button className={settingsSection === 'security' ? 'active' : ''} type="button" onClick={() => setSettingsSection('security')}><span>◇</span> Bảo mật</button>
              <button className="logout-nav" type="button" onClick={logout}><span>↪</span> Đăng xuất</button>
            </aside>

            <div className="settings-content">
              {settingsSection === 'appearance' ? (
                <>
                  <h3>Giao diện</h3>
                  <div className="setting-block">
                    <h4>Chế độ hiển thị</h4>
                    <p>Chọn giao diện phù hợp với môi trường làm việc của bạn.</p>
                    <div className="choice-cards theme-choices">
                      {(['light', 'dark', 'system'] as const).map((value) => (
                        <button className={theme === value ? 'selected' : ''} type="button" key={value} onClick={() => setTheme(value)}>
                          <span className={`theme-preview ${value}`}><i /><i /></span>
                          <strong>{value === 'light' ? 'Sáng' : value === 'dark' ? 'Tối' : 'Theo hệ thống'}</strong>
                          <small>{theme === value ? '✓ Đang chọn' : 'Chọn'}</small>
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="setting-block font-setting">
                    <h4>Cỡ chữ</h4>
                    <div className="font-options">
                      {([['small', 'Nhỏ'], ['medium', 'Vừa — mặc định'], ['large', 'Lớn']] as const).map(([value, label]) => <button className={fontSize === value ? 'selected' : ''} type="button" key={value} onClick={() => setFontSize(value)}>{label}</button>)}
                    </div>
                    <div className={`font-preview preview-${fontSize}`}><strong>Văn bản xem trước</strong><p>Đây là nội dung mẫu giúp bạn xem trước kích thước chữ hiển thị.</p></div>
                  </div>
                </>
              ) : (
                <>
                  <h3>Bảo mật</h3>
                  <div className="setting-block security-block">
                    <div><h4>Đổi mật khẩu</h4><p>Cập nhật mật khẩu định kỳ để bảo vệ tài khoản của bạn.</p></div>
                    {!isPasswordFormOpen && <button className="change-password" type="button" onClick={() => setIsPasswordFormOpen(true)}>Đổi mật khẩu</button>}
                    {isPasswordFormOpen && <form className="password-form" onSubmit={(event) => { event.preventDefault(); setIsPasswordFormOpen(false) }}>
                      <label><span>Mật khẩu hiện tại</span><input type="password" required /></label>
                      <label><span>Mật khẩu mới</span><input type="password" required /></label>
                      <label><span>Xác nhận mật khẩu mới</span><input type="password" required /></label>
                      <div><button type="button" onClick={() => setIsPasswordFormOpen(false)}>Hủy</button><button className="update-password" type="submit">Cập nhật mật khẩu</button></div>
                    </form>}
                  </div>
                </>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

export default App
