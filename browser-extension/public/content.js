(() => {
  const BUTTON_ID = 'sovereign-compliance-selection-button'
  let selectedText = ''

  const removeButton = () => document.getElementById(BUTTON_ID)?.remove()

  const openInChat = async () => {
    if (!selectedText) return
    await chrome.storage.local.set({ pendingQuestion: selectedText, pendingAt: Date.now() })
    chrome.runtime.sendMessage({ type: 'OPEN_SELECTION_IN_CHAT' })
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
      button.title = 'Đưa đoạn chọn vào Sovereign Compliance AI'
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
})()
