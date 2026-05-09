import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electronAPI', {
  minimizeWindow: () => ipcRenderer.invoke('window:minimize'),
  maximizeWindow: () => ipcRenderer.invoke('window:maximize'),
  closeWindow: () => ipcRenderer.invoke('window:close'),
  createTray: () => ipcRenderer.invoke('tray:create'),
  showTrayNotification: (title, body) => ipcRenderer.invoke('tray:show-notification', title, body),
  selectDirectory: () => ipcRenderer.invoke('fs:select-directory'),
  getPlatform: () => ipcRenderer.invoke('system:get-platform'),
  getVersion: () => ipcRenderer.invoke('system:get-version'),
  isGameRunning: (processName) => ipcRenderer.invoke('game:is-running', processName),
  getConfig: (key) => ipcRenderer.invoke('config:get', key),
  setConfig: (key, value) => ipcRenderer.invoke('config:set', key, value),

  onGameDetected: (callback) => {
    ipcRenderer.on('game-status', (_event, data) => {
      if (data && data.isRunning) callback(data.windowTitle)
    })
  },
  onScreenCapture: (callback) => {
    ipcRenderer.on('screen-capture', (_event, imageData) => callback(imageData))
  },
  onSystemError: (callback) => {
    ipcRenderer.on('system-error', (_event, error) => callback(error))
  },
  onNavigateTo: (callback) => {
    ipcRenderer.on('navigate-to', (_event, path) => callback(path))
  },
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel)
  },
  onAudioPlaybackComplete: (callback) => {
    ipcRenderer.on('audio-playback-complete', () => callback())
  },
  sendErrorLog: (error) => {
    ipcRenderer.send('error-log', error)
  },
  sendAnalyticsEvent: (event) => {
    ipcRenderer.send('analytics-event', event)
  },
  setLoading: (loading, message) => {
    ipcRenderer.send('loading-state', { loading, message })
  },
  setOverlayMode: (enabled) => {
    ipcRenderer.send('overlay-mode', enabled)
  }
})
