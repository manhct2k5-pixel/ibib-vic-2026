export type SourceItem = {
  name: string
  description: string
}

export type ChatResponse = {
  answer: string
  sources: SourceItem[]
  requestId?: string
  latencyMs?: number
}

const API_MODE = import.meta.env.VITE_API_MODE ?? 'mock'

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
).replace(/\/$/, '')

const REQUEST_TIMEOUT_MS = 15_000

const createMockResponse = async (
  question: string,
): Promise<ChatResponse> => {
  await new Promise((resolve) => window.setTimeout(resolve, 800))

  return {
    answer:
      `Hệ thống đã nhận yêu cầu: "${question}". ` +
      'Đây là phản hồi mô phỏng để kiểm tra giao diện của Team IBIB.',
    sources: [
      {
        name: 'Nguồn dữ liệu mẫu',
        description:
          'Nguồn này sẽ được thay bằng API hoặc dữ liệu chính thức của đề thi.',
      },
    ],
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
        name: source.name,
        description:
          typeof source.description === 'string'
            ? source.description
            : '',
      },
    ]
  })
}

export const sendChatRequest = async (
  question: string,
): Promise<ChatResponse> => {
  if (API_MODE === 'mock') {
    return createMockResponse(question)
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
      requestId:
        typeof payload.requestId === 'string'
          ? payload.requestId
          : undefined,
      latencyMs:
        typeof payload.latencyMs === 'number'
          ? payload.latencyMs
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
