'use client'

import { FormEvent, KeyboardEvent, ReactNode, useEffect, useRef, useState } from 'react'

type Source = { clause_id?: string; clauseId?: string; name?: string; description?: string; body?: string; url?: string; source_url?: string; is_current?: boolean }
type Turn = { id: number; question: string; answer: string; sources: Source[]; warning?: string; scopeInfo?: string; error?: string; loading?: boolean; latencyMs?: number; confidence?: string | number; answerType?: string; completedAt?: number }
type Settings = { apiUrl: string; audience: string }
type HistoryEntry = { question: string; answer?: string; at: number }
type PageContext = { title: string; url: string; favIconUrl?: string }
type PageExtract = { ok: boolean; title?: string; url?: string; text?: string; hash?: string; warnings?: string[]; truncated?: boolean; stats?: { characters: number; blocks: number; readableFrames: number }; scope?: { scoped: boolean; keywords: string[]; matchedBlocks: number }; error?: string }
type CachedPageData = { url: string; title?: string; text: string; hash: string; extractedAt: number; warnings?: string[]; truncated?: boolean; stats?: PageExtract['stats'] }

const DEFAULTS: Settings = { apiUrl: 'https://ibib-vic-2026.onrender.com', audience: 'employee' }
const HOME_URL = 'http://localhost:5173/chatbot'
const LOGIN_URL = 'http://localhost:5173/login'
const storageGet = <T,>(keys: string[]) => new Promise<T>((resolve) => chrome.storage.local.get(keys, (value) => resolve(value as T)))
const storageSet = (value: Record<string, unknown>) => new Promise<void>((resolve) => chrome.storage.local.set(value, resolve))

