'use client'

import { useEffect, useState } from 'react'

export default function PopupPage() {
  const [enabled, setEnabled] = useState(false)

  useEffect(() => {
    chrome.storage.local.get(['aiBubbleEnabled'], ({ aiBubbleEnabled }) => setEnabled(aiBubbleEnabled === true))
  }, [])

  const toggleBubble = async () => {
    const next = !enabled
    setEnabled(next)
    await chrome.storage.local.set({ aiBubbleEnabled: next })
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
    if (!tab?.id || !tab.url?.match(/^https?:\/\//)) return
    try {
      const response = await chrome.tabs.sendMessage(tab.id, { type: 'SET_CHAT_BUBBLE', enabled: next }) as { ok?: boolean } | undefined
      if (!response?.ok) throw new Error('Content script chưa sẵn sàng.')
    } catch {
      await chrome.scripting.insertCSS({ target: { tabId: tab.id }, files: ['content.css'] })
      await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['content.js'] })
      await chrome.tabs.sendMessage(tab.id, { type: 'SET_CHAT_BUBBLE', enabled: next })
    }
  }

  const openPanel = async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
    if (tab?.windowId) await chrome.sidePanel.open({ windowId: tab.windowId })
    window.close()
  }

  return <main className="popup-page"><div className="brand-mark">AI</div><strong>SovAI</strong><p>Bật bóng chat để mở trợ lý ngay trên mọi trang web.</p><label className="bubble-toggle"><span><b>Bóng chat trên trang</b><small>{enabled ? 'Đang bật' : 'Đang tắt'}</small></span><input type="checkbox" checked={enabled} onChange={() => void toggleBubble()} /><i /></label><button type="button" onClick={openPanel}>Mở trợ lý ngay</button></main>
}
