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
}

const STATUS_LABEL: Record<string, string> = {
  active: 'Đang hiệu lực',
  amended: 'Đã sửa đổi',
  superseded: 'Đã thay thế',
  expired: 'Hết hiệu lực',
}

// Văn bản hợp nhất inline trong chat (FR-17, FR-19): 1 văn bản gốc + mọi sửa đổi.
function ConsolidatedDocView({ docCode, asOf, audience, sessionId, onClose }: Props) {
  const [doc, setDoc] = useState<ConsolidatedDoc | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
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
  }, [docCode, asOf, audience, sessionId])

  return (
    <section className="consolidated-doc" aria-label={`Văn bản hợp nhất ${docCode}`}>
      <header className="consolidated-head">
        <div>
          <strong>Văn bản hợp nhất: {docCode}</strong>
          {doc && <span className="consolidated-sub">{doc.title} · tại ngày {doc.asOf}</span>}
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
              {s.fromSession && <span className="section-badge session">Tài liệu đính kèm</span>}
            </div>
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
          </article>
        ))}
    </section>
  )
}

export default ConsolidatedDocView