type FrameExtract = { ok: boolean; title?: string; url?: string; text?: string; fullLength?: number; keywords?: string[]; matchedBlocks?: number; scoped?: boolean; error?: string }
const scopeFetchedText = (rawText: string, query: string): FrameExtract => {
  const text = rawText.replace(/\u00a0/g, ' ').replace(/[ \t]+/g, ' ').replace(/\n{3,}/g, '\n\n').trim().slice(0, 300_000)
  const stopWords = new Set(['của', 'cho', 'với', 'trong', 'được', 'những', 'các', 'này', 'đó', 'là', 'và', 'hoặc', 'thì', 'về', 'theo', 'tôi', 'bạn', 'hãy', 'gì', 'như', 'nào', 'nói', 'tìm', 'thông', 'tin', 'trang', 'liên', 'quan', 'đến', 'đang', 'xem'])
  const keywords = [...new Set((query || '').toLocaleLowerCase('vi-VN').match(/[\p{L}\p{N}_-]{1,}/gu) || [])].filter((word) => (word.length >= 3 || /^\d+$/.test(word)) && !stopWords.has(word)).slice(0, 12)
  if (!keywords.length) return { ok: Boolean(text), text: text.slice(0, 80_000), fullLength: text.length, keywords, matchedBlocks: 0, scoped: false }
  const blocks = text.split(/\n+/).map((item) => item.trim()).filter((item) => item.length > 1)
  const ranked = blocks.map((block, index) => { const normalized = block.toLocaleLowerCase('vi-VN'); return { index, score: keywords.filter((word) => /^\d+$/.test(word) ? new RegExp(`(^|\\D)${word}(\\D|$)`).test(normalized) : normalized.includes(word)).length } }).filter((item) => item.score > 0).sort((a, b) => b.score - a.score)
  const selected = new Set<number>()
  ranked.slice(0, 30).forEach(({ index }) => { selected.add(index); if (index > 0) selected.add(index - 1); if (index < blocks.length - 1) selected.add(index + 1) })
  const scopedText = selected.size ? [...selected].sort((a, b) => a - b).map((index) => blocks[index]).join('\n\n') : ''
  return { ok: Boolean(scopedText), text: scopedText.slice(0, 50_000), fullLength: text.length, keywords, matchedBlocks: ranked.length, scoped: true }
}
const fetchFrameReader = async (url: string, query: string): Promise<FrameExtract> => {
  if (!/^https?:/i.test(url)) return { ok: false, error: 'Frame không có URL HTTP có thể tải.' }
  const response = await fetch(url, { credentials: 'include', cache: 'no-store' })
  if (!response.ok) return { ok: false, error: `Không thể tải frame (${response.status}).` }
  const html = await response.text()
  const documentFromFrame = new DOMParser().parseFromString(html, 'text/html')
  documentFromFrame.querySelectorAll('script,style,noscript,nav,footer,form,button,input,textarea,select,[aria-hidden="true"]').forEach((node) => node.remove())
  return { ...scopeFetchedText(documentFromFrame.body?.innerText || documentFromFrame.body?.textContent || '', query), title: documentFromFrame.title, url }
}
const readRenderedSnapshot = async (tabId: number, query: string): Promise<FrameExtract> => {
  const target = { tabId }
  const attach = () => new Promise<void>((resolve, reject) => chrome.debugger.attach(target, '1.3', () => {
    const error = chrome.runtime.lastError
    if (error) reject(new Error(error.message))
    else resolve()
  }))
  const capture = () => new Promise<{ strings?: string[]; documents?: Array<{ layout?: { text?: number[] }; nodes?: { nodeValue?: number[] } }> }>((resolve, reject) => {
    chrome.debugger.sendCommand(target, 'DOMSnapshot.captureSnapshot', { computedStyles: [], includeDOMRects: false, includePaintOrder: false }, (result) => {
      const error = chrome.runtime.lastError
      if (error) reject(new Error(error.message))
      else resolve(result as { strings?: string[]; documents?: Array<{ layout?: { text?: number[] }; nodes?: { nodeValue?: number[] } }> })
    })
  })
  await attach()
  try {
    const snapshot = await capture()
    const strings = snapshot.strings || []
    const rendered = [] as string[]
    for (const documentSnapshot of snapshot.documents || []) {
      for (const stringIndex of documentSnapshot.layout?.text || []) {
        const value = strings[stringIndex]
        if (value?.trim()) rendered.push(value)
      }
    }
    const result = scopeFetchedText(rendered.join('\n'), query)
    return { ...result, title: 'Nội dung đang hiển thị', url: '' }
  } finally {
    await new Promise<void>((resolve) => chrome.debugger.detach(target, () => resolve()))
  }
}
const injectFrameReader = async (tabId: number, frameId: number, query: string): Promise<FrameExtract> => {
  const injected = await chrome.scripting.executeScript({
    target: { tabId, frameIds: [frameId] },
    world: 'ISOLATED',
    args: [query],
    func: (frameQuery: string) => {
      const text = (document.body?.innerText || document.body?.textContent || '')
        .replace(/\u00a0/g, ' ')
        .replace(/[ \t]+/g, ' ')
        .replace(/\n{3,}/g, '\n\n')
        .trim()
        .slice(0, 160_000)
      const stopWords = new Set(['của', 'cho', 'với', 'trong', 'được', 'những', 'các', 'này', 'đó', 'là', 'và', 'hoặc', 'thì', 'về', 'theo', 'tôi', 'bạn', 'hãy', 'gì', 'như', 'nào', 'nói', 'tìm', 'thông', 'tin', 'trang', 'liên', 'quan', 'đến', 'đang', 'xem'])
      const keywords = [...new Set((frameQuery || '').toLocaleLowerCase('vi-VN').match(/[\p{L}\p{N}_-]{1,}/gu) || [])].filter((word) => (word.length >= 3 || /^\d+$/.test(word)) && !stopWords.has(word)).slice(0, 12)
      if (!keywords.length) return { ok: Boolean(text), title: document.title, url: location.href, text: text.slice(0, 80_000), fullLength: text.length, keywords, matchedBlocks: 0, scoped: false }
      const blocks = text.split(/\n+/).map((item) => item.trim()).filter((item) => item.length > 1)
      const ranked = blocks.map((block, index) => {
        const normalized = block.toLocaleLowerCase('vi-VN')
        return { index, score: keywords.filter((word) => /^\d+$/.test(word) ? new RegExp(`(^|\\D)${word}(\\D|$)`).test(normalized) : normalized.includes(word)).length }
      }).filter((item) => item.score > 0).sort((a, b) => b.score - a.score)
      const selected = new Set<number>()
      ranked.slice(0, 28).forEach(({ index }) => {
        selected.add(index)
        if (index > 0) selected.add(index - 1)
        if (index < blocks.length - 1) selected.add(index + 1)
      })
      const scopedText = selected.size ? [...selected].sort((a, b) => a - b).map((index) => blocks[index]).join('\n\n') : ''
      return { ok: Boolean(text), title: document.title, url: location.href, text: scopedText.slice(0, 40_000), fullLength: text.length, keywords, matchedBlocks: ranked.length, scoped: true }
    },
  })
  return (injected[0]?.result || { ok: false, error: 'Frame không trả dữ liệu.' }) as FrameExtract
}
const readAcrossFrames = async (tabId: number, query = ''): Promise<PageExtract> => {
  const frames = await chrome.webNavigation.getAllFrames({ tabId }).catch(() => null)
  if (!frames?.length) return chrome.tabs.sendMessage(tabId, { type: 'READ_CURRENT_PAGE', query }) as Promise<PageExtract>
  const results = await Promise.all(frames.map(async (frame) => {
    try {
      return await chrome.tabs.sendMessage(tabId, { type: 'READ_FRAME_CONTENT', query }, { frameId: frame.frameId }) as FrameExtract
    } catch {
      try {
        const injected = await injectFrameReader(tabId, frame.frameId, query)
        if (injected.ok && injected.text) return injected
      } catch {
        // Tiếp tục bằng URL của frame bên dưới.
      }
      try {
        return await fetchFrameReader(frame.url, query)
      } catch (error) {
        return { ok: false, error: error instanceof Error ? error.message : 'Không thể đọc frame.' } as FrameExtract
      }
    }
  }))
  if (frames.some((frame) => frame.url.includes('thuvienphapluat.vn'))) {
    try {
      const rendered = await readRenderedSnapshot(tabId, query)
      if (rendered.ok && rendered.text) results.push(rendered)
    } catch {
      // DevTools đang mở hoặc Chrome không cho phép attach; giữ các lớp đọc trước.
    }
  }
  const readable = results.filter((result) => result.ok && result.text)
  if (!readable.length) return { ok: false, error: 'Không tìm thấy frame có nội dung có thể đọc.' }
  readable.sort((a, b) => query
    ? Number(b.matchedBlocks || 0) - Number(a.matchedBlocks || 0)
    : Number(b.fullLength || 0) - Number(a.fullLength || 0))
  const uniqueTexts = [...new Set(readable.map((result) => result.text!.trim()).filter(Boolean))]
  const text = uniqueTexts.join('\n\n--- Nội dung frame tiếp theo ---\n\n').slice(0, 80_000)
  const inaccessible = results.length - readable.length
  const main = results[0]
  return {
    ok: true,
    title: main?.title || readable[0].title,
    url: main?.url || readable[0].url,
    text,
    warnings: inaccessible && readable.length === 1 ? [`${inaccessible} frame không cung cấp nội dung có thể đọc.`] : [],
    truncated: readable.some((result) => Number(result.fullLength || 0) > 80_000),
    stats: { characters: text.length, blocks: readable.reduce((sum, result) => sum + Number(result.matchedBlocks || 0), 0), readableFrames: readable.length },
    scope: {
      scoped: Boolean(query),
      keywords: [...new Set(readable.flatMap((result) => result.keywords || []))],
      matchedBlocks: readable.reduce((sum, result) => sum + Number(result.matchedBlocks || 0), 0),
    },
  }
}

