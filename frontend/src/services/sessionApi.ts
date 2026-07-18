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
  effective_date?: string
  chars?: number
}

// PDF số → backend cắt theo Điều + LLM trích hiệu lực → clause phiên.
export const uploadSessionPdf = async (
  sessionId: string,
  file: File,
  docCode = '',
): Promise<SessionUploadResult> => {
  const form = new FormData()
  form.append('sessionId', sessionId)
  form.append('file', file)
  if (docCode) form.append('docCode', docCode)

  const response = await fetch(`${API_BASE_URL}/api/session/upload-pdf`, {
    method: 'POST',
    body: form,
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
