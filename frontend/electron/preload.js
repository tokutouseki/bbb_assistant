/**
 * 崩坏3专属AI陪伴助手 - Electron预加载脚本
 * 在渲染进程和主进程之间提供安全的桥梁
 */

const { contextBridge, ipcRenderer } = require('electron')

// 安全的API暴露给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  // 窗口控制
  minimizeWindow: () => ipcRenderer.invoke('window:minimize'),
  maximizeWindow: () => ipcRenderer.invoke('window:maximize'),
  closeWindow: () => ipcRenderer.invoke('window:close'),
  
  // 系统托盘
  createTray: () => ipcRenderer.invoke('tray:create'),
  showTrayNotification: (title, body) => ipcRenderer.invoke('tray:show-notification', title, body),
  
  // 文件系统
  selectDirectory: () => ipcRenderer.invoke('fs:select-directory'),
  
  // 系统信息
  getPlatform: () => ipcRenderer.invoke('system:get-platform'),
  getVersion: () => ipcRenderer.invoke('system:get-version'),
  
  // 游戏检测
  isGameRunning: (processName) => ipcRenderer.invoke('game:is-running', processName),
  
  // 配置管理
  getConfig: (key) => ipcRenderer.invoke('config:get', key),
  setConfig: (key, value) => ipcRenderer.invoke('config:set', key, value),
  
  // 事件监听（从主进程到渲染进程）
  onGameDetected: (callback) => {
    ipcRenderer.on('game-status', (event, data) => {
      if (data.isRunning) {
        callback(data.windowTitle)
      }
    })
  },
  
  onScreenCapture: (callback) => {
    ipcRenderer.on('screen-capture', (event, imageData) => {
      callback(imageData)
    })
  },
  
  onSystemError: (callback) => {
    ipcRenderer.on('system-error', (event, error) => {
      callback(error)
    })
  },
  
  onNavigateTo: (callback) => {
    ipcRenderer.on('navigate-to', (event, path) => {
      callback(path)
    })
  },
  
  // 移除事件监听器
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel)
  }
})

// 开发工具支持
if (process.env.NODE_ENV === 'development') {
  contextBridge.exposeInMainWorld('devTools', {
    open: () => {
      try {
        require('electron').remote.getCurrentWindow().webContents.openDevTools()
      } catch (error) {
        console.warn('无法打开开发者工具:', error)
      }
    },
    
    reload: () => {
      try {
        require('electron').remote.getCurrentWindow().reload()
      } catch (error) {
        console.warn('无法重新加载窗口:', error)
      }
    },
    
    getNodeVersion: () => process.versions.node,
    getChromeVersion: () => process.versions.chrome,
    getElectronVersion: () => process.versions.electron,
  })
}

// 性能监控
if (process.env.NODE_ENV === 'development') {
  const performanceMetrics = {
    startTime: Date.now(),
    memoryUsage: {},
    fps: 0,
    lastFrameTime: 0,
    frameCount: 0,
  }
  
  // 监控内存使用
  setInterval(() => {
    try {
      const memory = process.getProcessMemoryInfo()
      performanceMetrics.memoryUsage = memory
      
      // 发送到主进程（可选）
      ipcRenderer.send('performance-metrics', {
        memory,
        uptime: Date.now() - performanceMetrics.startTime,
        fps: performanceMetrics.fps,
      })
    } catch (error) {
      // 忽略权限错误
    }
  }, 5000)
  
  // FPS计算
  function calculateFPS() {
    const now = Date.now()
    const delta = now - performanceMetrics.lastFrameTime
    
    if (performanceMetrics.lastFrameTime > 0) {
      performanceMetrics.frameCount++
      
      if (delta >= 1000) {
        performanceMetrics.fps = Math.round((performanceMetrics.frameCount * 1000) / delta)
        performanceMetrics.frameCount = 0
        performanceMetrics.lastFrameTime = now
      }
    } else {
      performanceMetrics.lastFrameTime = now
    }
    
    requestAnimationFrame(calculateFPS)
  }
  
  // 开始FPS计算
  requestAnimationFrame(calculateFPS)
  
  // 暴露性能数据给渲染进程
  contextBridge.exposeInMainWorld('performance', {
    getMetrics: () => performanceMetrics,
    getFPS: () => performanceMetrics.fps,
    getMemoryUsage: () => performanceMetrics.memoryUsage,
    getUptime: () => Date.now() - performanceMetrics.startTime,
  })
}

// 安全警告
console.log(`
==========================================
崩坏3专属AI陪伴助手 - 安全提示
==========================================
此应用运行在受保护的Electron环境中。
请勿在控制台中输入任何敏感信息。
开发模式已启用额外调试功能。
==========================================
`)