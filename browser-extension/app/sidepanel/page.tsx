'use client'

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from 'react'

type Source = { clause_id?: string; clauseId?: string; name?: string; description?: string; body?: string }
type Turn = { id: number; question: string; answer: string; sources: Source[]; warning?: string; error?: string; loading?: boolean }
type Settings = { apiUrl: string; audience: string }
type HistoryEntry = { question: string; answer?: string; at: number }
type PageContext = { title: string; url: string; favIconUrl?: string }
type PageExtract = { ok: boolean; title?: string; url?: string; text?: string; error?: string }

const DEFAULTS: Settings = { apiUrl: 'http://localhost:8000', audience: 'employee' }
const HOME_URL = 'http://localhost:5173/chatbot'
const LOGIN_URL = 'http://localhost:5173/login'
const storageGet = <T,>(keys: string[]) => new Promise<T>((resolve) => chrome.storage.local.get(keys, (value) => resolve(value as T)))
const storageSet = (value: Record<string, unknown>) => new Promise<void>((resolve) => chrome.storage.local.set(value, resolve))

const summarizeLocally = (text: string) => {
  const sentences = text
    .replace(/\s+/g, ' ')
    .split(/(?<=[.!?;:])\s+/)
    .map((sentence) => sentence.trim())
    .filter((sentence) => sentence.length >= 45 && sentence.length <= 420)
  const unique = sentences.filter((sentence, index) => sentences.findIndex((item) => item.toLocaleLowerCase('vi-VN') === sentence.toLocaleLowerCase('vi-VN')) === index)
  const selected = unique.slice(0, 7)
  if (selected.length === 0) return 'Không tìm thấy đủ nội dung văn bản để tạo bản tóm tắt.'
  return `Tóm tắt nhanh (chế độ cục bộ do API chưa kết nối):\n\n${selected.map((sentence) => `• ${sentence}`).join('\n')}`
}

