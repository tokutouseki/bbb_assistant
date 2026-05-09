/**
 * 崩坏3专属AI陪伴助手 - Electron主进程
 * 负责窗口管理、系统集成、进程间通信等
 */

import { app, BrowserWindow, ipcMain, shell, Tray, Menu, nativeImage, screen } from 'electron'
import path from 'path'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'
import { autoUpdater } from 'electron-updater'
import log from 'electron-log'

// 配置日志
log.transports.file.level = 'info'
log.transports.console.level = 'debug'

// ES模块兼容性处理
const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// 全局变量
let mainWindow = null
let tray = null
let isGameOverlayVisible = false
let gameMonitorInterval = null
let isDevelopment = process.env.NODE_ENV === 'development'

// 应用配置
const APP_CONFIG = {
  name: '崩坏3专属AI陪伴助手',
  version: app.getVersion(),
  author: '崩坏3助手团队',
  minWidth: 400,
  minHeight: 300,
  defaultWidth: 800,
  defaultHeight: 600,
  gameOverlayWidth: 400,
  gameOverlayHeight: 200,
  gameOverlayOpacity: 0.9,
  trayIconSize: 16,
}

// 创建主窗口
function createMainWindow() {
  log.info('创建主窗口...')
  
  const { width, height } = screen.getPrimaryDisplay().workAreaSize
  
  mainWindow = new BrowserWindow({
    width: APP_CONFIG.defaultWidth,
    height: APP_CONFIG.defaultHeight,
    minWidth: APP_CONFIG.minWidth,
    minHeight: APP_CONFIG.minHeight,
    center: true,
    show: false,
    frame: true,
    titleBarStyle: 'hiddenInset',
    icon: join(__dirname, '../../assets/icons/icon.ico'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: join(__dirname, 'preload.js'),
    },
    backgroundColor: '#1f2937',
  })

  // 加载应用
  if (isDevelopment) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(join(__dirname, '../dist/index.html'))
  }

  // 窗口事件
  mainWindow.on('ready-to-show', () => {
    mainWindow.show()
    log.info('主窗口已显示')
  })

  mainWindow.on('closed', () => {
    mainWindow = null
    log.info('主窗口已关闭')
  })

  // 外部链接在浏览器中打开
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  return mainWindow
}

// 创建游戏覆盖层窗口
function createGameOverlayWindow() {
  log.info('创建游戏覆盖层窗口...')
  
  // 检查游戏窗口是否存在
  const gameWindow = findGameWindow()
  if (!gameWindow) {
    log.warn('未找到游戏窗口，无法创建覆盖层')
    return null
  }

  const { x, y, width, height } = gameWindow.bounds
  
  const overlayWindow = new BrowserWindow({
    x: x + width - APP_CONFIG.gameOverlayWidth - 20,
    y: y + 20,
    width: APP_CONFIG.gameOverlayWidth,
    height: APP_CONFIG.gameOverlayHeight,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    movable: true,
    focusable: false,
    hasShadow: false,
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: join(__dirname, 'preload.js'),
    },
  })

  // 设置窗口透明度
  overlayWindow.setOpacity(APP_CONFIG.gameOverlayOpacity)

  // 加载覆盖层页面
  if (isDevelopment) {
    overlayWindow.loadURL('http://localhost:5173/#/game-overlay')
  } else {
    overlayWindow.loadFile(join(__dirname, '../dist/index.html'), {
      hash: '#/game-overlay',
    })
  }

  overlayWindow.on('ready-to-show', () => {
    overlayWindow.show()
    overlayWindow.setAlwaysOnTop(true, 'screen-saver')
    log.info('游戏覆盖层窗口已显示')
  })

  overlayWindow.on('closed', () => {
    log.info('游戏覆盖层窗口已关闭')
    isGameOverlayVisible = false
  })

  isGameOverlayVisible = true
  return overlayWindow
}

