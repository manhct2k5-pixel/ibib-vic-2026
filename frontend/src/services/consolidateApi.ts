// Gọi GET /api/consolidate — văn bản hợp nhất của một văn bản gốc (FR-17).

export type ConsolidatedSection = {
  path: string
  clauseId: string
  text: string
  status: 'active' | 'amended' | 'superseded' | 'expired'
  amendedBy: string | null
  amendNote: string | null
  amendedByText: string | null
  amendedByPath: string | null
  effectiveFrom: string
  fromSession: boolean
}

export type ConsolidatedDoc = {
  docCode: string
  title: string
  asOf: string
  sections: ConsolidatedSection[]
}

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
).replace(/\/$/, '')

export type ConsolidateOptions = {
  asOf?: string
  audience?: 'employee' | 'customer'
  sessionId?: string
}

export const fetchConsolidatedDoc = async (
  docCode: string,
  options: ConsolidateOptions = {},
): Promise<ConsolidatedDoc> => {
  const params = new URLSearchParams({ docCode })
  if (options.asOf) params.set('asOf', options.asOf)
  if (options.audience) params.set('audience', options.audience)
  if (options.sessionId) params.set('sessionId', options.sessionId)

  const response = await fetch(`${API_BASE_URL}/api/consolidate?${params}`)
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

  return payload as unknown as ConsolidatedDoc
}
