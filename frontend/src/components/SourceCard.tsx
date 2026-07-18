import type { SourceItem } from '../services/chatApi'

type Props = {
  source: SourceItem
}

function SourceCard({ source }: Props) {
  const superseded = !source.isCurrent
  const effectiveDate = source.effectiveDate
    ? new Intl.DateTimeFormat('vi-VN').format(new Date(`${source.effectiveDate}T00:00:00`))
    : null

  return (
    <details className="source-card">
      <summary>
        <span><span className="cid">{source.clauseId}</span><strong className="doc">{source.name}</strong></span>
        <span className={`badge ${superseded ? 'superseded' : 'active'}`}>{superseded ? 'Đã thay thế' : 'Hiệu lực'}</span>
      </summary>
      <div className="source-details">
        {superseded && source.supersededBy && <p className="replacement-note">Được thay thế bởi {source.supersededBy}</p>}
        <div className="source-facts">
          {effectiveDate && <span><strong>Ngày hiệu lực</strong>{effectiveDate}</span>}
          {source.metricValue !== null && <span className="metric"><strong>Chỉ số</strong>{source.metricValue.toLocaleString('vi-VN')} {source.metricUnit ?? ''}</span>}
        </div>
        <div className={superseded ? 'source-body struck' : 'source-body'}><strong>Nội dung điều luật</strong><p>{source.body || source.description}</p></div>
      </div>
    </details>
  )
}

export default SourceCard