const inlineMarkdown = (text: string): ReactNode[] => {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.filter(Boolean).map((part, index) => part.startsWith('**') && part.endsWith('**')
    ? <strong className="clause-highlight" key={index}>{part.slice(2, -2)}</strong>
    : <span key={index}>{part}</span>)
}

const MarkdownAnswer = ({ content }: { content: string }) => {
  const blocks: ReactNode[] = []
  let bullets: string[] = []
  const flushBullets = () => {
    if (!bullets.length) return
    blocks.push(<ul key={`list-${blocks.length}`}>{bullets.map((line, index) => <li key={index}>{inlineMarkdown(line)}</li>)}</ul>)
    bullets = []
  }
  content.split('\n').forEach((raw) => {
    const line = raw.trim()
    if (line.startsWith('- ') || line.startsWith('• ')) {
      bullets.push(line.slice(2))
      return
    }
    flushBullets()
    if (!line) return
    if (line.startsWith('### ')) blocks.push(<h4 key={blocks.length}>{inlineMarkdown(line.slice(4))}</h4>)
    else if (line.startsWith('## ')) blocks.push(<h3 key={blocks.length}>{inlineMarkdown(line.slice(3))}</h3>)
    else if (line.startsWith('# ')) blocks.push(<h2 key={blocks.length}>{inlineMarkdown(line.slice(2))}</h2>)
    else blocks.push(<p key={blocks.length}>{inlineMarkdown(line)}</p>)
  })
  flushBullets()
  return <div className="markdown-answer">{blocks}</div>
}