export default function SidePanelPage() {
  const [settings, setSettings] = useState(DEFAULTS)
  const [authenticated, setAuthenticated] = useState(false)
  const [question, setQuestion] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [historyOpen, setHistoryOpen] = useState(false)
  const [pageContext, setPageContext] = useState<PageContext | null>(null)
  const [readingPage, setReadingPage] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const conversationRef = useRef<HTMLElement>(null)
  const loading = turns.some((turn) => turn.loading)

  useEffect(() => {
    const surface = window.self !== window.top ? 'floating' : 'native'
    const publishSurface = () => void storageSet({ activeChatSurface: surface, activeChatSurfaceAt: Date.now() })
    publishSurface()
    const heartbeat = window.setInterval(publishSurface, 2_000)
    return () => window.clearInterval(heartbeat)
  }, [])

  useEffect(() => {
    const readActiveTab = async () => {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
      if (!tab?.url || tab.url.startsWith('chrome-extension://')) {
        setPageContext(null)
        return
      }
      setPageContext({ title: tab.title || new URL(tab.url).hostname, url: tab.url, favIconUrl: tab.favIconUrl })
    }
    const onActivated = () => { void readActiveTab() }
    const onUpdated = (_tabId: number, changeInfo: { title?: string; url?: string; status?: string }, tab: chrome.tabs.Tab) => {
      if (tab.active && (changeInfo.title || changeInfo.url || changeInfo.status === 'complete')) void readActiveTab()
    }
    void readActiveTab()
    chrome.tabs.onActivated.addListener(onActivated)
    chrome.tabs.onUpdated.addListener(onUpdated)
    return () => {
      chrome.tabs.onActivated.removeListener(onActivated)
      chrome.tabs.onUpdated.removeListener(onUpdated)
    }
  }, [])

  useEffect(() => {
    void storageGet<Partial<Settings> & { pendingQuestion?: string; pendingAt?: number; chatHistory?: HistoryEntry[]; extensionAuthenticated?: boolean; authenticatedRole?: string }>(['apiUrl', 'audience', 'pendingQuestion', 'pendingAt', 'chatHistory', 'extensionAuthenticated', 'authenticatedRole']).then((value) => {
      setSettings({ apiUrl: value.apiUrl || DEFAULTS.apiUrl, audience: value.audience || DEFAULTS.audience })
      setAuthenticated(value.extensionAuthenticated === true)
      if (value.authenticatedRole) setSettings((current) => ({ ...current, audience: value.authenticatedRole || DEFAULTS.audience }))
      setHistory(Array.isArray(value.chatHistory) ? value.chatHistory : [])
      if (value.pendingQuestion && Date.now() - (value.pendingAt || 0) < 60_000) {
        setQuestion(value.pendingQuestion)
        void storageSet({ pendingQuestion: '', pendingAt: 0 })
      }
    })
  }, [])

  useEffect(() => {
    const receiveAuth = (changes: Record<string, chrome.storage.StorageChange>, area: string) => {
      if (area !== 'local') return
      if (changes.extensionAuthenticated) setAuthenticated(changes.extensionAuthenticated.newValue === true)
      if (changes.authenticatedRole?.newValue) setSettings((current) => ({ ...current, audience: String(changes.authenticatedRole.newValue) }))
    }
    chrome.storage.onChanged.addListener(receiveAuth)
    return () => chrome.storage.onChanged.removeListener(receiveAuth)
  }, [])

  useEffect(() => {
    const receiveSelection = (changes: Record<string, chrome.storage.StorageChange>, area: string) => {
      if (area !== 'local' || !changes.pendingQuestion?.newValue) return
      setQuestion(String(changes.pendingQuestion.newValue))
      void storageSet({ pendingQuestion: '', pendingAt: 0 })
      window.setTimeout(() => inputRef.current?.focus(), 0)
    }
    chrome.storage.onChanged.addListener(receiveSelection)
    return () => chrome.storage.onChanged.removeListener(receiveSelection)
  }, [])

  useEffect(() => {
    const input = inputRef.current
    if (!input) return
    input.style.height = 'auto'
    input.style.height = `${Math.min(input.scrollHeight, 130)}px`
  }, [question])

  useEffect(() => {
    const box = conversationRef.current
    if (box) box.scrollTop = box.scrollHeight
  }, [turns])

  const openHomepage = async () => {
    await chrome.tabs.create({ url: HOME_URL })
  }

  const startLogin = async () => {
    const [currentTab] = await chrome.tabs.query({ active: true, currentWindow: true })
    if (currentTab?.id) await storageSet({ authReturnTabId: currentTab.id })
    await chrome.tabs.create({ url: LOGIN_URL })
  }

  const runQuery = async (clean: string, displayQuestion = clean, fallbackAnswer?: string) => {
    if (!clean || loading) return
    const id = Date.now()
    setQuestion('')
    setTurns((current) => [...current, { id, question: displayQuestion, answer: '', sources: [], loading: true }])
    try {
      const response = await fetch(`${settings.apiUrl.replace(/\/$/, '')}/api/chat`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: clean, audience: settings.audience, mode: 'system' }),
      })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload.detail || `API trả lỗi ${response.status}`)
      setTurns((current) => current.map((turn) => turn.id === id ? { ...turn, answer: payload.answer || 'Không có nội dung trả lời.', sources: payload.sources || [], warning: payload.conflictWarning, loading: false } : turn))
      const nextHistory = [...history, { question: displayQuestion, answer: payload.answer, at: Date.now() }].slice(-30)
      setHistory(nextHistory)
      await storageSet({ chatHistory: nextHistory })
    } catch (error) {
      if (fallbackAnswer) {
        setTurns((current) => current.map((turn) => turn.id === id ? { ...turn, answer: fallbackAnswer, error: undefined, loading: false } : turn))
        const nextHistory = [...history, { question: displayQuestion, answer: fallbackAnswer, at: Date.now() }].slice(-30)
        setHistory(nextHistory)
        await storageSet({ chatHistory: nextHistory })
      } else {
        setTurns((current) => current.map((turn) => turn.id === id ? { ...turn, error: error instanceof Error ? error.message : 'Không thể tra cứu.', loading: false } : turn))
      }
    }
  }

  const send = async (event?: FormEvent) => {
    event?.preventDefault()
    await runQuery(question.trim())
  }

  const summarizeCurrentPage = async () => {
    if (!pageContext || loading || readingPage) return
    setReadingPage(true)
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
      if (!tab?.id) throw new Error('Không tìm thấy tab đang xem.')
      const page = await chrome.tabs.sendMessage(tab.id, { type: 'READ_CURRENT_PAGE' }) as PageExtract
      if (!page.ok || !page.text) throw new Error(page.error || 'Trang không có nội dung có thể đọc.')
      const prompt = `Hãy tóm tắt trang web dưới đây bằng tiếng Việt. Nêu các ý chính, nghĩa vụ hoặc mốc thời gian quan trọng và cảnh báo điểm cần kiểm chứng.\n\nTiêu đề: ${page.title || pageContext.title}\nURL: ${page.url || pageContext.url}\n\nNội dung trang:\n${page.text}`
      await runQuery(prompt, `Tóm tắt trang: ${page.title || pageContext.title}`, summarizeLocally(page.text))
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Không thể đọc trang đang xem.'
      setTurns((current) => [...current, { id: Date.now(), question: `Tóm tắt trang: ${pageContext.title}`, answer: '', sources: [], error: message }])
    } finally {
      setReadingPage(false)
    }
  }

  const keyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void send() }
  }

  const attachTextFile = async (file?: File) => {
    if (!file) return
    const content = await file.text()
    const excerpt = content.slice(0, 8_000)
    setQuestion((current) => current.trim() ? `${current.trim()}\n\nTệp ${file.name}:\n${excerpt}` : `Tệp ${file.name}:\n${excerpt}`)
    inputRef.current?.focus()
  }

  if (!authenticated) return <div className={`panel-shell auth-shell ${typeof window !== 'undefined' && window.self !== window.top ? 'embedded-panel' : ''}`}><header><button className="brand brand-link" type="button" title="Truy cập trang chủ" onClick={() => void openHomepage()}><i>◆</i><div><strong>Sovereign Compliance AI</strong><small>Trợ lý tuân thủ</small></div></button></header><main className="auth-gate"><i>AI</i><h1>Đăng nhập để sử dụng</h1><p>Truy cập trang chủ để đăng nhập hoặc đăng ký. Tiện ích sẽ tự đồng bộ tài khoản và quyền sử dụng của bạn.</p><button type="button" onClick={() => void startLogin()}>Truy cập trang chủ</button><small>Quay lại tiện ích sau khi đăng nhập thành công.</small></main></div>

  return <div className={`panel-shell ${typeof window !== 'undefined' && window.self !== window.top ? 'embedded-panel' : ''}`}>
    <header><button className="brand brand-link" type="button" title="Truy cập trang chủ" onClick={() => void openHomepage()}><i>◆</i><div><strong>Sovereign Compliance AI</strong><small>Trợ lý tuân thủ</small></div></button></header>
    <main ref={conversationRef} className="conversation">{turns.length === 0 ? <section className="welcome"><i>◆</i><h1>Chào bạn, tôi có thể giúp gì?</h1><p>Bôi chọn nội dung trên trang hoặc nhập câu hỏi để tra cứu quy định liên quan.</p><span>Trả lời có đối chiếu nguồn và ngày hiệu lực</span></section> : turns.map((turn) => <article className="turn" key={turn.id}><div className="user">{turn.question}</div><div className={`answer ${turn.loading ? 'loading' : ''} ${turn.error ? 'error' : ''}`}>{turn.loading ? 'Đang tra cứu quy định…' : turn.error ? `Không thể tra cứu: ${turn.error}` : <>{turn.warning && <div className="warning">⚠ {turn.warning}</div>}{turn.answer}{turn.sources.length > 0 && <details className="sources"><summary>Nguồn tham khảo ({turn.sources.length})</summary>{turn.sources.map((source, index) => <div className="source" key={`${source.clause_id || source.clauseId}-${index}`}><strong>{source.name || source.clause_id || source.clauseId || 'Nguồn'}</strong><p>{source.description || source.body || ''}</p></div>)}</details>}</>}</div></article>)}</main>
    <section className="composer-wrap">{historyOpen && <div className="composer-history"><header><strong>Lịch sử gần đây</strong><button type="button" onClick={() => setHistoryOpen(false)}>×</button></header>{history.length === 0 ? <p>Chưa có cuộc trò chuyện nào.</p> : [...history].reverse().slice(0, 8).map((item) => <button type="button" className="history-row" key={item.at} onClick={() => { setQuestion(item.question); setHistoryOpen(false); inputRef.current?.focus() }}><span>{item.question}</span><small>{new Date(item.at).toLocaleString('vi-VN')}</small></button>)}</div>}<form onSubmit={send}>{pageContext && <div className="active-page" title={pageContext.url}>{pageContext.favIconUrl ? <img src={pageContext.favIconUrl} alt="" /> : <span className="page-fallback">◉</span>}<div><small>Trang đang xem</small><strong>{pageContext.title}</strong><span>{pageContext.url}</span></div><button className="summarize-page" type="button" disabled={loading || readingPage} onClick={() => void summarizeCurrentPage()}>{readingPage ? 'Đang đọc…' : 'Tóm tắt'}</button><button type="button" aria-label="Ẩn ngữ cảnh trang" title="Ẩn ngữ cảnh trang" onClick={() => setPageContext(null)}>×</button></div>}<textarea ref={inputRef} rows={1} value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={keyDown} placeholder="Nhập câu hỏi hoặc mô tả tình huống nghiệp vụ..." /><div className="tools"><div className="left-tools"><button className="circle-tool" type="button" title="Lịch sử" onClick={() => setHistoryOpen((open) => !open)}>↶</button><label className="circle-tool" title="Đính kèm tệp văn bản" aria-label="Đính kèm tệp văn bản"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m21.4 11.6-8.9 8.9a6 6 0 0 1-8.5-8.5l9.6-9.6a4 4 0 0 1 5.7 5.7l-9.6 9.6a2 2 0 0 1-2.8-2.8l8.9-8.9" /></svg><input type="file" accept=".txt,.md,.csv,.json" onChange={(event) => { void attachTextFile(event.target.files?.[0]); event.target.value = '' }} /></label></div><div className="right-tools"><button className="new-chat" type="button" onClick={() => { setTurns([]); setQuestion(''); setHistoryOpen(false) }}>＋ <span>New chat</span></button><button id="send" type="submit" disabled={!question.trim() || loading}>↑</button></div></div></form><p className="disclaimer">Câu trả lời AI cần được đối chiếu với nguồn trích dẫn.</p></section>
  </div>
}
