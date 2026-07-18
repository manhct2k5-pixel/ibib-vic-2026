import { useEffect, useState } from 'react'
import {
  fetchConsolidatedDoc,
  type ConsolidatedDoc,
} from '../services/consolidateApi'

type Props = {
  docCode: string
  asOf?: string
  audience?: 'employee' | 'customer'
  sessionId?: string
  onClose?: () => void
  data?: ConsolidatedDoc // nếu có: dùng trực tiếp, KHÔNG fetch
  label?: string // tiêu đề thay cho "Văn bản hợp nhất: {docCode}"
  mergedFrom?: string[] // các văn bản đã gộp vào bản nền
}

const STATUS_LABEL: Record<string, string> = {
  active: 'Đang hiệu lực',
  amended: 'Đã sửa đổi',
  superseded: 'Đã thay thế',
  expired: 'Hết hiệu lực',
}

// Diff mức từ (LCS): đánh dấu các từ THÊM/ĐỔI ở bản hợp nhất so với bản gốc.
const DiffText = ({ original, merged }: { original: string; merged: string }) => {
  const a = original.split(/(\s+)/)
  const b = merged.split(/(\s+)/)
  const m = a.length
  const n = b.length
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0))
  for (let i = m - 1; i >= 0; i--)
    for (let j = n - 1; j >= 0; j--)
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1])
  const parts: { text: string; added: boolean }[] = []
  let i = 0
  let j = 0
  while (j < n) {
    if (i < m && a[i] === b[j]) { parts.push({ text: b[j], added: false }); i++; j++ }
    else if (i < m && dp[i + 1][j] >= dp[i][j + 1]) { i++ }
    else { parts.push({ text: b[j], added: true }); j++ }
  }
  return (
    <>
      {parts.map((p, idx) => (p.added ? <mark key={idx}>{p.text}</mark> : <span key={idx}>{p.text}</span>))}
    </>
  )
}

// Văn bản hợp nhất inline trong chat (FR-17, FR-19): 1 văn bản gốc + mọi sửa đổi.
function ConsolidatedDocView({ docCode, asOf, audience, sessionId, onClose, data, label, mergedFrom }: Props) {
  const [doc, setDoc] = useState<ConsolidatedDoc | null>(data ?? null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(!data)

  useEffect(() => {
    if (data) { setDoc(data); setLoading(false); setError(''); return }
    let alive = true
    setLoading(true)
    setError('')
    fetchConsolidatedDoc(docCode, { asOf, audience, sessionId })
      .then((d) => {
        if (alive) setDoc(d)
      })
      .catch((e: unknown) => {
        if (alive) setError(e instanceof Error ? e.message : 'Lỗi tải văn bản hợp nhất.')
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [docCode, asOf, audience, sessionId, data])

  return (
    <section className="consolidated-doc" aria-label={`Văn bản hợp nhất ${docCode}`}>
      <header className="consolidated-head">
        <div>
          <strong>{label ?? `Văn bản hợp nhất: ${docCode}`}</strong>
          {doc && <span className="consolidated-sub">{doc.title} · tại ngày {doc.asOf}{mergedFrom && mergedFrom.length > 0 ? ` · đã gộp: ${mergedFrom.join(', ')}` : ''}</span>}
        </div>
        {onClose && (
          <button type="button" className="consolidated-close" onClick={onClose} aria-label="Đóng">
            ×
          </button>
        )}
      </header>

      {loading && <p className="consolidated-status">Đang dựng văn bản hợp nhất…</p>}
      {error && <p className="consolidated-status error">{error}</p>}

      {doc &&
        doc.sections.map((s) => (
          <article key={s.clauseId} className={`consolidated-section status-${s.status}`}>
            <div className="section-head">
              <span className="section-path">{s.path}</span>
              <span className={`section-badge ${s.status}`}>{STATUS_LABEL[s.status] ?? s.status}</span>
              {s.consolidatedText && <span className="section-badge merged">Đã hợp nhất</span>}
              {s.fromSession && <span className="section-badge session">Tài liệu đính kèm</span>}
            </div>

            {s.consolidatedText ? (
              <>
                {/* Bản hợp nhất (đã áp sửa đổi) — nội dung đọc chính, highlight phần mới */}
                <p className="section-text">
                  <DiffText original={s.text} merged={s.consolidatedText} />
                </p>
                {s.changeSummary && <div className="change-summary">✏️ {s.changeSummary}</div>}
                <details className="compare">
                  <summary>Đối chiếu bản gốc ↔ đã sửa đổi</summary>
                  <div className="compare-old">
                    <strong>Bản gốc [{s.clauseId}]</strong>
                    <p className="section-text struck">{s.text}</p>
                  </div>
                  {s.amendedBy && (
                    <div className="compare-src">
                      <strong>
                        {s.status === 'superseded' ? 'Thay thế bởi' : 'Sửa đổi bởi'} {s.amendedBy}
                        {s.amendedByPath ? ` (${s.amendedByPath})` : ''}
                      </strong>
                      {s.amendedByText && <p className="amend-text">{s.amendedByText}</p>}
                    </div>
                  )}
                </details>
              </>
            ) : (
              <>
                <p className={s.status === 'superseded' || s.status === 'expired' ? 'section-text struck' : 'section-text'}>
                  {s.text}
                </p>
                {s.amendedBy && (
                  <div className="section-amend">
                    <span className="amend-label">
                      {s.status === 'superseded' ? 'Được thay thế bởi' : 'Được sửa đổi bởi'} {s.amendedBy}
                      {s.amendedByPath ? ` (${s.amendedByPath})` : ''}
                    </span>
                    {s.amendNote && <span className="amend-note">{s.amendNote}</span>}
                    {s.amendedByText && <p className="amend-text">{s.amendedByText}</p>}
                  </div>
                )}
              </>
            )}
          </article>
        ))}
    </section>
  )
}

export default ConsolidatedDocView