const confidenceLabel = (confidence?: string | number, sourceCount = 0) => {
  if (typeof confidence === 'number') return `${Math.round(confidence <= 1 ? confidence * 100 : confidence)}%`
  if (confidence) return confidence
  return sourceCount > 0 ? 'Có nguồn đối chiếu' : 'Chưa có nguồn'
}

const isPageLookupIntent = (question: string) => {
  const normalized = question
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('vi-VN')
    .replace(/\s+/g, ' ')
    .trim()
  const pageTerms = '(?:trang|website|web|tai lieu|van ban)'
  return [
    new RegExp(`(?:tim|kiem tra|tra cuu|cho biet|thong tin).*(?:trong|tren) ${pageTerms}`),
    new RegExp(`${pageTerms} (?:nay|dang xem|hien tai)`),
    new RegExp(`(?:trong|tren) ${pageTerms}`),
    /noi dung dang xem/,
    /dua vao (?:noi dung )?(?:trang|tai lieu|van ban)/,
    /lien quan den tu .* trong/,
    /tom tat (?:trang|website|tai lieu|van ban)/,
  ].some((pattern) => pattern.test(normalized))
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
  const [cachedPageData, setCachedPageData] = useState<CachedPageData | null>(null)
  const [copied, setCopied] = useState('')
  const [copyFailed, setCopyFailed] = useState('')
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
    void storageGet<Partial<Settings> & { pendingQuestion?: string; pendingAt?: number; chatHistory?: HistoryEntry[]; extensionAuthenticated?: boolean; authenticatedRole?: string; cachedPageData?: CachedPageData }>(['apiUrl', 'audience', 'pendingQuestion', 'pendingAt', 'chatHistory', 'extensionAuthenticated', 'authenticatedRole', 'cachedPageData']).then((value) => {
      setSettings({ apiUrl: value.apiUrl || DEFAULTS.apiUrl, audience: value.audience || DEFAULTS.audience })
      setAuthenticated(value.extensionAuthenticated === true)
      if (value.authenticatedRole) setSettings((current) => ({ ...current, audience: value.authenticatedRole || DEFAULTS.audience }))
      setHistory(Array.isArray(value.chatHistory) ? value.chatHistory : [])
      if (value.cachedPageData && Date.now() - value.cachedPageData.extractedAt < 300_000) {
        setCachedPageData(value.cachedPageData)
      }
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
      if (area !== 'local') return
      if (changes.pendingQuestion?.newValue) {
        setQuestion(String(changes.pendingQuestion.newValue))
        void storageSet({ pendingQuestion: '', pendingAt: 0 })
        window.setTimeout(() => inputRef.current?.focus(), 0)
      }
      // Auto-detect cached page data
      if (changes.cachedPageData?.newValue) {
        const cached = changes.cachedPageData.newValue as CachedPageData
        if (Date.now() - cached.extractedAt < 300_000) {
          setCachedPageData(cached)
        }
      }
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
      setTurns((current) => current.map((turn) => turn.id === id ? {
        ...turn,
        answer: payload.answer || 'Không có nội dung trả lời.',
        sources: payload.sources || [],
        warning: payload.conflictWarning,
        latencyMs: payload.latencyMs,
        confidence: payload.confidence,
        answerType: payload.answerType || 'Tra cứu quy định',
        completedAt: Date.now(),
        loading: false,
      } : turn))
      const nextHistory = [...history, { question: displayQuestion, answer: payload.answer, at: Date.now() }].slice(-30)
      setHistory(nextHistory)
      await storageSet({ chatHistory: nextHistory })
    } catch (error) {
      if (fallbackAnswer) {
        setTurns((current) => current.map((turn) => turn.id === id ? { ...turn, answer: fallbackAnswer, error: undefined, answerType: 'Tóm tắt cục bộ', completedAt: Date.now(), loading: false } : turn))
        const nextHistory = [...history, { question: displayQuestion, answer: fallbackAnswer, at: Date.now() }].slice(-30)
        setHistory(nextHistory)
        await storageSet({ chatHistory: nextHistory })
      } else {
        setTurns((current) => current.map((turn) => turn.id === id ? { ...turn, error: error instanceof Error ? error.message : 'Không thể tra cứu.', loading: false } : turn))
      }
    }
  }

  const runPageRequest = async (pageQuestion?: string) => {
    if (!pageContext || loading || readingPage) return
    setReadingPage(true)
    const id = Date.now()
    const cleanQuestion = pageQuestion?.trim() || ''
    const displayQuestion = cleanQuestion || `Tóm tắt trang: ${pageContext.title}`
    if (cleanQuestion) setQuestion('')
    setTurns((current) => [...current, { id, question: displayQuestion, answer: '', sources: [], loading: true }])
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
      if (!tab?.id) throw new Error('Không tìm thấy tab đang xem.')
      let page = await readAcrossFrames(tab.id, cleanQuestion)
      if (!cleanQuestion && (!page.ok || !page.text) && cachedPageData?.url === pageContext.url && Date.now() - cachedPageData.extractedAt < 300_000) {
        page = { ok: true, ...cachedPageData }
      }
      if (!page.ok || !page.text) throw new Error(page.error || 'Trang không có nội dung có thể đọc.')
      const response = await fetch(`${settings.apiUrl.replace(/\/$/, '')}/api/summarize-page`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: page.title || pageContext.title, url: page.url || pageContext.url, text: page.text, question: cleanQuestion || null, keywords: page.scope?.keywords || [], warnings: page.warnings || [], truncated: !cleanQuestion && page.truncated === true }),
      })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload.detail || `API trả lỗi ${response.status}`)
      const extraction = page.scope?.scoped
        ? `Đã thu hẹp theo ${page.scope.keywords.length} từ khóa, tìm thấy ${page.scope.matchedBlocks} khối liên quan.`
        : page.stats ? `Đã đọc ${page.stats.characters.toLocaleString('vi-VN')} ký tự · ${page.stats.blocks} khối nội dung${page.stats.readableFrames ? ` · ${page.stats.readableFrames} iframe` : ''}` : undefined
      setTurns((current) => current.map((turn) => turn.id === id ? {
        ...turn,
        answer: payload.answer || 'Không có nội dung tóm tắt.',
        sources: payload.sources || [],
        warning: payload.conflictWarning,
        scopeInfo: extraction,
        latencyMs: payload.latencyMs,
        confidence: payload.confidence,
        answerType: payload.answerType || (cleanQuestion ? 'Hỏi đáp theo trang' : 'Tóm tắt trang web'),
        completedAt: Date.now(),
        loading: false,
      } : turn))
      const nextHistory = [...history, { question: displayQuestion, answer: payload.answer, at: Date.now() }].slice(-30)
      setHistory(nextHistory)
      await storageSet({ chatHistory: nextHistory })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Không thể đọc trang đang xem.'
      setTurns((current) => current.map((turn) => turn.id === id ? { ...turn, error: message, loading: false } : turn))
    } finally {
      setReadingPage(false)
    }
  }

  const send = async (event?: FormEvent) => {
    event?.preventDefault()
    const clean = question.trim()
    if (!clean) return
    if (pageContext && isPageLookupIntent(clean)) await runPageRequest(clean)
    else await runQuery(clean)
  }

  const summarizeCurrentPage = async () => runPageRequest()

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

  const copyText = async (text: string, key: string) => {
    if (!text.trim()) return
    let success = false
    try {
      await navigator.clipboard.writeText(text)
      success = true
    } catch {
      const temporary = document.createElement('textarea')
      temporary.value = text
      temporary.setAttribute('readonly', '')
      temporary.style.position = 'fixed'
      temporary.style.left = '-9999px'
      temporary.style.opacity = '0'
      document.body.append(temporary)
      temporary.focus()
      temporary.select()
      temporary.setSelectionRange(0, temporary.value.length)
      success = document.execCommand('copy')
      temporary.remove()
    }
    if (success) {
      setCopyFailed('')
      setCopied(key)
      window.setTimeout(() => setCopied((current) => current === key ? '' : current), 1_500)
    } else {
      setCopied('')
      setCopyFailed(key)
      window.setTimeout(() => setCopyFailed((current) => current === key ? '' : current), 2_000)
    }
  }

  const sourceText = (source: Source) => [source.clause_id || source.clauseId, source.name, source.body, source.description].filter(Boolean).join('\n')

  if (!authenticated) return <div className={`panel-shell auth-shell ${typeof window !== 'undefined' && window.self !== window.top ? 'embedded-panel' : ''}`}><header><button className="brand brand-link" type="button" title="Truy cập trang chủ" onClick={() => void openHomepage()}><i>◆</i><div><strong>SovAI</strong><small>Trợ lý tuân thủ</small></div></button></header><main className="auth-gate"><i>AI</i><h1>Đăng nhập để sử dụng</h1><p>Truy cập trang chủ để đăng nhập hoặc đăng ký. Tiện ích sẽ tự đồng bộ tài khoản và quyền sử dụng của bạn.</p><button type="button" onClick={() => void startLogin()}>Truy cập trang chủ</button><small>Quay lại tiện ích sau khi đăng nhập thành công.</small></main></div>

  return <div className={`panel-shell ${typeof window !== 'undefined' && window.self !== window.top ? 'embedded-panel' : ''}`}>
    <header><button className="brand brand-link" type="button" title="Truy cập trang chủ" onClick={() => void openHomepage()}><i>◆</i><div><strong>SovAI</strong><small>Trợ lý tuân thủ</small></div></button></header>
    <main ref={conversationRef} className="conversation">{turns.length === 0 ? <section className="welcome"><i>◆</i><h1>Chào bạn, tôi có thể giúp gì?</h1><p>Bôi chọn nội dung trên trang hoặc nhập câu hỏi để tra cứu quy định liên quan.</p><span>Trả lời có đối chiếu nguồn và ngày hiệu lực</span></section> : turns.map((turn) => <article className="turn" key={turn.id}>
      <div className="user">{turn.question}</div>
      <div className={`answer ${turn.loading ? 'loading' : ''} ${turn.error ? 'error' : ''}`}>
        {turn.loading ? <div className="answer-loading"><span />Đang tra cứu quy định…</div> : turn.error ? `Không thể tra cứu: ${turn.error}` : <>
          <header className="answer-heading"><div><span className="answer-kind">{turn.answerType || 'Câu trả lời'}</span><strong>SovAI trả lời</strong></div><button type="button" onClick={() => void copyText(turn.answer, `answer-${turn.id}`)}>{copied === `answer-${turn.id}` ? '✓ Đã sao chép' : copyFailed === `answer-${turn.id}` ? 'Không thể chép' : '⧉ Sao chép'}</button></header>
          {turn.warning && <section className="warning"><strong>⚠ Phát hiện nội dung cần lưu ý</strong><p>{turn.warning}</p></section>}
          <MarkdownAnswer content={turn.answer} />
          {turn.scopeInfo && <div className="scope-info">⌕ {turn.scopeInfo}</div>}
          <footer className="answer-meta"><span>{turn.completedAt ? new Date(turn.completedAt).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }) : 'Vừa xong'}</span>{typeof turn.latencyMs === 'number' && <span>{turn.latencyMs < 1_000 ? `${turn.latencyMs} ms` : `${(turn.latencyMs / 1_000).toFixed(1)} giây`}</span>}<span className={turn.sources.length ? 'confidence-ok' : 'confidence-low'}>● {confidenceLabel(turn.confidence, turn.sources.length)}</span></footer>
          {turn.sources.length > 0 && <details className="sources"><summary><div><strong>Nguồn đối chiếu</strong><span>{turn.sources.length} điều khoản · Nhấn để xem</span></div><i aria-hidden="true" /></summary><div className="source-toolbar"><button type="button" onClick={() => void copyText(turn.sources.map(sourceText).join('\n\n'), `sources-${turn.id}`)}>{copied === `sources-${turn.id}` ? '✓ Đã sao chép' : copyFailed === `sources-${turn.id}` ? 'Không thể chép' : '⧉ Sao chép nguồn'}</button></div><div className="source-list">{turn.sources.map((source, index) => {
            const clauseId = source.clause_id || source.clauseId || 'Nguồn'
            const sourceUrl = source.url || source.source_url
            return <article className="source" key={`${clauseId}-${index}`}><div className="source-title"><mark>{clauseId}</mark><span className={source.is_current === false ? 'source-old' : 'source-current'}>{source.is_current === false ? 'Đã thay thế' : 'Đang hiệu lực'}</span></div><strong>{source.name || clauseId}</strong><p>{source.body || source.description || 'Chưa có nội dung xem trước.'}</p><div className="source-actions"><button type="button" onClick={() => void copyText(sourceText(source), `source-${turn.id}-${index}`)}>{copied === `source-${turn.id}-${index}` ? '✓ Đã chép' : copyFailed === `source-${turn.id}-${index}` ? 'Không thể chép' : '⧉ Sao chép'}</button>{sourceUrl && <a href={sourceUrl} target="_blank" rel="noreferrer">Mở nguồn ↗</a>}</div></article>
          })}</div></details>}
        </>}
      </div>
    </article>)}</main>
    <section className="composer-wrap">{historyOpen && <div className="composer-history"><header><strong>Lịch sử gần đây</strong><button type="button" onClick={() => setHistoryOpen(false)}>×</button></header>{history.length === 0 ? <p>Chưa có cuộc trò chuyện nào.</p> : [...history].reverse().slice(0, 8).map((item) => <button type="button" className="history-row" key={item.at} onClick={() => { setQuestion(item.question); setHistoryOpen(false); inputRef.current?.focus() }}><span>{item.question}</span><small>{new Date(item.at).toLocaleString('vi-VN')}</small></button>)}</div>}<form onSubmit={send}>{pageContext && <div className="active-page" title={pageContext.url}>{pageContext.favIconUrl ? <img src={pageContext.favIconUrl} alt="" /> : <span className="page-fallback">◉</span>}<div><small>Trang đang xem</small><strong>{pageContext.title}</strong><span>{pageContext.url}</span></div><button className="summarize-page" type="button" disabled={loading || readingPage} onClick={() => void summarizeCurrentPage()}>{readingPage ? 'Đang đọc…' : 'Tóm tắt'}</button><button type="button" aria-label="Ẩn ngữ cảnh trang" title="Ẩn ngữ cảnh trang" onClick={() => setPageContext(null)}>×</button></div>}<textarea ref={inputRef} rows={1} value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={keyDown} placeholder="Nhập câu hỏi hoặc mô tả tình huống nghiệp vụ..." /><div className="tools"><div className="left-tools"><button className="circle-tool" type="button" title="Lịch sử" onClick={() => setHistoryOpen((open) => !open)}>↶</button><label className="circle-tool" title="Đính kèm tệp văn bản" aria-label="Đính kèm tệp văn bản"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m21.4 11.6-8.9 8.9a6 6 0 0 1-8.5-8.5l9.6-9.6a4 4 0 0 1 5.7 5.7l-9.6 9.6a2 2 0 0 1-2.8-2.8l8.9-8.9" /></svg><input type="file" accept=".txt,.md,.csv,.json" onChange={(event) => { void attachTextFile(event.target.files?.[0]); event.target.value = '' }} /></label></div><div className="right-tools"><button className="new-chat" type="button" onClick={() => { setTurns([]); setQuestion(''); setHistoryOpen(false) }}>＋ <span>New chat</span></button><button id="send" type="submit" disabled={!question.trim() || loading}>↑</button></div></div></form><p className="disclaimer">Câu trả lời AI cần được đối chiếu với nguồn trích dẫn.</p></section>
  </div>
}
