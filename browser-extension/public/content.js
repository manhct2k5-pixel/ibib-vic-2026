(() => {
  const BUTTON_ID = 'sovereign-compliance-selection-button'
  const BUBBLE_ID = 'sovereign-compliance-chat-bubble-v1'
  const PANEL_ID = 'sovereign-compliance-floating-panel-v1'
  const BUBBLE_POSITION_KEY = 'aiBubblePosition'

  // Magic numbers extracted as constants
  const CONFIG = {
    MAX_TEXT_LENGTH: 80_000,
    MAX_SCAN_LENGTH: 400_000,
    SURFACE_LIVE_TIMEOUT: 5_000,
    MIN_DRAG_THRESHOLD: 5,
    PADDING: 8,
    CHAT_BUBBLE_SIZE: 56,
    CHAT_BUBBLE_SIZE_MOBILE: 50,
    ANIMATION_DURATION: { POP: 140, PANEL: 200 }
  }

  let selectedText = ''
  let bubbleDragListeners = null

  const isIbibChatbotPage = () => {
    const path = location.pathname.replace(/\/+$/, '') || '/'
    return path === '/chatbot' && Boolean(document.querySelector('.app-shell'))
  }

  const clamp = (value, min, max) => Math.min(Math.max(value, min), Math.max(min, max))
  const applyBubblePosition = (bubble, position) => {
    if (!bubble || !position || !Number.isFinite(position.x) || !Number.isFinite(position.y)) return
    const rect = bubble.getBoundingClientRect()
    const maxLeft = Math.max(CONFIG.PADDING, window.innerWidth - rect.width - CONFIG.PADDING)
    const maxTop = Math.max(CONFIG.PADDING, window.innerHeight - rect.height - CONFIG.PADDING)
    bubble.style.left = `${clamp(position.x * maxLeft, CONFIG.PADDING, maxLeft)}px`
    bubble.style.top = `${clamp(position.y * maxTop, CONFIG.PADDING, maxTop)}px`
    bubble.style.right = 'auto'
    bubble.style.bottom = 'auto'
  }

  const removePanel = () => {
    const panel = document.getElementById(PANEL_ID)
    if (panel) {
      // Clean up bubble drag listeners when panel closes
      if (bubbleDragListeners) {
        window.removeEventListener('pointermove', bubbleDragListeners.move, true)
        window.removeEventListener('pointerup', bubbleDragListeners.finish, true)
        window.removeEventListener('pointercancel', bubbleDragListeners.finish, true)
        bubbleDragListeners = null
      }
      panel.remove()
    }
  }
  const removeLegacyWidgets = () => {
    document.querySelectorAll('[id^="sovereign-compliance-chat-bubble"], [id^="sovereign-compliance-floating-panel"]').forEach((element) => element.remove())
  }
  const removeBubble = () => {
    removeLegacyWidgets()
  }
  const togglePanel = async () => {
    const existing = document.getElementById(PANEL_ID)
    if (existing) {
      existing.remove()
      document.getElementById(BUBBLE_ID)?.setAttribute('aria-expanded', 'false')
      return
    }
    const panel = document.createElement('aside')
    panel.id = PANEL_ID
    panel.className = 'loading'
    panel.setAttribute('aria-label', 'SovAI')

    // Close button
    const close = document.createElement('button')
    close.type = 'button'
    close.className = 'sovereign-panel-close'
    close.title = 'Đóng trợ lý'
    close.setAttribute('aria-label', 'Đóng trợ lý')
    close.textContent = '×'
    close.addEventListener('click', removePanel)

    const frame = document.createElement('iframe')
    frame.src = chrome.runtime.getURL('sidepanel.html')
    frame.title = 'SovAI'
    frame.addEventListener('load', () => {
      panel.classList.remove('loading')
    })
    panel.append(close, frame)
    document.documentElement.append(panel)
    document.getElementById(BUBBLE_ID)?.setAttribute('aria-expanded', 'true')
  }
  const openPanel = () => {
    if (document.getElementById(PANEL_ID)) return
    togglePanel()
  }
  const showBubble = () => {
    if (isIbibChatbotPage()) {
      removeBubble()
      return
    }
    // Luôn thay bóng cũ sau khi extension reload để event listener không bị
    // giữ trong extension context đã hết hạn.
    removeBubble()
    const bubble = document.createElement('button')
    bubble.id = BUBBLE_ID
    bubble.type = 'button'
    bubble.title = 'Mở SovAI'
    bubble.setAttribute('aria-label', 'Mở trợ lý AI')
    bubble.setAttribute('aria-expanded', 'false')
    bubble.dataset.extensionAction = 'toggle-compliance-copilot'
    bubble.innerHTML = '<span>AI</span><i>✦</i>'
    let dragState = null
    let suppressNextClick = false
    const moveBubble = (event) => {
      if (!dragState || event.pointerId !== dragState.pointerId) return
      event.preventDefault()
      event.stopPropagation()
      if (Math.hypot(event.clientX - dragState.startX, event.clientY - dragState.startY) >= CONFIG.MIN_DRAG_THRESHOLD) dragState.moved = true
      if (!dragState.moved) return
      const rect = bubble.getBoundingClientRect()
      const maxLeft = Math.max(CONFIG.PADDING, window.innerWidth - rect.width - CONFIG.PADDING)
      const maxTop = Math.max(CONFIG.PADDING, window.innerHeight - rect.height - CONFIG.PADDING)
      bubble.style.setProperty('left', `${clamp(event.clientX - dragState.offsetX, CONFIG.PADDING, maxLeft)}px`, 'important')
      bubble.style.setProperty('top', `${clamp(event.clientY - dragState.offsetY, CONFIG.PADDING, maxTop)}px`, 'important')
      bubble.style.setProperty('right', 'auto', 'important')
      bubble.style.setProperty('bottom', 'auto', 'important')
    }
    const finishDrag = (event) => {
      if (!dragState || event.pointerId !== dragState.pointerId) return
      event.preventDefault()
      event.stopPropagation()
      const wasMoved = dragState.moved
      dragState = null
      window.removeEventListener('pointermove', moveBubble, true)
      window.removeEventListener('pointerup', finishDrag, true)
      window.removeEventListener('pointercancel', finishDrag, true)
      bubble.classList.remove('sovereign-bubble-dragging')
      if (!wasMoved) return
      suppressNextClick = true
      const rect = bubble.getBoundingClientRect()
      const maxLeft = Math.max(1, window.innerWidth - rect.width - CONFIG.PADDING)
      const maxTop = Math.max(1, window.innerHeight - rect.height - CONFIG.PADDING)
      chrome.storage.local.set({
        [BUBBLE_POSITION_KEY]: {
          x: clamp(rect.left / maxLeft, 0, 1),
          y: clamp(rect.top / maxTop, 0, 1),
        },
      })
    }
    // Store references for cleanup
    bubbleDragListeners = { move: moveBubble, finish: finishDrag }
    bubble.addEventListener('pointerdown', (event) => {
      if (event.button !== 0) return
      event.preventDefault()
      event.stopPropagation()
      const rect = bubble.getBoundingClientRect()
      dragState = {
        pointerId: event.pointerId,
        offsetX: event.clientX - rect.left,
        offsetY: event.clientY - rect.top,
        startX: event.clientX,
        startY: event.clientY,
        moved: false,
      }
      bubble.classList.add('sovereign-bubble-dragging')
      window.addEventListener('pointermove', moveBubble, { capture: true, passive: false })
      window.addEventListener('pointerup', finishDrag, { capture: true, passive: false })
      window.addEventListener('pointercancel', finishDrag, { capture: true, passive: false })
    }, { capture: true, passive: false })
    bubble.addEventListener('click', (event) => {
      event.preventDefault()
      event.stopPropagation()
      if (suppressNextClick) {
        suppressNextClick = false
        return
      }
      togglePanel()
    }, true)
    document.documentElement.append(bubble)
    chrome.storage.local.get([BUBBLE_POSITION_KEY], ({ aiBubblePosition }) => applyBubblePosition(bubble, aiBubblePosition))
  }

  const syncBubble = () => chrome.storage.local.get(['aiBubbleEnabled'], ({ aiBubbleEnabled }) => {
    if (aiBubbleEnabled === true && !isIbibChatbotPage()) showBubble()
    else removeBubble()
  })

  syncBubble()

  // Frontend dùng điều hướng SPA nên content script không được nạp lại khi đi
  // từ đăng nhập sang /chatbot. Theo dõi thay đổi route/DOM để ẩn bóng ngay khi
  // giao diện chatbot SovAI xuất hiện, nhưng không tắt bóng trên các website khác.
  let bubbleHiddenForIbib = isIbibChatbotPage()
  let reconcileQueued = false
  const reconcileBubbleForPage = () => {
    if (reconcileQueued) return
    reconcileQueued = true
    queueMicrotask(() => {
      reconcileQueued = false
      const shouldHide = isIbibChatbotPage()
      if (shouldHide === bubbleHiddenForIbib) return
      bubbleHiddenForIbib = shouldHide
      if (shouldHide) removeBubble()
      else syncBubble()
    })
  }
  window.addEventListener('popstate', reconcileBubbleForPage)
  new MutationObserver(reconcileBubbleForPage).observe(document.documentElement, { childList: true, subtree: true })

  let reportedAuthRole = ''
  const syncFrontendSession = () => {
    if (!['localhost', '127.0.0.1'].includes(location.hostname)) return
    try {
      const raw = localStorage.getItem('compliance-ai-session')
      const session = raw ? JSON.parse(raw) : null
      const role = session?.role === 'manager' ? 'manager' : session?.role === 'employee' ? 'employee' : null
      chrome.storage.local.set({ extensionAuthenticated: Boolean(role), authenticatedRole: role || '' })
      if (role && reportedAuthRole !== role) {
        reportedAuthRole = role
        chrome.runtime.sendMessage({ type: 'AUTH_COMPLETED', role }).catch(() => {})
      }
    } catch {
      chrome.storage.local.set({ extensionAuthenticated: false, authenticatedRole: '' })
    }
  }
  syncFrontendSession()
  if (['localhost', '127.0.0.1'].includes(location.hostname)) window.setInterval(syncFrontendSession, 1_000)
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== 'local') return
    if (changes.aiBubbleEnabled) {
      if (changes.aiBubbleEnabled.newValue === true && !isIbibChatbotPage()) showBubble()
      else removeBubble()
    }
    if (changes[BUBBLE_POSITION_KEY]) {
      applyBubblePosition(document.getElementById(BUBBLE_ID), changes[BUBBLE_POSITION_KEY].newValue)
    }
  })

  window.addEventListener('resize', () => {
    const bubble = document.getElementById(BUBBLE_ID)
    if (!bubble) return
    chrome.storage.local.get([BUBBLE_POSITION_KEY], ({ aiBubblePosition }) => applyBubblePosition(bubble, aiBubblePosition))
  })

  const removeButton = () => document.getElementById(BUTTON_ID)?.remove()

  const openInChat = async () => {
    if (!selectedText) return
    await chrome.storage.local.set({ pendingQuestion: selectedText, pendingAt: Date.now() })
    const { aiBubbleEnabled, activeChatSurface, activeChatSurfaceAt } = await chrome.storage.local.get(['aiBubbleEnabled', 'activeChatSurface', 'activeChatSurfaceAt'])
    const surfaceIsLive = Date.now() - Number(activeChatSurfaceAt || 0) < CONFIG.SURFACE_LIVE_TIMEOUT
    if (surfaceIsLive && activeChatSurface === 'native') {
      // Side Panel Chrome đang mở và tự nhận pendingQuestion qua storage.
    } else if (document.getElementById(PANEL_ID) || (surfaceIsLive && activeChatSurface === 'floating')) {
      openPanel()
    } else if (aiBubbleEnabled === true) openPanel()
    else chrome.runtime.sendMessage({ type: 'OPEN_SELECTION_IN_CHAT' })
    removeButton()
  }

  const showButton = () => {
    window.setTimeout(() => {
      const selection = window.getSelection()
      const text = selection?.toString().trim() || ''
      if (!text || !selection?.rangeCount) {
        removeButton()
        return
      }

      const range = selection.getRangeAt(0)
      const rect = range.getBoundingClientRect()
      if (!rect.width && !rect.height) return
      selectedText = text
      removeButton()

      const button = document.createElement('button')
      button.id = BUTTON_ID
      button.type = 'button'
      button.title = 'Đưa đoạn chọn vào SovAI'
      button.setAttribute('aria-label', 'Đưa đoạn chọn vào chat')
      button.innerHTML = '<span>◆</span><b>Hỏi AI</b>'
      button.style.left = `${Math.min(window.innerWidth - 88, Math.max(8, rect.right + window.scrollX - 76))}px`
      button.style.top = `${Math.max(8, rect.top + window.scrollY - 42)}px`
      button.addEventListener('mousedown', (event) => event.preventDefault())
      button.addEventListener('click', openInChat)
      document.documentElement.append(button)
    }, 0)
  }

  document.addEventListener('mouseup', showButton, true)
  document.addEventListener('keyup', (event) => {
    if (event.key === 'Shift' || event.key.startsWith('Arrow')) showButton()
  }, true)
  document.addEventListener('mousedown', (event) => {
    if (event.button === 2) return
    if (!(event.target instanceof Element) || event.target.closest(`#${BUTTON_ID}`)) return
    removeButton()
  }, true)
  window.addEventListener('scroll', removeButton, { passive: true })

  const normalizePageText = (value) => value
    .replace(/\u00a0/g, ' ')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim()

  const scopePageText = (text, query) => {
    const cleanQuery = normalizePageText(query || '').toLocaleLowerCase('vi-VN')
    if (!cleanQuery) return { text: text.slice(0, CONFIG.MAX_TEXT_LENGTH), scoped: false, keywords: [], matchedBlocks: 0 }
    const stopWords = new Set(['của', 'cho', 'với', 'trong', 'được', 'những', 'các', 'này', 'đó', 'là', 'và', 'hoặc', 'thì', 'về', 'theo', 'tôi', 'bạn', 'hãy', 'gì', 'như', 'nào', 'tìm', 'thông', 'tin', 'trang', 'liên', 'quan', 'đến', 'đang', 'xem'])
    const keywords = [...new Set(cleanQuery.match(/[\p{L}\p{N}_-]{2,}/gu) || [])]
      .filter((word) => word.length >= 3 && !stopWords.has(word))
      .slice(0, 12)
    if (!keywords.length) return { text, scoped: false, keywords: [], matchedBlocks: 0 }
    const blocks = text.split(/\n{2,}/).map((block) => block.trim()).filter(Boolean)
    const ranked = blocks.map((block, index) => {
      const normalized = block.toLocaleLowerCase('vi-VN')
      const matches = keywords.filter((word) => normalized.includes(word))
      const headingBoost = block.startsWith('#') ? 2 : 0
      return { index, score: matches.length * 4 + headingBoost, matches }
    }).filter((item) => item.matches.length > 0).sort((a, b) => b.score - a.score)
    if (!ranked.length) return { text: text.slice(0, 24_000), scoped: true, keywords, matchedBlocks: 0 }
    const selected = new Set()
    for (const item of ranked.slice(0, 18)) {
      selected.add(item.index)
      if (item.index > 0) selected.add(item.index - 1)
      if (item.index < blocks.length - 1) selected.add(item.index + 1)
    }
    let scopedText = [...selected].sort((a, b) => a - b).map((index) => blocks[index]).join('\n\n')
    if (scopedText.length > 32_000) scopedText = scopedText.slice(0, 32_000)
    return { text: scopedText, scoped: true, keywords, matchedBlocks: ranked.length }
  }

  const extractReadablePage = () => {
    const blocks = []
    const seen = new Set()
    const warnings = []
    const add = (value, prefix = '') => {
      const text = normalizePageText(value || '')
      if (!text || text.length < 2) return
      const key = text.toLocaleLowerCase('vi-VN')
      if (seen.has(key)) return
      seen.add(key)
      blocks.push(`${prefix}${text}`)
    }
    const readRoot = (root, label = '') => {
      const selector = 'h1,h2,h3,h4,h5,h6,p,li,blockquote,pre,td,th,figcaption,article,main,[role="article"],section,div,span'
      const elements = root.querySelectorAll?.(selector) || []
      for (const element of elements) {
        if (element.closest?.('script,style,noscript,nav,footer,form,button,input,textarea,select,[aria-hidden="true"]')) continue
        if (element.matches('article,main,[role="article"],section,div,span') && element.querySelector(selector)) continue
        const tag = element.tagName?.toLowerCase()
        const prefix = /^h[1-6]$/.test(tag) ? `${'#'.repeat(Number(tag[1]))} ` : tag === 'li' ? '- ' : ''
        add(element.innerText || element.textContent, prefix)
      }
      // Một số thư viện pháp luật đặt câu chữ trực tiếp trong div và phân cách
      // bằng <br>/<a>, không bọc trong p/li. Đọc các text node chưa được nhóm bởi
      // phần tử ngữ nghĩa để không bỏ sót phần nội dung văn bản phản chiếu.
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
      let textNode = walker.nextNode()
      while (textNode) {
        const parent = textNode.parentElement
        if (parent
          && !parent.closest('script,style,noscript,nav,footer,form,button,input,textarea,select,[aria-hidden="true"]')
          && !parent.closest('h1,h2,h3,h4,h5,h6,p,li,blockquote,pre,td,th,figcaption,span')) {
          add(textNode.nodeValue)
        }
        textNode = walker.nextNode()
      }
      for (const element of root.querySelectorAll?.('*') || []) {
        if (element.shadowRoot) readRoot(element.shadowRoot, 'Shadow DOM')
      }
      if (label && elements.length === 0) warnings.push(`${label} không có văn bản có thể đọc.`)
    }
    readRoot(document, 'Trang chính')
    let readableFrames = 0
    for (const frame of document.querySelectorAll('iframe')) {
      try {
        if (frame.contentDocument?.body) {
          readableFrames += 1
          add(frame.title || frame.name, '## Nội dung iframe: ')
          readRoot(frame.contentDocument, `iframe ${frame.title || readableFrames}`)
        } else warnings.push('Có iframe không cung cấp nội dung văn bản.')
      } catch {
        warnings.push('Có iframe khác nguồn nên tiện ích không được phép đọc nội dung.')
      }
    }
    for (const image of document.images) {
      if (image.alt?.trim()) add(image.alt, 'Hình ảnh: ')
    }
    const metadata = [
      document.querySelector('meta[name="description"]')?.content,
      document.querySelector('meta[property="og:description"]')?.content,
    ].filter(Boolean)
    metadata.forEach((item) => add(item, 'Mô tả trang: '))
    const fullText = normalizePageText(blocks.join('\n\n'))
    if (document.querySelector('canvas')) warnings.push('Trang có canvas/biểu đồ; tiện ích chưa đọc được chữ nằm trong hình vẽ.')
    if (document.images.length && !Array.from(document.images).some((image) => image.alt?.trim())) warnings.push('Trang có hình ảnh không có mô tả; nội dung trong ảnh chưa được nhận dạng OCR.')
    if (/\.pdf(?:$|[?#])/i.test(location.href) || document.contentType === 'application/pdf') warnings.push('PDF đang mở bằng trình xem của trình duyệt có thể không cung cấp toàn bộ văn bản cho content script.')
    return {
      text: fullText.slice(0, CONFIG.MAX_SCAN_LENGTH),
      truncated: fullText.length > CONFIG.MAX_TEXT_LENGTH,
      warnings: [...new Set(warnings)],
      stats: { characters: Math.min(fullText.length, CONFIG.MAX_SCAN_LENGTH), blocks: blocks.length, readableFrames },
    }
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type === 'OPEN_FLOATING_WITH_SELECTION') {
      if (typeof message.text === 'string' && message.text.trim()) {
        chrome.storage.local.set({ pendingQuestion: message.text.trim(), pendingAt: Date.now() })
      }
      openPanel()
      sendResponse({ ok: true })
      return
    }
    if (message?.type === 'SET_CHAT_BUBBLE') {
      if (message.enabled === true) showBubble()
      else removeBubble()
      sendResponse({ ok: true })
      return
    }
    if (message?.type === 'READ_FRAME_CONTENT') {
      try {
        const extracted = extractReadablePage()
        const scoped = scopePageText(extracted.text, message.query)
        sendResponse({
          ok: true,
          title: document.title,
          url: location.href,
          fullLength: extracted.text.length,
          text: scoped.text,
          keywords: scoped.keywords,
          matchedBlocks: scoped.matchedBlocks,
          scoped: scoped.scoped,
        })
      } catch (error) {
        sendResponse({ ok: false, error: error instanceof Error ? error.message : 'Không thể đọc frame.' })
      }
      return
    }
    if (message?.type !== 'READ_CURRENT_PAGE') return
    try {
      const extracted = extractReadablePage()
      const scoped = scopePageText(extracted.text, message.query)

      // Generate hash for deduplication
      const hashInput = `${location.href}|${document.title}|${extracted.text.length}|${extracted.text.slice(0, 200)}`
      let hashValue = 0
      for (let index = 0; index < hashInput.length; index += 1) hashValue = ((hashValue << 5) - hashValue + hashInput.charCodeAt(index)) | 0
      const pageHash = Math.abs(hashValue).toString(36)
      const cachedData = {
        url: location.href,
        title: document.title,
        text: scopePageText(extracted.text, '').text,
        warnings: extracted.warnings,
        truncated: extracted.truncated,
        stats: extracted.stats,
        extractedAt: Date.now(),
        hash: pageHash
      }

      // Cache extracted data to Chrome Storage (persists across components)
      chrome.storage.local.set({ cachedPageData: cachedData })

      sendResponse({
        ok: true,
        title: document.title,
        url: location.href,
        hash: pageHash,
        ...extracted,
        text: scoped.text,
        scope: { scoped: scoped.scoped, keywords: scoped.keywords, matchedBlocks: scoped.matchedBlocks },
      })
    } catch (error) {
      sendResponse({ ok: false, error: error instanceof Error ? error.message : 'Không thể đọc nội dung trang.' })
    }
  })
})()
