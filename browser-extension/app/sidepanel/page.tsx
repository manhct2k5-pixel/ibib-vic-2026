'use client'

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from 'react'

type Source = { clause_id?: string; clauseId?: string; name?: string; description?: string; body?: string }
type Turn = { id: number; question: string; answer: string; sources: Source[]; warning?: string; error?: string; loading?: boolean }
type Settings = { apiUrl: string; audience: string }
type HistoryEntry = { question: string; answer?: string; at: number }

const DEFAULTS: Settings = { apiUrl: 'http://localhost:8000', audience: 'employee' }
const storageGet = <T,>(keys: string[]) => new Promise<T>((resolve) => chrome.storage.local.get(keys, (value) => resolve(value as T)))
const storageSet = (value: Record<string, unknown>) => new Promise<void>((resolve) => chrome.storage.local.set(value, resolve))

export default function SidePanelPage() {
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [settings, setSettings] = useState(DEFAULTS)
  const [saved, setSaved] = useState(false)
  const [question, setQuestion] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [historyOpen, setHistoryOpen] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const conversationRef = useRef<HTMLElement>(null)
  const loading = turns.some((turn) => turn.loading)

  useEffect(() => {
    void storageGet<Partial<Settings> & { pendingQuestion?: string; pendingAt?: number; chatHistory?: HistoryEntry[] }>(['apiUrl', 'audience', 'pendingQuestion', 'pendingAt', 'chatHistory']).then((value) => {
      setSettings({ apiUrl: value.apiUrl || DEFAULTS.apiUrl, audience: value.audience || DEFAULTS.audience })
      setHistory(Array.isArray(value.chatHistory) ? value.chatHistory : [])
      if (value.pendingQuestion && Date.now() - (value.pendingAt || 0) < 60_000) {
        setQuestion(value.pendingQuestion)
        void storageSet({ pendingQuestion: '', pendingAt: 0 })
      }
    })
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

  const saveSettings = async () => {
    const next = { ...settings, apiUrl: settings.apiUrl.trim() || DEFAULTS.apiUrl }
    setSettings(next)
    await storageSet(next)
    setSaved(true)
    window.setTimeout(() => setSaved(false), 1500)
  }

  const send = async (event?: FormEvent) => {
    event?.preventDefault()
    const clean = question.trim()
    if (!clean || loading) return
    const id = Date.now()
    setQuestion('')
    setTurns((current) => [...current, { id, question: clean, answer: '', sources: [], loading: true }])
    try {
      const response = await fetch(`${settings.apiUrl.replace(/\/$/, '')}/api/chat`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: clean, audience: settings.audience, mode: 'system' }),
      })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload.detail || `API trả lỗi ${response.status}`)
      setTurns((current) => current.map((turn) => turn.id === id ? { ...turn, answer: payload.answer || 'Không có nội dung trả lời.', sources: payload.sources || [], warning: payload.conflictWarning, loading: false } : turn))
      const nextHistory = [...history, { question: clean, answer: payload.answer, at: Date.now() }].slice(-30)
      setHistory(nextHistory)
      await storageSet({ chatHistory: nextHistory })
    } catch (error) {
      setTurns((current) => current.map((turn) => turn.id === id ? { ...turn, error: error instanceof Error ? error.message : 'Không thể tra cứu.', loading: false } : turn))
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

  return <div className="panel-shell">
    <header><div className="brand"><i>◆</i><div><strong>Sovereign Compliance AI</strong><small>Trợ lý tuân thủ</small></div></div><button className="icon" type="button" title="Cài đặt" onClick={() => setSettingsOpen((open) => !open)}>⚙</button></header>
    {settingsOpen && <section className="settings"><label>Địa chỉ API<input type="url" value={settings.apiUrl} onChange={(event) => setSettings((current) => ({ ...current, apiUrl: event.target.value }))} /></label><label>Vai trò<select value={settings.audience} onChange={(event) => setSettings((current) => ({ ...current, audience: event.target.value }))}><option value="employee">Nhân viên</option><option value="manager">Quản lý</option><option value="customer">Khách hàng</option></select></label><button type="button" onClick={saveSettings}>Lưu cấu hình</button><span>{saved ? 'Đã lưu' : ''}</span></section>}
    <main ref={conversationRef} className="conversation">{turns.length === 0 ? <section className="welcome"><i>◆</i><h1>Chào bạn, tôi có thể giúp gì?</h1><p>Bôi chọn nội dung trên trang hoặc nhập câu hỏi để tra cứu quy định liên quan.</p><span>Trả lời có đối chiếu nguồn và ngày hiệu lực</span></section> : turns.map((turn) => <article className="turn" key={turn.id}><div className="user">{turn.question}</div><div className={`answer ${turn.loading ? 'loading' : ''} ${turn.error ? 'error' : ''}`}>{turn.loading ? 'Đang tra cứu quy định…' : turn.error ? `Không thể tra cứu: ${turn.error}` : <>{turn.warning && <div className="warning">⚠ {turn.warning}</div>}{turn.answer}{turn.sources.length > 0 && <details className="sources"><summary>Nguồn tham khảo ({turn.sources.length})</summary>{turn.sources.map((source, index) => <div className="source" key={`${source.clause_id || source.clauseId}-${index}`}><strong>{source.name || source.clause_id || source.clauseId || 'Nguồn'}</strong><p>{source.description || source.body || ''}</p></div>)}</details>}</>}</div></article>)}</main>
    <section className="composer-wrap">{historyOpen && <div className="composer-history"><header><strong>Lịch sử gần đây</strong><button type="button" onClick={() => setHistoryOpen(false)}>×</button></header>{history.length === 0 ? <p>Chưa có cuộc trò chuyện nào.</p> : [...history].reverse().slice(0, 8).map((item) => <button type="button" className="history-row" key={item.at} onClick={() => { setQuestion(item.question); setHistoryOpen(false); inputRef.current?.focus() }}><span>{item.question}</span><small>{new Date(item.at).toLocaleString('vi-VN')}</small></button>)}</div>}<form onSubmit={send}><textarea ref={inputRef} rows={1} value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={keyDown} placeholder="Nhập câu hỏi hoặc mô tả tình huống nghiệp vụ..." /><div className="tools"><div className="left-tools"><button className="circle-tool" type="button" title="Lịch sử" onClick={() => setHistoryOpen((open) => !open)}>↶</button><label className="circle-tool" title="Đính kèm tệp văn bản">⌕<input type="file" accept=".txt,.md,.csv,.json" onChange={(event) => { void attachTextFile(event.target.files?.[0]); event.target.value = '' }} /></label></div><div className="right-tools"><button className="new-chat" type="button" onClick={() => { setTurns([]); setQuestion(''); setHistoryOpen(false) }}>＋ <span>New chat</span></button><button id="send" type="submit" disabled={!question.trim() || loading}>↑</button></div></div></form><p className="disclaimer">Câu trả lời AI cần được đối chiếu với nguồn trích dẫn.</p></section>
  </div>
}
