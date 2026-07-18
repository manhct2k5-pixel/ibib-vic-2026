import { useRef, useState } from 'react'
import {
  sendChatRequest,
  type ChatResponse,
  type SourceItem,
} from '../services/chatApi'
import SourceCard from './SourceCard'

// Một cột kết quả benchmark (RAG thường HOẶC Compliance Copilot)
type ColumnState = {
  result: ChatResponse | null
  error: string
  loading: boolean
}

const EMPTY: ColumnState = { result: null, error: '', loading: false }

const SAMPLES = [
  'Tỷ lệ an toàn vốn tối thiểu hiện nay là bao nhiêu?',
  'Quy định tại Điều 10 về vốn tự có dẫn chiếu điều nào?',
]

function BenchmarkPanel() {
  const [question, setQuestion] = useState('')
  const [baseline, setBaseline] = useState<ColumnState>(EMPTY)
  const [system, setSystem] = useState<ColumnState>(EMPTY)
  // Chỉ nhận kết quả của lần "So sánh" mới nhất (chống race khi bấm nhanh)
  const runId = useRef(0)

  const run = async (q: string) => {
    const clean = q.trim()
    if (!clean) return
    const myId = ++runId.current
    setBaseline({ ...EMPTY, loading: true })
    setSystem({ ...EMPTY, loading: true })

    // Gọi song song: mỗi cột độc lập, lỗi 1 cột không chặn cột kia
    void sendChatRequest(clean, { mode: 'baseline' })
      .then((r) => {
        if (myId === runId.current)
          setBaseline({ result: r, error: '', loading: false })
      })
      .catch((e: unknown) => {
        if (myId === runId.current)
          setBaseline({
            result: null,
            error: e instanceof Error ? e.message : 'Lỗi.',
            loading: false,
          })
      })
    void sendChatRequest(clean, { mode: 'system' })
      .then((r) => {
        if (myId === runId.current)
          setSystem({ result: r, error: '', loading: false })
      })
      .catch((e: unknown) => {
        if (myId === runId.current)
          setSystem({
            result: null,
            error: e instanceof Error ? e.message : 'Lỗi.',
            loading: false,
          })
      })
  }

  // Chỉ so khác biệt khi CẢ HAI cột có kết quả (tránh tô nhầm khi 1 cột lỗi)
  const bothLoaded = baseline.result !== null && system.result !== null
  const baseById = new Map(
    (baseline.result?.sources ?? []).map((s) => [s.clauseId, s]),
  )
  const sysById = new Map(
    (system.result?.sources ?? []).map((s) => [s.clauseId, s]),
  )

  // Nguồn "khác biệt": chỉ có ở cột này, HOẶC cùng clause_id nhưng khác trạng
  // thái hiệu lực (baseline coi còn hiệu lực, system đánh dấu đã thay thế —
  // đây chính là điểm cốt lõi cần làm nổi bật). Chỉ tính khi cả 2 cột có kết quả.
  const isDiff = (s: SourceItem, other: Map<string, SourceItem>): boolean => {
    if (!bothLoaded) return false
    const match = other.get(s.clauseId)
    return match === undefined || match.isCurrent !== s.isCurrent
  }

  const renderColumn = (
    title: string,
    subtitle: string,
    col: ColumnState,
    otherById: Map<string, SourceItem>,
    variant: 'baseline' | 'system',
  ) => (
    <div className={`bench-col bench-${variant}`}>
      <header className="bench-col-head">
        <h3>{title}</h3>
        <small>{subtitle}</small>
      </header>
      {col.loading && (
        <div className="loading-state">
          <span className="spinner" />
          Đang tra cứu...
        </div>
      )}
      {col.error && <p className="error-message">{col.error}</p>}
      {col.result && (
        <>
          {variant === 'system' && col.result.conflictWarning?.trim() && (
            <div className="conflict-banner">
              <span aria-hidden="true">⚠</span>
              <span>{col.result.conflictWarning}</span>
            </div>
          )}
          <div className="answer-box">{col.result.answer}</div>
          {col.result.sources.length > 0 && (
            <div className="sources">
              <h4>Nguồn ({col.result.sources.length})</h4>
              {col.result.sources.map((s: SourceItem, i) => (
                <div
                  key={`${s.clauseId}-${i}`}
                  className={isDiff(s, otherById) ? 'bench-diff' : ''}
                >
                  <SourceCard source={s} />
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )

  return (
    <section className="benchmark-panel" aria-label="So sánh benchmark">
      <div className="bench-head">
        <h2>Benchmark — RAG thường vs Compliance Copilot</h2>
        <p className="bench-note">
          Cùng một câu hỏi, hai hệ thống trả lời cạnh nhau. Nguồn được tô là chỗ
          khác biệt (chỉ xuất hiện ở một bên).
        </p>
      </div>

      <form
        className="bench-form"
        onSubmit={(e) => {
          e.preventDefault()
          void run(question)
        }}
      >
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Nhập câu hỏi để so sánh..."
          aria-label="Câu hỏi benchmark"
        />
        <button type="submit" className="primary-button">
          So sánh
        </button>
      </form>

      <div className="bench-samples">
        {SAMPLES.map((s) => (
          <button
            key={s}
            type="button"
            className="sample-chip"
            onClick={() => {
              setQuestion(s)
              void run(s)
            }}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="bench-grid">
        {renderColumn(
          'RAG thường',
          'Không lọc hiệu lực · không dẫn chiếu',
          baseline,
          sysById,
          'baseline',
        )}
        {renderColumn(
          'Compliance Copilot',
          'Lọc hiệu lực · dẫn chiếu · cảnh báo xung đột',
          system,
          baseById,
          'system',
        )}
      </div>
    </section>
  )
}

export default BenchmarkPanel
