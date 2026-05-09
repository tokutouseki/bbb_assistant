/**
 * 崩坏3专属AI陪伴助手 - IPC处理器
 * 处理从渲染进程到主进程的IPC通信
 */

import { ipcMain, dialog, shell, clipboard, nativeImage } from 'electron'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'
import log from 'electron-log'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// 配置存储
const configStore = new Map()

/**
 * 注册所有IPC处理器
 */
export function registerIpcHandlers() {
  log.info('注册IPC处理器...')
  
  // 窗口控制处理器
  registerWindowHandlers()
  
  // 文件系统处理器
  registerFileSystemHandlers()
  
  // 系统处理器
  registerSystemHandlers()
  
  // 游戏相关处理器
  registerGameHandlers()
  
  // 音频处理器
  registerAudioHandlers()
  
  // 网络处理器
  registerNetworkHandlers()
  
  // 工具处理器
  registerUtilityHandlers()
  
  log.info('IPC处理器注册完成')
}

/**
 * 窗口控制处理器
 */
function registerWindowHandlers() {
  // 最小化窗口
  ipcMain.handle('window:minimize', (event) => {
    const window = getWindowFromEvent(event)
    if (window) {
      window.minimize()
      return true
    }
    return false
  })
  
  // 最大化/还原窗口
  ipcMain.handle('window:maximize', (event) => {
    const window = getWindowFromEvent(event)
    if (window) {
      if (window.isMaximized()) {
        window.unmaximize()
        return 'restored'
      } else {
        window.maximize()
        return 'maximized'
      }
    }
    return 'error'
  })
  
  // 关闭窗口
  ipcMain.handle('window:close', (event) => {
    const window = getWindowFromEvent(event)
    if (window) {
      window.close()
      return true
    }
    return false
  })
  
  // 设置窗口大小
  ipcMain.handle('window:set-size', (event, width, height) => {
    const window = getWindowFromEvent(event)
    if (window) {
      window.setSize(width, height)
      return true
    }
    return false
  })
  
  // 设置窗口位置
  ipcMain.handle('window:set-position', (event, x, y) => {
    const window = getWindowFromEvent(event)
    if (window) {
      window.setPosition(x, y)
      return true
    }
    return false
  })
  
  // 设置窗口总在最前
  ipcMain.handle('window:set-always-on-top', (event, alwaysOnTop) => {
    const window = getWindowFromEvent(event)
    if (window) {
      window.setAlwaysOnTop(alwaysOnTop)
      return true
    }
    return false
  })
  
  // 设置窗口透明度
  ipcMain.handle('window:set-opacity', (event, opacity) => {
    const window = getWindowFromEvent(event)
    if (window) {
      window.setOpacity(opacity)
      return true
    }
    return false
  })
  
  // 获取窗口信息
  ipcMain.handle('window:get-info', (event) => {
    const window = getWindowFromEvent(event)
    if (window) {
      const bounds = window.getBounds()
      return {
        isMaximized: window.isMaximized(),
        isMinimized: window.isMinimized(),
        isFullScreen: window.isFullScreen(),
        isAlwaysOnTop: window.isAlwaysOnTop(),
        bounds,
        opacity: window.getOpacity(),
      }
    }
    return null
  })
}

/**
 * 文件系统处理器
 */
