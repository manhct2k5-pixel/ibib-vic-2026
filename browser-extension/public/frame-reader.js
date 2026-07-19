(() => {
  const normalize = (value) => (value || '').replace(/\u00a0/g, ' ').replace(/[ \t]+/g, ' ').replace(/\n{3,}/g, '\n\n').trim()
  const keywordsOf = (query) => {
    const stopWords = new Set(['của', 'cho', 'với', 'trong', 'được', 'những', 'các', 'này', 'đó', 'là', 'và', 'hoặc', 'thì', 'về', 'theo', 'tôi', 'bạn', 'hãy', 'gì', 'như', 'nào', 'nói', 'tìm', 'thông', 'tin', 'trang', 'liên', 'quan', 'đến', 'đang', 'xem'])
    return [...new Set((query || '').toLocaleLowerCase('vi-VN').match(/[\p{L}\p{N}_-]{1,}/gu) || [])].filter((word) => (word.length >= 3 || /^\d+$/.test(word)) && !stopWords.has(word)).slice(0, 12)
  }
  const scope = (text, query) => {
    const keywords = keywordsOf(query)
    if (!keywords.length) return { text: text.slice(0, 80_000), keywords, matchedBlocks: 0, scoped: false }
    const blocks = text.split(/\n+/).map((item) => item.trim()).filter((item) => item.length > 1)
    const ranked = blocks.map((block, index) => {
      const normalized = block.toLocaleLowerCase('vi-VN')
      const matches = keywords.filter((word) => /^\d+$/.test(word) ? new RegExp(`(^|\\D)${word}(\\D|$)`).test(normalized) : normalized.includes(word))
      return { index, score: matches.length }
    }).filter((item) => item.score > 0).sort((a, b) => b.score - a.score)
    const selected = new Set()
    ranked.slice(0, 24).forEach(({ index }) => {
      selected.add(index)
      if (index > 0) selected.add(index - 1)
      if (index < blocks.length - 1) selected.add(index + 1)
    })
    const result = selected.size ? [...selected].sort((a, b) => a - b).map((index) => blocks[index]).join('\n\n') : text.slice(0, 20_000)
    return { text: result.slice(0, 40_000), keywords, matchedBlocks: ranked.length, scoped: true }
  }
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type !== 'READ_FRAME_CONTENT') return
    try {
      const clone = document.body?.cloneNode(true)
      if (!clone) throw new Error('Frame chưa có nội dung.')
      clone.querySelectorAll('script,style,noscript,nav,footer,form,button,input,textarea,select,[aria-hidden="true"]').forEach((node) => node.remove())
      const fullText = normalize(clone.innerText || clone.textContent).slice(0, 400_000)
      sendResponse({ ok: Boolean(fullText), title: document.title, url: location.href, fullLength: fullText.length, ...scope(fullText, message.query) })
    } catch (error) {
      sendResponse({ ok: false, error: error instanceof Error ? error.message : 'Không thể đọc frame.' })
    }
  })
})()
