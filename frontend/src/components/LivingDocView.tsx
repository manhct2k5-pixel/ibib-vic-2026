import { useState } from 'react'
import type { LivingDoc } from '../services/chatApi'

type Props = { doc: LivingDoc }

// "Văn bản hợp nhất SỐNG": bản còn hiệu lực đã dựng lại cho đúng câu hỏi, kèm dấu
// vết provenance ngay tại chỗ (khoản nào bị thay thế/ai bãi bỏ). Focus+context:
// mặc định chỉ hiện điều trực tiếp + đang hiệu lực; phần liên quan gói lại, bấm bung.
function LivingDocView({ doc }: Props) {
  const [expanded, setExpanded] = useState(false)
  if (!doc || doc.clauses.length === 0) return null
  return (
    <section className="living-doc" aria-label="Văn bản hợp nhất còn hiệu lực">
      <div className="living-head">
        <strong>📋 Điều khoản liên quan còn hiệu lực</strong>
      </div>

      {doc.clauses.map((c) => (
        <article key={c.clauseId} className="living-clause">
          <div className="living-clause-head">
            <span className="living-doc">{c.docCode}</span>
            <span className="living-path">{c.path}</span>
            <span className="living-src">hiệu lực {c.effectiveDate}</span>
            <span className="living-badge">Đang hiệu lực</span>
          </div>
          <p className="living-text">{c.text}</p>

          {c.provenance.supersedes && (
            <div className="living-super">
              <span className="living-super-label">
                ⤷ Thay thế bản cũ <b>{c.provenance.supersedes.clauseId}</b>
                {c.provenance.supersedes.note ? ` — ${c.provenance.supersedes.note}` : ''}
              </span>
              <p className="living-old">
                <span className="struck">
                  {c.provenance.supersedes.text.slice(0, 140)}
                  {c.provenance.supersedes.text.length > 140 ? '…' : ''}
                </span>
              </p>
            </div>
          )}
          {c.provenance.amendedBy.length > 0 && (
            <div className="living-amend">
              ✏️ Được sửa đổi bởi {c.provenance.amendedBy.map((a) => a.clauseId).join(', ')}
            </div>
          )}
        </article>
      ))}

      {expanded && doc.related.length > 0 && (
        <div className="living-related">
          {doc.related.map((r) => (
            <div key={r.clauseId} className={`related-item ${r.isActive ? '' : 'expired'}`}>
              <span className={`related-tag ${r.relType}`}>{r.relLabel}</span>
              <span className="related-cid">[{r.clauseId}]</span>
              {!r.isActive && <span className="related-exp">hết hiệu lực</span>}
              <p className="related-text">{r.text}{r.text.length >= 220 ? '…' : ''}</p>
            </div>
          ))}
        </div>
      )}

      <div className="living-foot">
        Dựng từ <b>{doc.builtFrom.length}</b> văn bản ({doc.builtFrom.join(', ')})
        {doc.hiddenCount > 0 && (
          <>
            {' · '}
            <button type="button" className="living-expand" onClick={() => setExpanded((v) => !v)}>
              {expanded ? '▾ Ẩn' : `▸ +${doc.hiddenCount}`} văn bản liên quan
            </button>
          </>
        )}
      </div>
    </section>
  )
}

export default LivingDocView
