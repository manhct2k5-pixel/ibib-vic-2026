import { useMemo } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import type { SessionAnalysis } from '../services/sessionApi'

type Props = {
  analysis: SessionAnalysis
  onClose?: () => void
  onConsolidateMerged?: () => void
  onRemove?: (docCode: string) => void
}

const ROLE_COLOR: Record<string, string> = {
  consolidated: '#f58220', // cam — văn bản hợp nhất
  current: '#16a34a', // xanh lá — hiện hành
  amended: '#0ea5e9', // xanh dương — bị sửa đổi
  historical: '#94a3b8', // xám — lịch sử
  external: '#cbd5e1', // xám nhạt — tham chiếu ngoài
}
const EDGE_COLOR: Record<string, string> = {
  CONSOLIDATES: '#f58220',
  SUPERSEDES: '#d81e28',
  AMENDS: '#f59e0b',
  REFERENCES: '#94a3b8',
  GUIDES: '#0ea5e9',
}
const EDGE_LABEL: Record<string, string> = {
  CONSOLIDATES: 'Hợp nhất',
  SUPERSEDES: 'Thay thế',
  AMENDS: 'Sửa đổi',
  REFERENCES: 'Căn cứ',
  GUIDES: 'Hướng dẫn',
}

const GuideLine = ({ text }: { text: string }) => (
  <>
    {text.split(/(\*\*.*?\*\*)/g).map((part, i) =>
      part.startsWith('**') && part.endsWith('**') ? (
        <strong key={i}>{part.slice(2, -2)}</strong>
      ) : (
        <span key={i}>{part}</span>
      ),
    )}
  </>
)

function SessionAnalysisView({ analysis, onClose, onConsolidateMerged, onRemove }: Props) {
  const graphData = useMemo(
    () => ({
      nodes: analysis.graph.nodes.map((n) => ({ ...n })),
      links: analysis.graph.edges.map((e) => ({
        source: e.from,
        target: e.to,
        type: e.type,
        note: e.note,
      })),
    }),
    [analysis],
  )

  return (
    <section className="analysis-view" aria-label="Phân tích bộ tài liệu">
      <header className="analysis-head">
        <strong>Bản đồ quan hệ &amp; hướng dẫn đọc ({analysis.documents.length} tài liệu)</strong>
        {onClose && (
          <button type="button" className="analysis-close" onClick={onClose} aria-label="Đóng">
            ×
          </button>
        )}
      </header>

      <div className="analysis-docs">
        {analysis.documents.map((d) => (
          <span key={d.id} className={`doc-pill role-${d.role}`}>
            <b>{d.id}</b>
            <span className="doc-pill-meta">{d.docType || 'Tài liệu'} · {d.numClauses} điều</span>
            {onRemove && (
              <button type="button" className="doc-remove" title={`Xoá ${d.id}`} aria-label={`Xoá ${d.id}`} onClick={() => onRemove(d.id)}>×</button>
            )}
          </span>
        ))}
      </div>

      <div className="analysis-guide">
        {analysis.guide.split('\n').map((line, i) => {
          const t = line.trim()
          if (!t) return null
          if (t.startsWith('- '))
            return (
              <div className="guide-bullet" key={i}>
                <span>•</span>
                <p><GuideLine text={t.slice(2)} /></p>
              </div>
            )
          return <p key={i}><GuideLine text={t} /></p>
        })}
      </div>

      {onConsolidateMerged && (
        <button type="button" className="merged-consolidate-btn" onClick={onConsolidateMerged}>
          📄 Xem văn bản hợp nhất tổng hợp
        </button>
      )}

      {graphData.nodes.length > 0 && (
        <div className="analysis-graph">
          <ForceGraph2D
            graphData={graphData}
            width={520}
            height={300}
            cooldownTicks={80}
            nodeRelSize={5}
            linkColor={(l: { type?: string }) => EDGE_COLOR[l.type ?? ''] ?? '#94a3b8'}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={1}
            linkWidth={1.5}
            nodeCanvasObject={(node: Record<string, unknown>, ctx: CanvasRenderingContext2D, scale: number) => {
              const n = node as { id: string; label: string; role: string; inSession: boolean; x: number; y: number }
              const r = n.inSession ? 6 : 4
              ctx.beginPath()
              ctx.arc(n.x, n.y, r, 0, 2 * Math.PI)
              ctx.fillStyle = ROLE_COLOR[n.role] ?? '#cbd5e1'
              ctx.fill()
              if (n.inSession) {
                ctx.lineWidth = 1.5 / scale
                ctx.strokeStyle = '#1e293b'
                ctx.stroke()
              }
              const fs = Math.max(9 / scale, 3)
              ctx.font = `${fs}px 'Be Vietnam Pro', sans-serif`
              ctx.fillStyle = '#1e293b'
              ctx.textAlign = 'center'
              ctx.fillText(n.label, n.x, n.y + r + fs)
            }}
          />
          <div className="analysis-legend">
            {Object.entries(EDGE_LABEL).map(([k, v]) => (
              <span key={k} className="legend-item">
                <i style={{ background: EDGE_COLOR[k] }} />{v}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="analysis-reading">
        <h4>Thứ tự đọc đề xuất</h4>
        <ol>
          {analysis.readingOrder
            .filter((r) => r.inSession)
            .map((r) => (
              <li key={r.docCode} className={`reading-item role-${r.role}`}>
                <div>
                  <strong>{r.docCode}</strong>
                  <span className="reading-role">{r.roleLabel}</span>
                  {r.title && <span className="reading-title">{r.title}</span>}
                </div>
              </li>
            ))}
        </ol>
      </div>
    </section>
  )
}

export default SessionAnalysisView
