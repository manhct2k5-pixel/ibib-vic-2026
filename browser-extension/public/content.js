(() => {
  const BUTTON_ID = 'sovereign-compliance-selection-button'
  const BUBBLE_ID = 'sovereign-compliance-chat-bubble-v106'
  const PANEL_ID = 'sovereign-compliance-floating-panel-v106'
  let selectedText = ''

  const removePanel = () => document.getElementById(PANEL_ID)?.remove()
  const removeLegacyWidgets = () => {
    document.querySelectorAll('[id^="sovereign-compliance-chat-bubble"], [id^="sovereign-compliance-floating-panel"]').forEach((element) => element.remove())
  }
  const removeBubble = () => {
    removeLegacyWidgets()
  }
  const togglePanel = () => {
    const existing = document.getElementById(PANEL_ID)
    if (existing) {
      existing.remove()
      document.getElementById(BUBBLE_ID)?.setAttribute('aria-expanded', 'false')
      return
    }
    const panel = document.createElement('aside')
    panel.id = PANEL_ID
    panel.setAttribute('aria-label', 'IBIB')
    const close = document.createElement('button')
    close.type = 'button'
    close.className = 'sovereign-panel-close'
    close.title = 'Đóng trợ lý'
    close.setAttribute('aria-label', 'Đóng trợ lý')
    close.textContent = '×'
    close.addEventListener('click', removePanel)
    const frame = document.createElement('iframe')
    frame.src = chrome.runtime.getURL('sidepanel.html')
    frame.title = 'IBIB'
    panel.append(close, frame)
    document.documentElement.append(panel)
    document.getElementById(BUBBLE_ID)?.setAttribute('aria-expanded', 'true')
  }
  const openPanel = () => {
    if (document.getElementById(PANEL_ID)) return
    togglePanel()
  }
  const showBubble = () => {
    // Luôn thay bóng cũ sau khi extension reload để event listener không bị
    // giữ trong extension context đã hết hạn.
    removeBubble()
    const bubble = document.createElement('button')
    bubble.id = BUBBLE_ID
    bubble.type = 'button'
    bubble.title = 'Mở IBIB'
    bubble.setAttribute('aria-label', 'Mở trợ lý AI')
    bubble.setAttribute('aria-expanded', 'false')
    bubble.dataset.extensionAction = 'toggle-compliance-copilot'
    bubble.innerHTML = '<span>AI</span><i>✦</i>'
    bubble.addEventListener('pointerdown', (event) => {
      event.preventDefault()
      event.stopPropagation()
    }, true)
    bubble.addEventListener('click', (event) => {
      event.preventDefault()
      event.stopPropagation()
      togglePanel()
    }, true)
    document.documentElement.append(bubble)
  }

  const syncBubble = () => chrome.storage.local.get(['aiBubbleEnabled'], ({ aiBubbleEnabled }) => {
    if (aiBubbleEnabled === true) showBubble()
    else removeBubble()
  })

  syncBubble()

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
    if (area !== 'local' || !changes.aiBubbleEnabled) return
    if (changes.aiBubbleEnabled.newValue === true) showBubble()
    else removeBubble()
  })

  const removeButton = () => document.getElementById(BUTTON_ID)?.remove()

  const openInChat = async () => {
    if (!selectedText) return
    await chrome.storage.local.set({ pendingQuestion: selectedText, pendingAt: Date.now() })
    const { aiBubbleEnabled, activeChatSurface, activeChatSurfaceAt } = await chrome.storage.local.get(['aiBubbleEnabled', 'activeChatSurface', 'activeChatSurfaceAt'])
    const surfaceIsLive = Date.now() - Number(activeChatSurfaceAt || 0) < 5_000
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
      button.title = 'Đưa đoạn chọn vào IBIB'
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
    if (message?.type !== 'READ_CURRENT_PAGE') return
    try {
      const clone = document.body.cloneNode(true)
      clone.querySelectorAll('script, style, noscript, svg, canvas, iframe, nav, header, footer, form, button, input, textarea, select, [aria-hidden="true"]').forEach((node) => node.remove())
      const text = (clone.innerText || clone.textContent || '')
        .replace(/\u00a0/g, ' ')
        .replace(/[ \t]+/g, ' ')
        .replace(/\n{3,}/g, '\n\n')
        .trim()
        .slice(0, 16_000)
      sendResponse({ ok: true, title: document.title, url: location.href, text })
    } catch (error) {
      sendResponse({ ok: false, error: error instanceof Error ? error.message : 'Không thể đọc nội dung trang.' })
    }
  })
})()
