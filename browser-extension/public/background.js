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

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== MENU_ID || !info.selectionText) return
  chrome.storage.local.set({ pendingQuestion: info.selectionText.trim(), pendingAt: Date.now() })
  const enabled = await getBubbleEnabled()
  const surface = await getActiveSurface()
  if (surface === 'native') {
    return
  } else if (enabled && tab?.id) {
    chrome.tabs.sendMessage(tab.id, { type: 'OPEN_FLOATING_WITH_SELECTION', text: info.selectionText.trim() }).catch(() => {})
  } else if (tab?.id) {
    chrome.sidePanel.open({ tabId: tab.id }).catch(() => {})
  }
})

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === 'AUTH_COMPLETED') {
    chrome.storage.local.get(['authReturnTabId'], async ({ authReturnTabId }) => {
      const returnTabId = Number(authReturnTabId)
      if (Number.isInteger(returnTabId) && returnTabId > 0) {
        const returnTab = await chrome.tabs.get(returnTabId).catch(() => null)
        if (returnTab) {
          await chrome.tabs.update(returnTabId, { active: true }).catch(() => {})
          if (returnTab.windowId) await chrome.windows.update(returnTab.windowId, { focused: true }).catch(() => {})
          if (sender.tab?.id && sender.tab.id !== returnTabId) await chrome.tabs.remove(sender.tab.id).catch(() => {})
        }
      }
      await chrome.storage.local.remove(['authReturnTabId'])
      sendResponse({ ok: true })
    })
    return true
  }
  if (!['OPEN_SELECTION_IN_CHAT', 'OPEN_FLOATING_CHAT'].includes(message?.type) || !sender.tab?.id) return
  getBubbleEnabled().then((enabled) => {
    if (enabled) {
      sendResponse({ ok: true, ignored: 'floating-mode-enabled' })
      return
    }
    chrome.sidePanel.open({ tabId: sender.tab.id })
      .then(() => sendResponse({ ok: true }))
      .catch((error) => sendResponse({ ok: false, error: error?.message || 'Không thể mở Side Panel.' }))
  })
  return true
})

const ensureBubbleForTab = async (tab, enabled) => {
  if (!tab?.id || !/^https?:\/\//.test(tab.url || '')) return
  try {
    const response = await chrome.tabs.sendMessage(tab.id, { type: 'SET_CHAT_BUBBLE', enabled })
    if (!response?.ok) throw new Error('Content script chưa sẵn sàng.')
  } catch {
    try {
      await chrome.scripting.insertCSS({ target: { tabId: tab.id }, files: ['content.css'] })
      await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['content.js'] })
      await chrome.tabs.sendMessage(tab.id, { type: 'SET_CHAT_BUBBLE', enabled })
    } catch {
      // Chrome không cho chèn script vào trang hệ thống hoặc trang đặc quyền.
    }
  }
}

const getBubbleEnabled = () => new Promise((resolve) => {
  chrome.storage.local.get(['aiBubbleEnabled'], ({ aiBubbleEnabled }) => resolve(aiBubbleEnabled === true))
})

const getActiveSurface = () => new Promise((resolve) => {
  chrome.storage.local.get(['activeChatSurface', 'activeChatSurfaceAt'], ({ activeChatSurface, activeChatSurfaceAt }) => {
    const isLive = Date.now() - Number(activeChatSurfaceAt || 0) < 5_000
    resolve(isLive && (activeChatSurface === 'native' || activeChatSurface === 'floating') ? activeChatSurface : null)
  })
})

const applyBubbleToOpenTabs = async (enabled) => {
  const tabs = await chrome.tabs.query({})
  await Promise.allSettled(tabs.map((tab) => ensureBubbleForTab(tab, enabled)))
}

chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== 'local' || !changes.aiBubbleEnabled) return
  void applyBubbleToOpenTabs(changes.aiBubbleEnabled.newValue === true)
})

chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  const tab = await chrome.tabs.get(tabId).catch(() => null)
  if (tab) await ensureBubbleForTab(tab, await getBubbleEnabled())
})

chrome.tabs.onUpdated.addListener(async (_tabId, changeInfo, tab) => {
  if (changeInfo.status !== 'complete' || !tab.active) return
  await ensureBubbleForTab(tab, await getBubbleEnabled())
})
