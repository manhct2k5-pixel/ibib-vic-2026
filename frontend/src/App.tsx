import { useEffect, useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { sendChatRequest } from './services/chatApi'
import './App.css'

const Icon = ({ name }: { name: 'bell' | 'history' | 'paperclip' | 'pin' | 'arrow' | 'calendar' }) => {
  const paths = {
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></>,
    history: <><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/></>,
    paperclip: <path d="m21.4 11.6-8.9 8.9a6 6 0 0 1-8.5-8.5l9.6-9.6a4 4 0 0 1 5.7 5.7l-9.6 9.6a2 2 0 0 1-2.8-2.8l8.9-8.9"/>,
    pin: <><path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></>,
    calendar: <><rect x="4" y="5" width="16" height="15" rx="2"/><path d="M8 3v4M16 3v4M4 9h16"/></>,
    arrow: <><path d="M12 19V5M6 11l6-6 6 6"/></>,
  }
  return <svg viewBox="0 0 24 24" aria-hidden="true">{paths[name]}</svg>
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => window.location.pathname === '/chatbot')
  const [loginName, setLoginName] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isProfileOpen, setIsProfileOpen] = useState(false)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [settingsSection, setSettingsSection] = useState<'appearance' | 'security'>('appearance')
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>('system')
  const [fontSize, setFontSize] = useState<'small' | 'medium' | 'large'>('medium')
  const [isPasswordFormOpen, setIsPasswordFormOpen] = useState(false)
  const [displayName, setDisplayName] = useState('FB: SnooAI')
  const [username, setUsername] = useState('eacuncsowe')
  const fileInput = useRef<HTMLInputElement>(null)

  const navigate = (path: '/login' | '/chatbot') => {
    window.history.pushState({}, '', path)
    setIsAuthenticated(path === '/chatbot')
  }

  useEffect(() => {
    if (window.location.pathname !== '/login' && window.location.pathname !== '/chatbot') {
      window.history.replaceState({}, '', '/login')
    }
    const handlePopState = () => setIsAuthenticated(window.location.pathname === '/chatbot')
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  const submit = async (event?: FormEvent) => {
    event?.preventDefault()
    const value = question.trim()
    if (!value || isLoading) return
    setError(''); setAnswer(''); setIsLoading(true)
    try {
      const result = await sendChatRequest(value)
      setAnswer(result.answer)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Đã xảy ra lỗi.')
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
            <form onSubmit={(event) => { event.preventDefault(); navigate('/chatbot') }}>
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
              <button type="button" onClick={() => navigate('/chatbot')} aria-label="Đăng nhập bằng Google">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 12.2c0-.7-.1-1.3-.2-1.9H12v3.6h4.5a3.9 3.9 0 0 1-1.7 2.5v2.3h2.9c1.7-1.6 2.3-3.8 2.3-6.5Z"/><path d="M12 20c2.2 0 4.1-.7 5.5-2l-2.9-2.3c-.8.5-1.8.9-2.9.9-2.1 0-3.9-1.4-4.6-3.4h-3v2.4A8.3 8.3 0 0 0 12 20Z"/><path d="M7.1 13.2a5 5 0 0 1 0-3.1V7.7h-3a8.3 8.3 0 0 0 0 7.9l3-2.4Z"/><path d="M12 6.7c1.2 0 2.3.4 3.2 1.3l2.4-2.4A8 8 0 0 0 4.1 7.7l3 2.4A5 5 0 0 1 12 6.7Z"/></svg>
                Google
              </button>
              <button type="button" onClick={() => navigate('/chatbot')} aria-label="Đăng nhập bằng Microsoft">
                <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="8" height="8"/><rect x="13" y="3" width="8" height="8"/><rect x="3" y="13" width="8" height="8"/><rect x="13" y="13" width="8" height="8"/></svg>
                Microsoft
              </button>
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
          <button className="icon-button" aria-label="Thông báo"><Icon name="bell" /></button>
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
        <section className="hero">
          <h1>Chào bạn, tôi có thể giúp gì cho<br />{' '}nghiệp vụ của bạn hôm nay?</h1>
          <button className="date-picker" type="button"><Icon name="calendar" /><span>Ngày hiệu lực:</span><strong>30/10/2024</strong></button>
          <form className="prompt-box" onSubmit={submit}>
            <textarea aria-label="Câu hỏi nghiệp vụ" value={question} onChange={(e) => setQuestion(e.target.value)} onKeyDown={onKeyDown} placeholder="Nhập câu hỏi hoặc mô tả tình huống nghiệp vụ..." />
            <div className="prompt-tools">
              <div className="left-tools">
                <button type="button" aria-label="Lịch sử"><Icon name="history" /></button>
                <button type="button" aria-label="Đính kèm tệp" onClick={() => fileInput.current?.click()}><Icon name="paperclip" /></button>
                <button type="button" aria-label="Gợi ý"><Icon name="pin" /></button>
              </div>
              <button className="send-button" type="submit" disabled={!question.trim() || isLoading} aria-label="Gửi câu hỏi"><Icon name="arrow" /></button>
            </div>
          </form>
          <input ref={fileInput} type="file" hidden />
          {(isLoading || answer || error) && <div className={`response ${error ? 'response-error' : ''}`} aria-live="polite">{isLoading ? 'Đang xử lý yêu cầu...' : error || answer}</div>}
        </section>
      </main>

      <footer>
        <p>© 2024 Sovereign Compliance AI. All rights reserved.</p>
        <nav><a href="#privacy">Chính sách bảo mật</a><a href="#terms">Điều khoản dịch vụ</a></nav>
      </footer>

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
              <button className="logout-nav" type="button" onClick={() => { setIsSettingsOpen(false); navigate('/login') }}><span>↪</span> Đăng xuất</button>
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