function registerFileSystemHandlers() {
  // 选择目录
  ipcMain.handle('fs:select-directory', async (event, options = {}) => {
    const window = getWindowFromEvent(event)
    const result = await dialog.showOpenDialog(window, {
      title: options.title || '选择目录',
      buttonLabel: options.buttonLabel || '选择',
      properties: ['openDirectory', 'createDirectory'],
      defaultPath: options.defaultPath,
    })
    
    if (!result.canceled && result.filePaths.length > 0) {
      return result.filePaths[0]
    }
    return null
  })
  
  // 选择文件
  ipcMain.handle('fs:select-file', async (event, options = {}) => {
    const window = getWindowFromEvent(event)
    const result = await dialog.showOpenDialog(window, {
      title: options.title || '选择文件',
      buttonLabel: options.buttonLabel || '选择',
      properties: ['openFile'],
      filters: options.filters || [
        { name: '所有文件', extensions: ['*'] }
      ],
      defaultPath: options.defaultPath,
    })
    
    if (!result.canceled && result.filePaths.length > 0) {
      return result.filePaths[0]
    }
    return null
  })
  
  // 保存文件
  ipcMain.handle('fs:save-file', async (event, options = {}) => {
    const window = getWindowFromEvent(event)
    const result = await dialog.showSaveDialog(window, {
      title: options.title || '保存文件',
      buttonLabel: options.buttonLabel || '保存',
      filters: options.filters || [
        { name: '所有文件', extensions: ['*'] }
      ],
      defaultPath: options.defaultPath,
    })
    
    if (!result.canceled && result.filePath) {
      return result.filePath
    }
    return null
  })
  
  // 读取文件
  ipcMain.handle('fs:read-file', async (event, filePath) => {
    try {
      const content = await fs.promises.readFile(filePath, 'utf-8')
      return content
    } catch (error) {
      log.error('读取文件失败:', error)
      throw new Error(`读取文件失败: ${error.message}`)
    }
  })
  
  // 写入文件
  ipcMain.handle('fs:write-file', async (event, filePath, content) => {
    try {
      await fs.promises.writeFile(filePath, content, 'utf-8')
      return true
    } catch (error) {
      log.error('写入文件失败:', error)
      throw new Error(`写入文件失败: ${error.message}`)
    }
  })
  
  // 检查文件是否存在
  ipcMain.handle('fs:exists', async (event, filePath) => {
    try {
      await fs.promises.access(filePath, fs.constants.F_OK)
      return true
    } catch {
      return false
    }
  })
  
  // 列出目录内容
  ipcMain.handle('fs:list-directory', async (event, dirPath) => {
    try {
      const items = await fs.promises.readdir(dirPath, { withFileTypes: true })
      return items.map(item => ({
        name: item.name,
        path: path.join(dirPath, item.name),
        isDirectory: item.isDirectory(),
        isFile: item.isFile(),
        isSymbolicLink: item.isSymbolicLink(),
      }))
    } catch (error) {
      log.error('列出目录失败:', error)
      throw new Error(`列出目录失败: ${error.message}`)
    }
  })
  
  // 创建目录
  ipcMain.handle('fs:create-directory', async (event, dirPath) => {
    try {
      await fs.promises.mkdir(dirPath, { recursive: true })
      return true
    } catch (error) {
      log.error('创建目录失败:', error)
      throw new Error(`创建目录失败: ${error.message}`)
    }
  })
}

/**
 * 系统处理器
 */
function registerSystemHandlers() {
  // 获取平台信息
  ipcMain.handle('system:get-platform', () => {
    return process.platform
  })
  
  // 获取应用版本
  ipcMain.handle('system:get-version', () => {
    return process.env.npm_package_version || '0.1.0'
  })
  
  // 获取系统信息
  ipcMain.handle('system:get-info', () => {
    return {
      platform: process.platform,
      arch: process.arch,
      version: process.versions,
      memory: process.getSystemMemoryInfo?.(),
      cpu: process.getCPUUsage?.(),
    }
  })
  
  // 打开外部链接
  ipcMain.handle('system:open-external', (event, url) => {
    try {
      shell.openExternal(url)
      return true
    } catch (error) {
      log.error('打开外部链接失败:', error)
      return false
    }
  })
  
  // 打开文件位置
  ipcMain.handle('system:show-item-in-folder', (event, filePath) => {
    try {
      shell.showItemInFolder(filePath)
      return true
    } catch (error) {
      log.error('打开文件位置失败:', error)
      return false
    }
  })
  
  // 复制到剪贴板
  ipcMain.handle('system:copy-to-clipboard', (event, text) => {
    try {
      clipboard.writeText(text)
      return true
    } catch (error) {
      log.error('复制到剪贴板失败:', error)
      return false
    }
  })
  
  // 从剪贴板读取
  ipcMain.handle('system:read-from-clipboard', () => {
    try {
      return clipboard.readText()
    } catch (error) {
      log.error('从剪贴板读取失败:', error)
      return ''
    }
  })
  
  // 复制图片到剪贴板
  ipcMain.handle('system:copy-image-to-clipboard', (event, imagePath) => {
    try {
      const image = nativeImage.createFromPath(imagePath)
      clipboard.writeImage(image)
      return true
    } catch (error) {
      log.error('复制图片到剪贴板失败:', error)
      return false
    }
  })
}

