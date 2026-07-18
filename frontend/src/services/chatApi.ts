export type SourceItem = {
  clauseId: string
  name: string
  description: string
  body: string
  effectiveDate: string | null
  metricValue: number | null
  metricUnit: string | null
  isCurrent: boolean
  supersededBy: string | null
}

export type ChatResponse = {
  answer: string
  sources: SourceItem[]
  conflictWarning?: string | null
  intent?: 'content' | 'version' | 'change' | string
  requestId?: string
  latencyMs?: number
}

export type ChatOptions = {
  asOf?: string
  mode?: 'system' | 'baseline'
  audience?: 'manager' | 'employee' | 'customer'
  sessionId?: string
}

export type BackendHealth = {
  status: string
  clauses: number
}

const API_MODE = import.meta.env.VITE_API_MODE ?? 'mock'

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
).replace(/\/$/, '')

const REQUEST_TIMEOUT_MS = 15_000

export const checkBackendHealth = async (): Promise<BackendHealth> => {
  if (API_MODE === 'mock') return { status: 'mock', clauses: 1 }
  const response = await fetch(`${API_BASE_URL}/health`)
  if (!response.ok) throw new Error(`Health check lỗi ${response.status}.`)
  const raw: unknown = await response.json()
  const data = typeof raw === 'object' && raw !== null ? raw as Record<string, unknown> : {}
  return {
    status: typeof data.status === 'string' ? data.status : 'unknown',
    clauses: typeof data.clauses === 'number' ? data.clauses : 0,
  }
}

const createMockResponse = async (
  question: string,
  options: ChatOptions,
): Promise<ChatResponse> => {
  await new Promise((resolve) => window.setTimeout(resolve, 800))

  const managerAnswer = `## Đối chiếu quy định
### Tầng 1 — Luật ngoài (NHNN)
- Văn bản: Thông tư 22/2019/TT-NHNN
- Địa chỉ: Điều 1 — Thông tư 22/2019/TT-NHNN
- Nội dung: Tổ chức tín dụng phải duy trì tỷ lệ an toàn vốn tối thiểu 9%.

### Tầng 2 — Quy chế nội bộ
- Văn bản: Quy định nội bộ về tỷ lệ an toàn vốn
- Địa chỉ: Điều 2 — Quy định nội bộ
- Nội dung: Ngưỡng kiểm soát nội bộ được áp dụng theo quy chế hiện hành.

## Timeline hiệu lực
[Thông tư 22/2019 (Hiệu lực gốc)] → [Văn bản sửa đổi hiện hành]

## Phân tích tác động
### Operational Impact — Đối với ngân hàng
Cần rà soát ngưỡng kiểm soát và thẩm quyền phê duyệt trong quy trình nội bộ.`

  const employeeAnswer = `## Ý định người dùng
${question}

## Thực thể và dữ kiện chính
- Thông tư 22/2019/TT-NHNN
- Tỷ lệ an toàn vốn tối thiểu: 9%
- Điều khoản: TT22/Điều 1

## Kết luận nghiệp vụ
Tổ chức tín dụng phải duy trì tỷ lệ an toàn vốn tối thiểu 9% [TT22/Điều 1].

## Phân tích tác động
### Obligation Impact — Đối với khách hàng
Khách hàng cần cung cấp đầy đủ chứng từ theo yêu cầu thẩm định của ngân hàng.

## Timeline hiệu lực
[Thông tư 22/2019 (Hiệu lực gốc)] → [Văn bản sửa đổi hiện hành]`

  return {
    answer: options.audience === 'manager' ? managerAnswer : employeeAnswer,
    sources: [
      {
        clauseId: 'TT22/Điều 1',
        name: 'Thông tư 22/2019/TT-NHNN',
        description:
          'Tỷ lệ an toàn vốn tối thiểu 9% (dữ liệu mô phỏng cho chế độ mock).',
        body: 'Tổ chức tín dụng phải duy trì tỷ lệ an toàn vốn tối thiểu 9%.',
        effectiveDate: '2019-01-01',
        metricValue: 9,
        metricUnit: '%',
        isCurrent: true,
        supersededBy: null,
      },
    ],
    conflictWarning: null,
    requestId: 'mock-request',
    latencyMs: 800,
  }
}

