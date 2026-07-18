import { useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import {
  fetchGraph,
  type GraphData,
  type GraphLink,
  type GraphNode,
} from '../services/graphApi'

// Màu cạnh theo loại quan hệ (token semantic — App.css)
const LINK_COLORS: Record<string, string> = {
  SUPERSEDES: '#d81e28', // --brand-red
  AMENDS: '#f58220', // --brand-orange
  REFERENCES: '#64748b', // --muted
  GUIDES: '#0ea5e9', // --public
}
const LINK_LABELS: Record<string, string> = {
  SUPERSEDES: 'Thay thế',
  AMENDS: 'Sửa đổi',
  REFERENCES: 'Dẫn chiếu',
  GUIDES: 'Hướng dẫn',
}
const NODE_ACTIVE = '#16a34a' // --active
const NODE_EXPIRED = '#94a3b8' // --superseded

const _now = new Date()
const _pad = (n: number) => String(n).padStart(2, '0')
const TODAY_ISO = `${_now.getFullYear()}-${_pad(_now.getMonth() + 1)}-${_pad(
  _now.getDate(),
)}`

// Node hết hiệu lực: có expiry_date và đã qua hôm nay (so sánh chuỗi ISO là đủ)
const isExpired = (n: GraphNode): boolean =>
  n.expiry_date !== null && n.expiry_date < TODAY_ISO

const linkColor = (type: string): string => LINK_COLORS[type] ?? '#64748b'
const linkLabel = (type: string): string => LINK_LABELS[type] ?? type

type Props = {
  audience: 'employee' | 'customer'
}

function GraphPanel({ audience }: Props) {
  const [data, setData] = useState<GraphData>({ nodes: [], links: [] })
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [selected, setSelected] = useState<GraphNode | null>(null)
  const [width, setWidth] = useState(640)
  const containerRef = useRef<HTMLDivElement>(null)

  // Nạp đồ thị mỗi khi đổi audience (customer chỉ thấy node/edge public)
  useEffect(() => {
    let alive = true
    setIsLoading(true)
    setError('')
    setSelected(null)
    fetchGraph(audience)
      .then((g) => {
        if (alive) setData(g)
      })
      .catch((e: unknown) => {
        if (alive) setError(e instanceof Error ? e.message : 'Lỗi tải đồ thị.')
      })
      .finally(() => {
        if (alive) setIsLoading(false)
      })
    return () => {
      alive = false
    }
  }, [audience])

  // Đo bề rộng container để canvas không tràn layout
  useEffect(() => {
    const measure = () => {
      if (containerRef.current) {
        setWidth(containerRef.current.clientWidth)
      }
    }
    measure()
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [])

  // Bản đồ id → node để tra cứu nhanh cho bảng a11y + chi tiết
  const nodeById = useMemo(() => {
    const m = new Map<string, GraphNode>()
    for (const n of data.nodes) m.set(n.id, n)
    return m
  }, [data.nodes])

  // ForceGraph2D mutate link.source/target thành object → clone cho canvas,
  // giữ nguyên data.links (chuỗi) cho bảng quan hệ.
  const graphData = useMemo(
    () => ({
      nodes: data.nodes.map((n) => ({ ...n })),
      links: data.links.map((l) => ({ ...l })),
    }),
    [data],
  )

  return (
    <section className="graph-panel" aria-label="Đồ thị tri thức">
      <div className="graph-head">
        <h2>Đồ thị tri thức</h2>
        <div className="graph-legend" aria-hidden="true">
          <span>
            <i className="dot" style={{ background: NODE_ACTIVE }} /> Còn hiệu lực
          </span>
          <span>
            <i className="dot" style={{ background: NODE_EXPIRED }} /> Hết hiệu lực
          </span>
          {Object.entries(LINK_LABELS).map(([type, label]) => (
            <span key={type}>
              <i className="bar" style={{ background: LINK_COLORS[type] }} />{' '}
              {label}
            </span>
          ))}
        </div>
      </div>

      {isLoading && (
        <div className="loading-state">
          <span className="spinner" />
          Đang tải đồ thị...
        </div>
      )}
      {error && <p className="error-message">{error}</p>}

      {!isLoading && !error && (
        <>
          <div className="graph-canvas" ref={containerRef}>
            <ForceGraph2D
              graphData={graphData}
              width={width}
              height={380}
              nodeColor={(node) =>
                isExpired(node as GraphNode) ? NODE_EXPIRED : NODE_ACTIVE
              }
              nodeLabel={(node) => (node as GraphNode).id}
              nodeRelSize={6}
              linkColor={(link) => linkColor((link as GraphLink).type)}
              linkWidth={2}
              linkDirectionalArrowLength={4}
              linkDirectionalArrowRelPos={1}
              onNodeClick={(node) => setSelected(node as GraphNode)}
            />
          </div>

          {selected && (
            <div className="node-detail" aria-live="polite">
              <h3>Chi tiết điều khoản</h3>
              <p>
                <span className="cid">{selected.id}</span>
              </p>
              <dl>
                <dt>Đường dẫn</dt>
                <dd>
                  {selected.doc_code} — {selected.path}
                </dd>
                <dt>Chủ đề</dt>
                <dd>{selected.topic}</dd>
                <dt>Phạm vi</dt>
                <dd>{selected.visibility === 'internal' ? 'Nội bộ' : 'Công khai'}</dd>
                <dt>Trạng thái</dt>
                <dd>
                  {isExpired(selected) ? (
                    <span className="badge superseded">Đã hết hiệu lực</span>
                  ) : (
                    <span className="badge active">Còn hiệu lực</span>
                  )}
                </dd>
                <dt>Ngày hết hiệu lực</dt>
                <dd>{selected.expiry_date ? new Intl.DateTimeFormat('vi-VN').format(new Date(`${selected.expiry_date}T00:00:00`)) : 'Chưa xác định'}</dd>
              </dl>
              {/* Hook mở timeline phiên bản — hoàn thiện ở Story 2.2 */}
              <button type="button" className="secondary-button" disabled>
                Xem dòng thời gian (2.2)
              </button>
            </div>
          )}

          {/* Bảng thay thế cho người không thao tác đồ hình (a11y — UX-DR13) */}
          <div className="graph-relations">
            <h3>Danh sách quan hệ</h3>
            {data.links.length === 0 ? (
              <p className="empty-state">Không có quan hệ nào để hiển thị.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Nguồn</th>
                    <th>Quan hệ</th>
                    <th>Đích</th>
                  </tr>
                </thead>
                <tbody>
                  {data.links.map((l, i) => (
                    <tr key={`${l.source}-${l.type}-${l.target}-${i}`}>
                      <td className="cid">{l.source}</td>
                      <td>
                        <span
                          className="rel-tag"
                          style={{ color: linkColor(l.type) }}
                        >
                          {linkLabel(l.type)}
                        </span>
                      </td>
                      <td className="cid">
                        {l.target}
                        {nodeById.get(l.target) &&
                          isExpired(nodeById.get(l.target) as GraphNode) && (
                            <span className="badge superseded">hết hiệu lực</span>
                          )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </section>
  )
}

export default GraphPanel
