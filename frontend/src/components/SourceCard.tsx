import type { SourceItem } from '../services/chatApi'

type Props = {
  source: SourceItem
}

function SourceCard({ source }: Props) {
  const superseded = !source.isCurrent

  return (
    <article className="source-card">
      <span className="cid">{source.clauseId}</span>
      {superseded ? (
        <span className="badge superseded">
          Đã thay thế
          {source.supersededBy ? ` bởi ${source.supersededBy}` : ''}
        </span>
      ) : (
        <span className="badge active">Hiệu lực</span>
      )}
      <div className="doc">{source.name}</div>
      <div className={superseded ? 'desc struck' : 'desc'}>
        {source.description}
      </div>
    </article>
  )
}

export default SourceCard