const parseSources = (value: unknown): SourceItem[] => {
  if (!Array.isArray(value)) {
    return []
  }

  return value.flatMap((item) => {
    if (typeof item !== 'object' || item === null) {
      return []
    }

    const source = item as Record<string, unknown>

    if (typeof source.name !== 'string') {
      return []
    }

    return [
      {
        clauseId:
          typeof source.clause_id === 'string' ? source.clause_id : '',
        name: source.name,
        description:
          typeof source.description === 'string'
            ? source.description
            : '',
        body:
          typeof source.body === 'string'
            ? source.body
            : typeof source.description === 'string'
              ? source.description
              : '',
        effectiveDate:
          typeof source.effective_date === 'string'
            ? source.effective_date
            : typeof source.effectiveDate === 'string'
              ? source.effectiveDate
              : null,
        metricValue:
          typeof source.metric_value === 'number'
            ? source.metric_value
            : typeof source.metricValue === 'number'
              ? source.metricValue
              : null,
        metricUnit:
          typeof source.metric_unit === 'string'
            ? source.metric_unit
            : typeof source.metricUnit === 'string'
              ? source.metricUnit
              : null,
        isCurrent:
          typeof source.is_current === 'boolean' ? source.is_current : true,
        supersededBy:
          typeof source.superseded_by === 'string'
            ? source.superseded_by
            : null,
      },
    ]
  })
}

export const sendChatRequest = async (
  question: string,
  options: ChatOptions = {},
): Promise<ChatResponse> => {
  if (API_MODE === 'mock') {
    return createMockResponse(question, options)
  }

  const controller = new AbortController()

  const timeoutId = window.setTimeout(() => {
    controller.abort()
  }, REQUEST_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question,
        ...(options.asOf ? { asOf: options.asOf } : {}),
        ...(options.mode ? { mode: options.mode } : {}),
        ...(options.audience ? { audience: options.audience } : {}),
        ...(options.sessionId ? { sessionId: options.sessionId } : {}),
      }),
      signal: controller.signal,
    })

    const responseText = await response.text()

    let rawData: unknown = {}

    if (responseText) {
      try {
        rawData = JSON.parse(responseText)
      } catch {
        throw new Error('Backend trả về dữ liệu không đúng định dạng JSON.')
      }
    }

    const payload =
      typeof rawData === 'object' && rawData !== null
        ? (rawData as Record<string, unknown>)
        : {}

    if (!response.ok) {
      const backendMessage =
        typeof payload.detail === 'string'
          ? payload.detail
          : typeof payload.message === 'string'
            ? payload.message
            : `Backend trả về lỗi ${response.status}.`

      throw new Error(backendMessage)
    }

    if (typeof payload.answer !== 'string') {
      throw new Error('Backend chưa trả về trường answer hợp lệ.')
    }

    return {
      answer: payload.answer,
      sources: parseSources(payload.sources),
      intent: typeof payload.intent === 'string' ? payload.intent : undefined,
      conflictWarning:
        typeof payload.conflictWarning === 'string'
          ? payload.conflictWarning
          : typeof payload.conflict_warning === 'string'
            ? payload.conflict_warning
          : null,
      requestId:
        typeof payload.requestId === 'string'
          ? payload.requestId
          : typeof payload.request_id === 'string'
            ? payload.request_id
          : undefined,
      latencyMs:
        typeof payload.latencyMs === 'number'
          ? payload.latencyMs
          : typeof payload.latency_ms === 'number'
            ? payload.latency_ms
          : undefined,
    }
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error(
        'Backend phản hồi quá 15 giây. Vui lòng thử lại hoặc chuyển sang phương án dự phòng.',
      )
    }

    if (error instanceof TypeError) {
      throw new Error(
        'Không thể kết nối tới backend. Hãy kiểm tra backend, địa chỉ API và CORS.',
      )
    }

    if (error instanceof Error) {
      throw error
    }

    throw new Error('Đã xảy ra lỗi không xác định khi gọi backend.')
  } finally {
    window.clearTimeout(timeoutId)
  }
}