// 创建系统托盘
function createSystemTray() {
  log.info('创建系统托盘...')
  
  const iconPath = join(__dirname, '../../assets/icons/tray-icon.png')
  let trayIcon
  
  try {
    trayIcon = nativeImage.createFromPath(iconPath)
    if (trayIcon.isEmpty()) {
      throw new Error('托盘图标加载失败')
    }
  } catch (error) {
    log.warn('无法加载托盘图标，使用默认图标:', error.message)
    trayIcon = nativeImage.createFromPath(join(__dirname, '../../assets/icons/icon.ico'))
  }

  // 调整图标大小
  trayIcon = trayIcon.resize({
    width: APP_CONFIG.trayIconSize,
    height: APP_CONFIG.trayIconSize,
  })

  tray = new Tray(trayIcon)

  const contextMenu = Menu.buildFromTemplate([
    {
      label: '显示主窗口',
      click: () => {
        if (mainWindow) {
          mainWindow.show()
          mainWindow.focus()
        }
      },
    },
    {
      label: '显示游戏覆盖层',
      type: 'checkbox',
      checked: isGameOverlayVisible,
      click: (menuItem) => {
        if (menuItem.checked) {
          createGameOverlayWindow()
        } else {
          // 关闭所有覆盖层窗口
          BrowserWindow.getAllWindows().forEach((window) => {
            if (window !== mainWindow) {
              window.close()
            }
          })
        }
      },
    },
    { type: 'separator' },
    {
      label: '游戏监控',
      submenu: [
        {
          label: '开始监控',
          click: startGameMonitor,
        },
        {
          label: '停止监控',
          click: stopGameMonitor,
        },
      ],
    },
    { type: 'separator' },
    {
      label: '设置',
      click: () => {
        if (mainWindow) {
          mainWindow.show()
          mainWindow.webContents.send('navigate-to', '/settings')
        }
      },
    },
    {
      label: '关于',
      click: showAboutDialog,
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        app.quit()
      },
    },
  ])

  tray.setToolTip(APP_CONFIG.name)
  tray.setContextMenu(contextMenu)

  // 托盘点击事件
  tray.on('click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.hide()
      } else {
        mainWindow.show()
        mainWindow.focus()
      }
    }
  })

  return tray
}

// 查找游戏窗口
function findGameWindow() {
  const windows = BrowserWindow.getAllWindows()
  for (const window of windows) {
    const title = window.getTitle()
    if (title.includes('崩坏3') || title.includes('Honkai Impact 3rd')) {
      return window
    }
  }
  
  // 尝试使用外部API查找游戏窗口
  // 这里可以集成其他窗口查找库
  return null
}

// 开始游戏监控
function startGameMonitor() {
  log.info('开始游戏监控...')
  
  if (gameMonitorInterval) {
    clearInterval(gameMonitorInterval)
  }
  
  gameMonitorInterval = setInterval(() => {
    const gameWindow = findGameWindow()
    if (gameWindow) {
      // 游戏运行中
      if (mainWindow) {
        mainWindow.webContents.send('game-status', {
          isRunning: true,
          windowTitle: gameWindow.getTitle(),
          timestamp: Date.now(),
        })
      }
      
      // 如果覆盖层未显示，自动显示
      if (!isGameOverlayVisible) {
        const overlayWindow = createGameOverlayWindow()
        if (overlayWindow) {
          overlayWindow.show()
        }
      }
    } else {
      // 游戏未运行
      if (mainWindow) {
        mainWindow.webContents.send('game-status', {
          isRunning: false,
          timestamp: Date.now(),
        })
      }
      
      // 关闭覆盖层窗口
      if (isGameOverlayVisible) {
        BrowserWindow.getAllWindows().forEach((window) => {
          if (window !== mainWindow) {
            window.close()
          }
        })
        isGameOverlayVisible = false
      }
    }
  }, 2000) // 每2秒检查一次
}

// 停止游戏监控
function stopGameMonitor() {
  log.info('停止游戏监控...')
  
  if (gameMonitorInterval) {
    clearInterval(gameMonitorInterval)
    gameMonitorInterval = null
  }
}

