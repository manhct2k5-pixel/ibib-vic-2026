// Service gọi GET /api/graph (Story 2.1, FR-12).
// Backend trả {nodes, edges} với edge dùng khóa from/to; react-force-graph-2d
// lại cần links[] với source/target → service này map sẵn để component chỉ việc render.

export type GraphNode = {
  id: string
  doc_code: string
  path: string
  topic: string
  visibility: string
  expiry_date: string | null
}

// Khóa của react-force-graph-2d: link cần source/target (không phải from/to)
export type GraphLink = {
  source: string
  target: string
  type: string
}

export type GraphData = {
  nodes: GraphNode[]
  links: GraphLink[]
}

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
).replace(/\/$/, '')

const REQUEST_TIMEOUT_MS = 15_000

const parseNodes = (value: unknown): GraphNode[] => {
  if (!Array.isArray(value)) return []
  return value.flatMap((item) => {
    if (typeof item !== 'object' || item === null) return []
    const n = item as Record<string, unknown>
    if (typeof n.id !== 'string') return []
    return [
      {
        id: n.id,
        doc_code: typeof n.doc_code === 'string' ? n.doc_code : '',
        path: typeof n.path === 'string' ? n.path : '',
        topic: typeof n.topic === 'string' ? n.topic : '',
        visibility: typeof n.visibility === 'string' ? n.visibility : 'public',
        expiry_date: typeof n.expiry_date === 'string' ? n.expiry_date : null,
      },
    ]
  })
}

// edges[].from → source, to → target (đổi khóa cho react-force-graph-2d)
const parseLinks = (value: unknown): GraphLink[] => {
  if (!Array.isArray(value)) return []
  return value.flatMap((item) => {
    if (typeof item !== 'object' || item === null) return []
    const e = item as Record<string, unknown>
    if (typeof e.from !== 'string' || typeof e.to !== 'string') return []
    return [
      {
        source: e.from,
        target: e.to,
        type: typeof e.type === 'string' ? e.type : 'REFERENCES',
      },
    ]
  })
}

export const fetchGraph = async (
  audience: 'employee' | 'customer' = 'employee',
): Promise<GraphData> => {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(
    () => controller.abort(),
    REQUEST_TIMEOUT_MS,
  )

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/graph?audience=${encodeURIComponent(audience)}`,
      { signal: controller.signal },
    )

    if (!response.ok) {
      throw new Error(`Backend trả về lỗi ${response.status} khi tải đồ thị.`)
    }

    const raw: unknown = await response.json()
    const payload =
      typeof raw === 'object' && raw !== null
        ? (raw as Record<string, unknown>)
        : {}

    return {
      nodes: parseNodes(payload.nodes),
      links: parseLinks(payload.edges),
    }
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('Tải đồ thị quá 15 giây. Vui lòng thử lại.')
    }
    if (error instanceof TypeError) {
      throw new Error(
        'Không thể kết nối tới backend để tải đồ thị. Kiểm tra backend và CORS.',
      )
    }
    if (error instanceof Error) throw error
    throw new Error('Đã xảy ra lỗi không xác định khi tải đồ thị.')
  } finally {
    window.clearTimeout(timeoutId)
  }
}
