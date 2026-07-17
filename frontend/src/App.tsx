import { useRef, useState } from 'react'
import { sendChatRequest, type SourceItem } from './services/chatApi'
import SourceCard from './components/SourceCard'
import './App.css'

const _now = new Date()
const _pad = (n: number) => String(n).padStart(2, '0')
// Ngày địa phương (không dùng UTC để tránh lệch ngày ở VN buổi tối)
const TODAY = `${_now.getFullYear()}-${_pad(_now.getMonth() + 1)}-${_pad(
  _now.getDate(),
)}`
const IS_MOCK = (import.meta.env.VITE_API_MODE ?? 'mock') === 'mock'

const SAMPLES = [
  'Tỷ lệ an toàn vốn tối thiểu hiện nay là bao nhiêu?',
  'Quy định về tỷ lệ an toàn vốn năm 2019 là gì?',
  '(Khách hàng) Chính sách công khai về an toàn vốn?',
]

function App() {
  const [question, setQuestion] = useState('')
  const [lastQuestion, setLastQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState<SourceItem[]>([])
  const [conflictWarning, setConflictWarning] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [asOf, setAsOf] = useState(TODAY)
  const [audience, setAudience] = useState<'employee' | 'customer'>('employee')
  // Chỉ chấp nhận response của request MỚI NHẤT (chống race khi đổi asOf/audience nhanh)
  const requestId = useRef(0)

  const runQuery = async (
    q: string,
    when: string,
    who: 'employee' | 'customer',
  ) => {
    const clean = q.trim()
    if (!clean) {
      setError('Vui lòng nhập câu hỏi.')
      return
    }

    const myId = ++requestId.current
    setError('')
    setAnswer('')
    setSources([])
    setConflictWarning(null)
    setIsLoading(true)
    setLastQuestion(clean)

    try {
      const response = await sendChatRequest(clean, {
        asOf: when || TODAY,
        audience: who,
      })
      if (myId !== requestId.current) return // đã có request mới hơn
      setAnswer(response.answer)
      setSources(response.sources)
      setConflictWarning(response.conflictWarning ?? null)
    } catch (requestError: unknown) {
      if (myId !== requestId.current) return
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Đã xảy ra lỗi không xác định.',
      )
    } finally {
      if (myId === requestId.current) setIsLoading(false)
    }
  }

  const handleAsOfChange = (value: string) => {
    setAsOf(value)
    if (lastQuestion) void runQuery(lastQuestion, value, audience)
  }

  const handleAudienceChange = (who: 'employee' | 'customer') => {
    setAudience(who)
    if (lastQuestion) void runQuery(lastQuestion, asOf, who)
  }

  const handleClear = () => {
    requestId.current += 1 // vô hiệu hóa request đang chạy
    setQuestion('')
    setLastQuestion('')
    setAnswer('')
    setSources([])
    setConflictWarning(null)
    setError('')
    setAsOf(TODAY)
    setAudience('employee')
    setIsLoading(false)
  }

  const hasResult =
    !!answer || sources.length > 0 || !!conflictWarning?.trim()

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="mark" />
          Trợ lý tra cứu văn bản ngân hàng thông minh
          <small>· SHB</small>
        </div>
        <div className="spacer" />
        <div className="mode-toggle" role="group" aria-label="Đối tượng tra cứu">
          <button
            type="button"
            className={audience === 'employee' ? 'on' : ''}
            disabled={isLoading}
            onClick={() => handleAudienceChange('employee')}
          >
            Nhân viên
          </button>
          <button
            type="button"
            className={audience === 'customer' ? 'on' : ''}
            disabled={isLoading}
            onClick={() => handleAudienceChange('customer')}
          >
            Khách hàng
          </button>
        </div>
        {audience === 'customer' && (
          <span className="public-tag">Chế độ công khai</span>
        )}
        <label className="asof" htmlFor="asof">
          Mốc hiệu lực
          <input
            id="asof"
            type="date"
            value={asOf}
            disabled={isLoading}
            onChange={(event) => handleAsOfChange(event.target.value)}
          />
        </label>
        {IS_MOCK && <span className="mock-tag">Chế độ mock</span>}
      </header>

      <main className="chat">
        <form
          className="request-card"
          onSubmit={(event) => {
            event.preventDefault()
            void runQuery(question, asOf, audience)
          }}
        >
          <label htmlFor="question">Câu hỏi về quy định</label>
          <textarea
            id="question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ví dụ: Tỷ lệ an toàn vốn tối thiểu hiện nay?"
            rows={3}
            disabled={isLoading}
          />
          <div className="button-row">
            <button
              className="secondary-button"
              type="button"
              onClick={handleClear}
              disabled={isLoading}
            >
              Xóa
            </button>
            <button className="primary-button" type="submit" disabled={isLoading}>
              {isLoading ? 'Đang tra cứu...' : 'Gửi'}
            </button>
          </div>
          {error && <p className="error-message">{error}</p>}
        </form>

        <section className="result-card" aria-live="polite">
          <h2>Kết quả</h2>

          {isLoading && (
            <div className="loading-state">
              <span className="spinner" />
              Đang tra cứu...
            </div>
          )}

          {!isLoading && !hasResult && (
            <div className="empty-state">
              Nhập câu hỏi, hoặc thử một trong các mẫu:
              <div className="samples">
                {SAMPLES.map((s) => (
                  <button
                    key={s}
                    type="button"
                    className="sample-chip"
                    onClick={() => {
                      setQuestion(s)
                      void runQuery(s, asOf, audience)
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {!isLoading && hasResult && (
            <>
              {conflictWarning?.trim() && (
                <div className="conflict-banner">
                  <span aria-hidden="true">⚠</span>
                  <span>{conflictWarning}</span>
                </div>
              )}
              {answer && <div className="answer-box">{answer}</div>}
              {sources.length > 0 && (
                <div className="sources">
                  <h3>Nguồn tham khảo</h3>
                  {sources.map((source, index) => (
                    <SourceCard
                      key={`${source.clauseId}-${index}`}
                      source={source}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </section>
      </main>

      <footer>Team IBIB · Vietnam AI Innovation Challenge 2026</footer>
    </div>
  )
}

export default App
