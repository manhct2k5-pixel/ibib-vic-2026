import { useRef, useState } from 'react'
import { uploadSessionPdf, type SessionUploadResult } from '../services/sessionApi'

type Props = {
  sessionId: string
  onUploaded: (result: SessionUploadResult) => void
}

// Đính kèm PDF theo phiên (FR-18, AD-13): chọn file → backend cắt Điều + LLM trích
// hiệu lực → clause phiên (không persist). Báo số điều khoản nạp được.
function InlineUpload({ sessionId, onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const onPick = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    setBusy(true)
    setError('')
    setStatus(`Đang phân tách "${file.name}"…`)
    try {
      const result = await uploadSessionPdf(sessionId, file)
      setStatus(
        `Đã nạp ${result.added} điều khoản từ ${result.docCode}` +
          (result.effective_date ? ` (hiệu lực ${result.effective_date})` : ''),
      )
      onUploaded(result)
    } catch (e: unknown) {
      setStatus('')
      setError(e instanceof Error ? e.message : 'Lỗi tải tài liệu.')
    } finally {
      setBusy(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <span className="inline-upload">
      <button
        type="button"
        aria-label="Đính kèm tài liệu PDF (phiên này)"
        title="Đính kèm PDF (chỉ trong phiên này)"
        disabled={busy}
        onClick={() => inputRef.current?.click()}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="m21.4 11.6-8.9 8.9a6 6 0 0 1-8.5-8.5l9.6-9.6a4 4 0 0 1 5.7 5.7l-9.6 9.6a2 2 0 0 1-2.8-2.8l8.9-8.9" />
        </svg>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        hidden
        onChange={onPick}
      />
      {status && <span className="upload-note">{status}</span>}
      {error && <span className="upload-note error">{error}</span>}
    </span>
  )
}

export default InlineUpload
