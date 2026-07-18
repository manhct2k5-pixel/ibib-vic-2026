'use client'

export default function PopupPage() {
  const openPanel = async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
    if (tab?.windowId) await chrome.sidePanel.open({ windowId: tab.windowId })
    window.close()
  }

  return <main className="popup-page"><div className="brand-mark">◆</div><strong>Sovereign Compliance AI</strong><p>Mở trợ lý ở thanh bên để tra cứu mà không rời trang hiện tại.</p><button type="button" onClick={openPanel}>Mở Side Panel</button></main>
}