/**
 * 游戏相关处理器
 */
function registerGameHandlers() {
  // 检查游戏是否运行
  ipcMain.handle('game:is-running', async (event, gameName = '崩坏3') => {
    try {
      // 这里需要实现具体的游戏检测逻辑
      // 可以使用外部库如win32api或通过进程名检测
      const { exec } = await import('child_process')
      
      return new Promise((resolve) => {
        if (process.platform === 'win32') {
          // Windows系统使用tasklist命令
          exec('tasklist', (error, stdout) => {
            if (error) {
              log.error('检查游戏进程失败:', error)
              resolve(false)
              return
            }
            
            // 简单检查是否有游戏进程
            const isRunning = stdout.toLowerCase().includes('game') || 
                             stdout.toLowerCase().includes('honkai') ||
                             stdout.toLowerCase().includes('bh3')
            resolve(isRunning)
          })
        } else {
          // 其他系统暂不支持
          resolve(false)
        }
      })
    } catch (error) {
      log.error('游戏检测错误:', error)
      return false
    }
  })
  
  // 获取游戏窗口信息
  ipcMain.handle('game:get-window-info', async () => {
    // 这里需要实现获取游戏窗口信息的逻辑
    // 可以使用外部库如win32api
    return {
      title: '',
      bounds: { x: 0, y: 0, width: 0, height: 0 },
      isForeground: false,
      processId: 0,
    }
  })
  
  // 截取游戏屏幕
  ipcMain.handle('game:capture-screen', async (event) => {
    try {
      const { screen } = await import('electron')
      const displays = screen.getAllDisplays()
      
      if (displays.length === 0) {
        throw new Error('没有找到显示器')
      }
      
      const primaryDisplay = screen.getPrimaryDisplay()
      const { width, height } = primaryDisplay.size
      
      // 这里需要实现具体的屏幕截取逻辑
      // 可以使用外部库如screenshot-desktop
      return {
        success: false,
        message: '屏幕截取功能待实现',
        width,
        height,
        displayCount: displays.length,
      }
    } catch (error) {
      log.error('屏幕截取失败:', error)
      return {
        success: false,
        error: error.message,
      }
    }
  })
  
  // 发送游戏按键
  ipcMain.handle('game:send-key', async (event, key) => {
    // 这里需要实现发送按键的逻辑
    // 可以使用外部库如robotjs
    log.info(`发送游戏按键: ${key}`)
    return true
  })
}

/**
 * 音频处理器
 */
function registerAudioHandlers() {
  // 播放音频
  ipcMain.handle('audio:play', async (event, filePath) => {
    try {
      // 这里需要实现音频播放逻辑
      // 可以使用外部库如play-sound或howler
      log.info(`播放音频: ${filePath}`)
      return { success: true }
    } catch (error) {
      log.error('播放音频失败:', error)
      return { success: false, error: error.message }
    }
  })
  
  // 停止音频
  ipcMain.handle('audio:stop', async () => {
    try {
      log.info('停止音频播放')
      return { success: true }
    } catch (error) {
      log.error('停止音频失败:', error)
      return { success: false, error: error.message }
    }
  })
  
  // 录音
  ipcMain.handle('audio:record', async (event, options = {}) => {
    try {
      // 这里需要实现录音逻辑
      // 可以使用外部库如node-record-lpcm16
      log.info('开始录音', options)
      return { success: true, recordingId: Date.now().toString() }
    } catch (error) {
      log.error('录音失败:', error)
      return { success: false, error: error.message }
    }
  })
  
  // 停止录音
  ipcMain.handle('audio:stop-record', async (event, recordingId) => {
    try {
      log.info(`停止录音: ${recordingId}`)
      return { success: true, filePath: '' }
    } catch (error) {
      log.error('停止录音失败:', error)
      return { success: false, error: error.message }
    }
  })
}

