/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface ImportMetaEnv {
  readonly VITE_APP_TITLE: string
  readonly VITE_API_BASE_URL: string
  readonly VITE_WS_BASE_URL: string
  readonly VITE_ELECTRON_ENV: 'development' | 'production'
  readonly VITE_APP_VERSION: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// Electron API 类型声明
interface Window {
  electronAPI: {
    // 窗口控制
    minimizeWindow: () => Promise<void>
    maximizeWindow: () => Promise<void>
    closeWindow: () => Promise<void>
    
    // 系统托盘
    createTray: () => Promise<void>
    showTrayNotification: (title: string, body: string) => Promise<void>
    
    // 文件系统
    selectDirectory: () => Promise<string>
    readFile: (path: string) => Promise<string>
    writeFile: (path: string, content: string) => Promise<void>
    
    // 系统信息
    getPlatform: () => Promise<string>
    getVersion: () => Promise<string>
    
    // 屏幕捕获
    captureScreen: () => Promise<string> // 返回base64图像
    
    // 音频控制
    playAudio: (filePath: string) => Promise<void>
    stopAudio: () => Promise<void>
    
    // 游戏检测
    isGameRunning: (processName: string) => Promise<boolean>
    getActiveWindowTitle: () => Promise<string>
    
    // 配置管理
    getConfig: (key: string) => Promise<any>
    setConfig: (key: string, value: any) => Promise<void>
    
    // 事件监听
    onGameDetected: (callback: (gameName: string) => void) => void
    onScreenCapture: (callback: (imageData: string) => void) => void
    onAudioPlaybackComplete: (callback: () => void) => void
  }
}