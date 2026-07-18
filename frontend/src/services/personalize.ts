// Cá nhân hoá phía client (FR-20, Story 7.5): lịch sử tra cứu + bookmark.
// Dùng localStorage — né auth doanh nghiệp, chỉ theo trình duyệt người dùng.

const HISTORY_KEY = 'ibib.history'
const BOOKMARK_KEY = 'ibib.bookmarks'
const MAX_HISTORY = 20

const readList = (key: string): string[] => {
  try {
    const raw = localStorage.getItem(key)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.filter((x) => typeof x === 'string') : []
  } catch {
    return []
  }
}

const writeList = (key: string, list: string[]) => {
  try {
    localStorage.setItem(key, JSON.stringify(list))
  } catch {
    /* localStorage đầy/tắt — bỏ qua, không chặn UX */
  }
}

export const getHistory = (): string[] => readList(HISTORY_KEY)

export const addHistory = (question: string): string[] => {
  const q = question.trim()
  if (!q) return getHistory()
  const next = [q, ...getHistory().filter((item) => item !== q)].slice(0, MAX_HISTORY)
  writeList(HISTORY_KEY, next)
  return next
}

export const clearHistory = (): void => writeList(HISTORY_KEY, [])

export const getBookmarks = (): string[] => readList(BOOKMARK_KEY)

export const isBookmarked = (question: string): boolean =>
  getBookmarks().includes(question.trim())

export const toggleBookmark = (question: string): string[] => {
  const q = question.trim()
  if (!q) return getBookmarks()
  const current = getBookmarks()
  const next = current.includes(q)
    ? current.filter((item) => item !== q)
    : [q, ...current]
  writeList(BOOKMARK_KEY, next)
  return next
}