// 显示关于对话框
function showAboutDialog() {
  const aboutWindow = new BrowserWindow({
    width: 400,
    height: 300,
    resizable: false,
    minimizable: false,
    maximizable: false,
    modal: true,
    parent: mainWindow,
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  })

  aboutWindow.loadURL(`data:text/html;charset=utf-8,
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <style>
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          padding: 20px;
          background: linear-gradient(135deg, #1f2937, #111827);
          color: #f9fafb;
          text-align: center;
        }
        .logo {
          width: 80px;
          height: 80px;
          margin: 0 auto 20px;
          background: linear-gradient(135deg, #ec4899, #8b5cf6);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 24px;
          font-weight: bold;
          color: white;
        }
        h1 {
          margin: 0 0 10px;
          color: #ec4899;
        }
        .version {
          color: #94a3b8;
          margin-bottom: 20px;
        }
        .info {
          text-align: left;
          margin: 20px 0;
          padding: 15px;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 8px;
        }
        .button {
          background: linear-gradient(135deg, #ec4899, #8b5cf6);
          color: white;
          border: none;
          padding: 10px 20px;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
          margin: 5px;
        }
        .button:hover {
          opacity: 0.9;
        }
      </style>
    </head>
    <body>
      <div class="logo">崩3</div>
      <h1>${APP_CONFIG.name}</h1>
      <div class="version">版本 ${APP_CONFIG.version}</div>
      <div class="info">
        <p>专为崩坏3玩家打造的沉浸式AI陪伴助手</p>
        <p>功能：游戏场景感知、语音交互、角色原声应答、攻略智能查询</p>
        <p>作者：${APP_CONFIG.author}</p>
      </div>
      <button class="button" onclick="window.close()">关闭</button>
    </body>
    </html>
  `)

  aboutWindow.on('ready-to-show', () => {
    aboutWindow.show()
  })
}

// 设置IPC通信
function setupIpcHandlers() {
  log.info('设置IPC处理器...')
  
  // 窗口控制
  ipcMain.handle('window:minimize', () => {
    if (mainWindow) {
      mainWindow.minimize()
    }
  })
  
  ipcMain.handle('window:maximize', () => {
    if (mainWindow) {
      if (mainWindow.isMaximized()) {
        mainWindow.unmaximize()
      } else {
        mainWindow.maximize()
      }
    }
  })
  
  ipcMain.handle('window:close', () => {
    if (mainWindow) {
      mainWindow.close()
    }
  })
  
  // 系统托盘
  ipcMain.handle('tray:create', () => {
    createSystemTray()
  })
  
  ipcMain.handle('tray:show-notification', (event, title, body) => {
    if (tray) {
      tray.displayBalloon({
        title,
        content: body,
        iconType: 'info',
      })
    }
  })
  
  // 文件系统
  ipcMain.handle('fs:select-directory', async () => {
    const { dialog } = await import('electron')
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openDirectory'],
    })
    
    if (!result.canceled && result.filePaths.length > 0) {
      return result.filePaths[0]
    }
    return null
  })
  
  // 系统信息
  ipcMain.handle('system:get-platform', () => {
    return process.platform
  })
  
  ipcMain.handle('system:get-version', () => {
    return APP_CONFIG.version
  })
  
  // 游戏检测
  ipcMain.handle('game:is-running', async (event, processName) => {
    const gameWindow = findGameWindow()
    return !!gameWindow
  })
  
  // 配置管理
  const configStore = new Map()
  
  ipcMain.handle('config:get', (event, key) => {
    return configStore.get(key)
  })
  
  ipcMain.handle('config:set', (event, key, value) => {
    configStore.set(key, value)
    return true
  })
}

// 应用初始化
function initializeApp() {
  log.info(`初始化应用: ${APP_CONFIG.name} v${APP_CONFIG.version}`)
  
  // 设置应用名称
  app.setName(APP_CONFIG.name)
  
  // 单实例锁
  const gotTheLock = app.requestSingleInstanceLock()
  
  if (!gotTheLock) {
    app.quit()
    return
  }
  
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.show()
      mainWindow.focus()
    }
  })
  
  // 应用事件
  app.whenReady().then(() => {
    createMainWindow()
    createSystemTray()
    setupIpcHandlers()
    
    // 自动检查更新（生产环境）
    if (!isDevelopment) {
      autoUpdater.checkForUpdatesAndNotify()
    }
    
    // 开始游戏监控
    startGameMonitor()
  })
  
  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
      app.quit()
    }
  })
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow()
    }
  })
  
  app.on('before-quit', () => {
    stopGameMonitor()
    log.info('应用正在退出...')
  })
  
  // 错误处理
  process.on('uncaughtException', (error) => {
    log.error('未捕获的异常:', error)
    
    // 发送错误到渲染进程
    if (mainWindow) {
      mainWindow.webContents.send('system-error', {
        message: error.message,
        stack: error.stack,
        timestamp: Date.now(),
      })
    }
  })
}

// 启动应用
initializeApp()

// 导出供其他模块使用
export {
  createMainWindow,
  createGameOverlayWindow,
  createSystemTray,
  startGameMonitor,
  stopGameMonitor,
  findGameWindow,
  APP_CONFIG,
}