import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/**
 * 应用全局状态管理
 * 管理应用级状态：加载状态、错误处理、通知、WebSocket连接等
 */
export const useAppStore = defineStore('app', () => {
  // 状态定义
  const isLoading = ref(false)
  const loadingMessage = ref('')
  const notifications = ref([])
  const errors = ref([])
  const navigationHistory = ref([])
  const websocket = ref(null)
  const websocketConnected = ref(false)
  const appVersion = ref(import.meta.env.VITE_APP_VERSION || '0.1.0')
  const isElectron = ref(typeof window.electronAPI !== 'undefined')
  const isDevelopment = ref(import.meta.env.DEV)
  
  // 计算属性
  const hasNotifications = computed(() => notifications.value.length > 0)
  const hasErrors = computed(() => errors.value.length > 0)
  const unreadNotificationCount = computed(() => 
    notifications.value.filter(n => !n.read).length
  )
  const latestError = computed(() => 
    errors.value.length > 0 ? errors.value[errors.value.length - 1] : null
  )
  const isOnline = computed(() => websocketConnected.value)
  const canConnectToBackend = computed(() => {
    // 检查后端连接状态
    return websocketConnected.value || isDevelopment.value
  })
  
  // 操作方法
  function setLoading(loading, message = '') {
    isLoading.value = loading
    loadingMessage.value = message
    
    if (loading && window.electronAPI) {
      window.electronAPI.setLoading?.(true, message)
    } else if (!loading && window.electronAPI) {
      window.electronAPI.setLoading?.(false)
    }
  }
  
  function showNotification(notification) {
    const id = Date.now().toString()
    const fullNotification = {
      id,
      title: notification.title,
      message: notification.message,
      type: notification.type || 'info', // info, success, warning, error
      duration: notification.duration || 5000,
      read: false,
      timestamp: new Date().toISOString(),
      ...notification
    }
    
    notifications.value.unshift(fullNotification)
    
    // 限制通知数量
    if (notifications.value.length > 50) {
      notifications.value = notifications.value.slice(0, 50)
    }
    
    // 自动移除
    if (fullNotification.duration > 0) {
      setTimeout(() => {
        removeNotification(id)
      }, fullNotification.duration)
    }
    
    // 发送到Electron（如果有）
    if (window.electronAPI && notification.showInTray !== false) {
      window.electronAPI.showTrayNotification?.(
        fullNotification.title,
        fullNotification.message
      )
    }
    
    return id
  }
  
  function removeNotification(id) {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index !== -1) {
      notifications.value.splice(index, 1)
    }
  }
  
  function markNotificationAsRead(id) {
    const notification = notifications.value.find(n => n.id === id)
    if (notification) {
      notification.read = true
    }
  }
  
  function clearAllNotifications() {
    notifications.value = []
  }
  
  function addError(error) {
    const errorObj = {
      id: Date.now().toString(),
      message: error.message || '未知错误',
      stack: error.stack,
      component: error.component,
      timestamp: new Date().toISOString(),
      metadata: error.metadata || {}
    }
    
    errors.value.unshift(errorObj)
    
    // 限制错误数量
    if (errors.value.length > 100) {
      errors.value = errors.value.slice(0, 100)
    }
    
    // 发送到后端日志
    logErrorToBackend(errorObj)
    
    return errorObj.id
  }
  
  function clearError(id) {
    const index = errors.value.findIndex(e => e.id === id)
    if (index !== -1) {
      errors.value.splice(index, 1)
    }
  }
  
  function clearAllErrors() {
    errors.value = []
  }
  
  function addNavigationHistory(entry) {
    navigationHistory.value.unshift(entry)
    
    // 限制历史记录数量
    if (navigationHistory.value.length > 100) {
      navigationHistory.value = navigationHistory.value.slice(0, 100)
    }
  }
  
  function clearNavigationHistory() {
    navigationHistory.value = []
  }
  
  function connectWebSocket(url) {
    if (websocket.value && websocketConnected.value) {
      console.log('WebSocket已连接，跳过重新连接')
      return
    }
    
    try {
      const ws = new WebSocket(url)
      
      ws.onopen = () => {
        websocketConnected.value = true
        showNotification({
          title: '连接成功',
          message: '已连接到AI服务器',
          type: 'success',
          duration: 3000
        })
        console.log('WebSocket连接已建立:', url)
      }
      
      ws.onclose = () => {
        websocketConnected.value = false
        websocket.value = null
        
        // 如果不是手动关闭，尝试重连
        if (!isDevelopment.value) {
          setTimeout(() => {
            showNotification({
              title: '连接断开',
              message: '正在尝试重新连接...',
              type: 'warning',
              duration: 3000
            })
            connectWebSocket(url)
          }, 5000)
        }
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket错误:', error)
        addError({
          message: 'WebSocket连接错误',
          metadata: { url, error }
        })
      }
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          handleWebSocketMessage(data)
        } catch (error) {
          console.error('WebSocket消息解析错误:', error, event.data)
        }
      }
      
      websocket.value = ws
    } catch (error) {
      console.error('WebSocket连接失败:', error)
      addError({
        message: 'WebSocket连接失败',
        metadata: { url, error: error.message }
      })
    }
  }
  
  function disconnectWebSocket() {
    if (websocket.value) {
      websocket.value.close()
      websocket.value = null
      websocketConnected.value = false
    }
  }
  
  function sendWebSocketMessage(message) {
    if (websocket.value && websocketConnected.value) {
      try {
        const messageStr = typeof message === 'string' ? message : JSON.stringify(message)
        websocket.value.send(messageStr)
        return true
      } catch (error) {
        console.error('发送WebSocket消息失败:', error)
        addError({
          message: '发送消息失败',
          metadata: { message, error: error.message }
        })
        return false
      }
    } else {
      console.warn('WebSocket未连接，无法发送消息')
      return false
    }
  }
  
  function handleWebSocketMessage(data) {
    // 根据消息类型分发处理
    switch (data.type) {
      case 'chat_response':
        // 聊天响应，由chatStore处理
        break
      case 'game_status':
        // 游戏状态更新，由gameStore处理
        break
      case 'system_notification':
        showNotification({
          title: data.title || '系统通知',
          message: data.message,
          type: data.notification_type || 'info',
          duration: data.duration || 5000
        })
        break
      case 'error':
        addError({
          message: data.message || '服务器错误',
          metadata: data.metadata
        })
        break
      case 'ping':
        // 响应ping
        sendWebSocketMessage({ type: 'pong', timestamp: Date.now() })
        break
      default:
        console.log('未知WebSocket消息类型:', data.type, data)
    }
  }
  
  function logErrorToBackend(error) {
    // 发送错误到后端日志服务
    if (window.electronAPI) {
      window.electronAPI.sendErrorLog?.(error)
    }
    
    // 如果是生产环境，可以发送到远程错误追踪服务
    if (!isDevelopment.value) {
      // 这里可以集成Sentry、Bugsnag等
    }
  }
  
  function initialize() {
    console.log('初始化应用状态')
    
    // 检查Electron API
    if (isElectron.value) {
      console.log('运行在Electron环境中')
    } else {
      console.log('运行在浏览器环境中')
    }
    
    // 显示欢迎通知
    showNotification({
      title: '欢迎使用崩坏3专属AI陪伴助手',
      message: `版本 ${appVersion.value} 已启动`,
      type: 'info',
      duration: 3000
    })
  }
  
  // 导出状态和方法
  return {
    // 状态
    isLoading,
    loadingMessage,
    notifications,
    errors,
    navigationHistory,
    websocket,
    websocketConnected,
    appVersion,
    isElectron,
    isDevelopment,
    
    // 计算属性
    hasNotifications,
    hasErrors,
    unreadNotificationCount,
    latestError,
    isOnline,
    canConnectToBackend,
    
    // 方法
    setLoading,
    showNotification,
    removeNotification,
    markNotificationAsRead,
    clearAllNotifications,
    addError,
    clearError,
    clearAllErrors,
    addNavigationHistory,
    clearNavigationHistory,
    connectWebSocket,
    disconnectWebSocket,
    sendWebSocketMessage,
    handleWebSocketMessage,
    initialize
  }
})