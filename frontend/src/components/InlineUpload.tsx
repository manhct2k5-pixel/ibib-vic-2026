import { useRef, useState } from 'react'
import { uploadSessionPdf, type SessionUploadResult } from '../services/sessionApi'

export type UploadError = { name: string; message: string }

type Props = {
  sessionId: string
  onComplete: (results: SessionUploadResult[], errors: UploadError[]) => void
  onUploadStart?: (fileName: string) => void
  onUploadEnd?: () => void
  onFileUploaded?: (result: SessionUploadResult) => void
  abortControllerRef?: React.MutableRefObject<AbortController | null>
}

// Đính kèm nhiều PDF theo phiên (FR-17/FR-18, AD-13): chọn file → backend phân
// tích (metadata + quan hệ) + cắt Điều → clause phiên (không persist). Upload tuần
// tự, báo tiến độ, gom lỗi từng file và gọi onComplete MỘT LẦN khi xong hết.
function InlineUpload({ sessionId, onComplete, onUploadStart, onUploadEnd, onFileUploaded, abortControllerRef }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(false)

  const onPick = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? [])
    if (inputRef.current) inputRef.current.value = ''
    if (files.length === 0) return

    setBusy(true)
    const results: SessionUploadResult[] = []
    const errors: UploadError[] = []

    const controller = new AbortController()
    if (abortControllerRef) {
      abortControllerRef.current = controller
    }

    for (const [index, file] of files.entries()) {
      if (controller.signal.aborted) break
      setStatus(`Đang phân tích "${file.name}" (${index + 1}/${files.length})…`)
      if (onUploadStart) onUploadStart(file.name)
      try {
        const res = await uploadSessionPdf(sessionId, file, '', controller.signal)
        results.push(res)
        if (onFileUploaded) onFileUploaded(res)
      } catch (e: unknown) {
        if (e instanceof Error && e.name === 'AbortError') {
          break
        }
        errors.push({ name: file.name, message: e instanceof Error ? e.message : 'lỗi' })
      }
    }
    setStatus('')
    setBusy(false)
    if (onUploadEnd) onUploadEnd()
    if (abortControllerRef) {
      abortControllerRef.current = null
    }
    onComplete(results, errors)
  }

  return (
    <span className="inline-upload">
      <button
        type="button"
        aria-label="Đính kèm tài liệu PDF (phiên này)"
        title="Đính kèm PDF — có thể chọn nhiều file (chỉ trong phiên này)"
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
        multiple
        hidden
        onChange={onPick}
      />
      {status && <span className="upload-note">{status}</span>}
    </span>
  )
}

export default InlineUpload