/**
 * 网络处理器
 */
function registerNetworkHandlers() {
  // 检查网络连接
  ipcMain.handle('network:is-online', async () => {
    try {
      // 简单检查网络连接
      const { exec } = await import('child_process')
      
      return new Promise((resolve) => {
        if (process.platform === 'win32') {
          exec('ping -n 1 8.8.8.8', (error) => {
            resolve(!error)
          })
        } else {
          exec('ping -c 1 8.8.8.8', (error) => {
            resolve(!error)
          })
        }
      })
    } catch (error) {
      log.error('检查网络连接失败:', error)
      return false
    }
  })
  
  // 下载文件
  ipcMain.handle('network:download-file', async (event, url, destination) => {
    try {
      const { default: fetch } = await import('node-fetch')
      const response = await fetch(url)
      
      if (!response.ok) {
        throw new Error(`下载失败: ${response.status} ${response.statusText}`)
      }
      
      const buffer = await response.buffer()
      await fs.promises.writeFile(destination, buffer)
      
      return { success: true, size: buffer.length }
    } catch (error) {
      log.error('下载文件失败:', error)
      return { success: false, error: error.message }
    }
  })
}

/**
 * 工具处理器
 */
function registerUtilityHandlers() {
  // 获取配置
  ipcMain.handle('config:get', (event, key) => {
    return configStore.get(key)
  })
  
  // 设置配置
  ipcMain.handle('config:set', (event, key, value) => {
    configStore.set(key, value)
    
    // 持久化配置（可选）
    try {
      const configPath = join(app.getPath('userData'), 'config.json')
      const config = Object.fromEntries(configStore)
      fs.writeFileSync(configPath, JSON.stringify(config, null, 2))
    } catch (error) {
      log.error('保存配置失败:', error)
    }
    
    return true
  })
  
  // 删除配置
  ipcMain.handle('config:delete', (event, key) => {
    return configStore.delete(key)
  })
  
  // 获取所有配置
  ipcMain.handle('config:get-all', () => {
    return Object.fromEntries(configStore)
  })
  
  // 重置配置
  ipcMain.handle('config:reset', () => {
    configStore.clear()
    return true
  })
  
  // 显示对话框
  ipcMain.handle('dialog:show', async (event, options) => {
    const window = getWindowFromEvent(event)
    
    switch (options.type) {
      case 'info':
        return await dialog.showMessageBox(window, {
          type: 'info',
          title: options.title || '提示',
          message: options.message,
          buttons: options.buttons || ['确定'],
        })
        
      case 'warning':
        return await dialog.showMessageBox(window, {
          type: 'warning',
          title: options.title || '警告',
          message: options.message,
          buttons: options.buttons || ['确定'],
        })
        
      case 'error':
        return await dialog.showMessageBox(window, {
          type: 'error',
          title: options.title || '错误',
          message: options.message,
          buttons: options.buttons || ['确定'],
        })
        
      case 'question':
        return await dialog.showMessageBox(window, {
          type: 'question',
          title: options.title || '确认',
          message: options.message,
          buttons: options.buttons || ['是', '否'],
        })
        
      default:
        throw new Error(`未知的对话框类型: ${options.type}`)
    }
  })
}

/**
 * 工具函数：从事件获取窗口
 */
function getWindowFromEvent(event) {
  return event.sender.getOwnerBrowserWindow()
}

// 导出
export default {
  registerIpcHandlers,
  configStore,
}