const MENU_ID = 'compliance-copilot-search'

const createContextMenu = () => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: MENU_ID,
      title: 'Hỏi Sovereign Compliance AI về “%s”',
      contexts: ['selection'],
    })
  })
}

chrome.runtime.onInstalled.addListener(() => {
  createContextMenu()
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {})
})

chrome.runtime.onStartup.addListener(createContextMenu)

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== MENU_ID || !info.selectionText) return
  chrome.storage.local.set({ pendingQuestion: info.selectionText.trim(), pendingAt: Date.now() })
  if (tab?.windowId) chrome.sidePanel.open({ windowId: tab.windowId }).catch(() => {})
})

chrome.runtime.onMessage.addListener((message, sender) => {
  if (message?.type !== 'OPEN_SELECTION_IN_CHAT' || !sender.tab?.windowId) return
  chrome.sidePanel.open({ windowId: sender.tab.windowId }).catch(() => {})
})
