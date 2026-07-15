import { useState } from 'react'
import type { FormEvent } from 'react'
import {
  sendChatRequest,
  type SourceItem,
} from './services/chatApi'
import './App.css'

function App() {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sources, setSources] = useState<SourceItem[]>([])

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault()

    const cleanQuestion = question.trim()

    if (!cleanQuestion) {
      setError('Vui lòng nhập yêu cầu trước khi gửi.')
      setAnswer('')
      setSources([])
      return
    }

    setError('')
    setAnswer('')
    setSources([])
    setIsLoading(true)

    try {
      const response = await sendChatRequest(cleanQuestion)

      setAnswer(response.answer)
      setSources(response.sources)
    } catch (requestError: unknown) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : 'Đã xảy ra lỗi không xác định.'

      setError(message)
      setAnswer('')
      setSources([])
    } finally {
      setIsLoading(false)
    }
  }

  const handleReset = () => {
    setQuestion('')
    setAnswer('')
    setError('')
    setSources([])
    setIsLoading(false)
  }

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <p className="team-label">TEAM IBIB</p>
          <h1>Trợ lý AI</h1>
        </div>

        <span className="status-badge">
          <span className="status-dot" />
          Giao diện thử nghiệm
        </span>
      </header>

      <main className="main-content">
        <section className="intro-card">
          <p className="section-label">
            VIETNAM INNOVATION CHALLENGE 2026
          </p>

          <h2>Nhập yêu cầu để thử luồng xử lý</h2>

          <p>
            Giao diện này là khung dùng chung. Nội dung, dữ liệu và chức năng
            sẽ được điều chỉnh sau khi đội nhận đề chính thức.
          </p>
        </section>

        <section className="workspace">
          <form className="request-card" onSubmit={handleSubmit}>
            <label htmlFor="question">
              Yêu cầu của người dùng
            </label>

            <textarea
              id="question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ví dụ: Hãy phân tích dữ liệu và đề xuất bước xử lý tiếp theo..."
              rows={6}
              disabled={isLoading}
            />

            <div className="button-row">
              <button
                className="secondary-button"
                type="button"
                onClick={handleReset}
                disabled={isLoading}
              >
                Xóa nội dung
              </button>

              <button
                className="primary-button"
                type="submit"
                disabled={isLoading}
              >
                {isLoading ? 'Đang xử lý...' : 'Gửi yêu cầu'}
              </button>
            </div>

            {error && (
              <p className="error-message">
                {error}
              </p>
            )}
          </form>

          <section className="result-card" aria-live="polite">
            <div className="result-heading">
              <p className="section-label">KẾT QUẢ</p>
              <h2>Phản hồi của hệ thống</h2>
            </div>

            {!answer && !isLoading && (
              <div className="empty-state">
                Kết quả sẽ xuất hiện tại đây sau khi gửi yêu cầu.
              </div>
            )}

            {isLoading && (
              <div className="loading-state">
                <span className="spinner" />
                Hệ thống đang xử lý yêu cầu...
              </div>
            )}

            {answer && (
              <>
                <div className="answer-box">
                  {answer}
                </div>

                {sources.length > 0 && (
                  <div className="sources">
                    <h3>Nguồn tham khảo</h3>

                    {sources.map((source, index) => (
                      <article
                        className="source-item"
                        key={`${source.name}-${index}`}
                      >
                        <strong>{source.name}</strong>
                        <span>{source.description}</span>
                      </article>
                    ))}
                  </div>
                )}
              </>
            )}
          </section>
        </section>
      </main>

      <footer>
        Team IBIB · Vietnam Innovation Challenge 2026
      </footer>
    </div>
  )
}

export default App