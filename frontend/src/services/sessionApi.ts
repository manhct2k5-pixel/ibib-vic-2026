// Upload tài liệu đính kèm theo phiên (ephemeral, AD-13). KHÔNG persist vào DB.

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
).replace(/\/$/, '')

export type SessionUploadResult = {
  sessionId: string
  docCode: string
  added: number
  sessionClauses: number
  title?: string
  docType?: string
  relations?: number
  effective_date?: string
  chars?: number
}

export type AnalysisNode = {
  id: string
  label: string
  title: string
  docType: string
  issuer: string
  effectiveDate: string | null
  numClauses: number
  inSession: boolean
  role: string
}

export type AnalysisEdge = {
  from: string
  to: string
  type: string
  fromArticle: string | null
  toArticle: string | null
  note: string | null
}

export type ReadingItem = {
  docCode: string
  title: string
  role: string
  roleLabel: string
  inSession: boolean
}

export type SessionAnalysis = {
  sessionId: string
  documents: AnalysisNode[]
  graph: { nodes: AnalysisNode[]; edges: AnalysisEdge[] }
  readingOrder: ReadingItem[]
  guide: string
}

export const removeSessionDoc = async (
  sessionId: string,
  docCode: string,
): Promise<SessionAnalysis> => {
  const response = await fetch(
    `${API_BASE_URL}/api/session/doc?sessionId=${encodeURIComponent(sessionId)}&docCode=${encodeURIComponent(docCode)}`,
    { method: 'DELETE' },
  )
  const text = await response.text()
  const data: unknown = text ? JSON.parse(text) : {}
  const payload =
    typeof data === 'object' && data !== null
      ? (data as Record<string, unknown>)
      : {}
  if (!response.ok) {
    throw new Error(
      typeof payload.detail === 'string'
        ? payload.detail
        : `Backend trả về lỗi ${response.status}.`,
    )
  }
  return payload.analysis as SessionAnalysis
}

// Chạy phân tích LLM (trích quan hệ) — gọi KHI GỬI câu hỏi.
export const analyzeSession = async (
  sessionId: string,
): Promise<SessionAnalysis> => {
  const response = await fetch(
    `${API_BASE_URL}/api/session/analyze?sessionId=${encodeURIComponent(sessionId)}`,
    { method: 'POST' },
  )
  const text = await response.text()
  const data: unknown = text ? JSON.parse(text) : {}
  const payload =
    typeof data === 'object' && data !== null
      ? (data as Record<string, unknown>)
      : {}
  if (!response.ok) {
    throw new Error(
      typeof payload.detail === 'string'
        ? payload.detail
        : `Backend trả về lỗi ${response.status}.`,
    )
  }
  return payload as unknown as SessionAnalysis
}

export type SessionConsolidated = {
  sessionId: string
  docCode: string
  title: string
  asOf: string
  mergedFrom: string[]
  docLevelNotes: { from: string; type: string; note: string | null }[]
  sections: {
    path: string
    clauseId: string
    text: string
    consolidatedText?: string | null
    changeSummary?: string | null
    status: 'active' | 'amended' | 'superseded' | 'expired'
    amendedBy: string | null
    amendNote: string | null
    amendedByText: string | null
    amendedByPath: string | null
    effectiveFrom: string
    fromSession: boolean
  }[]
}

// MỘT văn bản hợp nhất tổng hợp quanh văn bản nền của phiên.
export const getSessionConsolidated = async (
  sessionId: string,
  asOf?: string,
): Promise<SessionConsolidated> => {
  const params = new URLSearchParams({ sessionId })
  if (asOf) params.set('asOf', asOf)
  const response = await fetch(`${API_BASE_URL}/api/session/consolidated?${params}`)
  const text = await response.text()
  const data: unknown = text ? JSON.parse(text) : {}
  const payload =
    typeof data === 'object' && data !== null
      ? (data as Record<string, unknown>)
      : {}
  if (!response.ok) {
    throw new Error(
      typeof payload.detail === 'string'
        ? payload.detail
        : `Backend trả về lỗi ${response.status}.`,
    )
  }
  return payload as unknown as SessionConsolidated
}

export const getSessionAnalysis = async (
  sessionId: string,
): Promise<SessionAnalysis> => {
  const response = await fetch(
    `${API_BASE_URL}/api/session/analysis?sessionId=${encodeURIComponent(sessionId)}`,
  )
  const text = await response.text()
  const data: unknown = text ? JSON.parse(text) : {}
  const payload =
    typeof data === 'object' && data !== null
      ? (data as Record<string, unknown>)
      : {}
  if (!response.ok) {
    throw new Error(
      typeof payload.detail === 'string'
        ? payload.detail
        : `Backend trả về lỗi ${response.status}.`,
    )
  }
  return payload as unknown as SessionAnalysis
}

// PDF số → backend cắt theo Điều + LLM trích hiệu lực → clause phiên.
export const uploadSessionPdf = async (
  sessionId: string,
  file: File,
  docCode = '',
  signal?: AbortSignal,
): Promise<SessionUploadResult> => {
  const form = new FormData()
  form.append('sessionId', sessionId)
  form.append('file', file)
  if (docCode) form.append('docCode', docCode)

  const response = await fetch(`${API_BASE_URL}/api/session/upload-pdf`, {
    method: 'POST',
    body: form,
    signal,
  })
  const text = await response.text()
  let data: unknown = {}
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      throw new Error('Backend trả về dữ liệu không đúng định dạng JSON.')
    }
  }
  const payload =
    typeof data === 'object' && data !== null
      ? (data as Record<string, unknown>)
      : {}

  if (!response.ok) {
    const msg =
      typeof payload.detail === 'string'
        ? payload.detail
        : `Backend trả về lỗi ${response.status}.`
    throw new Error(msg)
  }

  return payload as unknown as SessionUploadResult
}
