/**
 * 崩坏3专属AI陪伴助手 - Electron主进程
 * 负责窗口管理、系统集成、进程间通信等
 */

import { app, BrowserWindow, ipcMain, shell, Tray, Menu, nativeImage, screen } from 'electron'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const { join } = path

let mainWindow = null
let tray = null
let isGameOverlayVisible = false
let gameMonitorInterval = null
let isDevelopment = process.env.NODE_ENV === 'development' || !!process.env.VITE_DEV_SERVER_URL || !app.isPackaged

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

function createMainWindow() {
  console.log('创建主窗口...')

  mainWindow = new BrowserWindow({
    width: APP_CONFIG.defaultWidth,
    height: APP_CONFIG.defaultHeight,
    minWidth: APP_CONFIG.minWidth,
    minHeight: APP_CONFIG.minHeight,
    center: true,
    show: false,
    frame: true,
    icon: join(__dirname, '../../assets/icons/icon.ico'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: join(__dirname, 'preload.mjs'),
    },
    backgroundColor: '#ffffff',
  })

  if (isDevelopment) {
    mainWindow.loadURL('http://localhost:5173')
  } else {
    mainWindow.loadFile(join(__dirname, '../dist/index.html'))
  }

  mainWindow.on('ready-to-show', () => {
    mainWindow.show()
    console.log('主窗口已显示')
  })

  mainWindow.on('closed', () => {
    mainWindow = null
    console.log('主窗口已关闭')
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  return mainWindow
}

function createGameOverlayWindow() {
  console.log('创建游戏覆盖层窗口...')

  const gameWindow = findGameWindow()
  if (!gameWindow || !gameWindow.bounds) {
    console.warn('未找到游戏窗口，无法创建覆盖层')
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
      preload: join(__dirname, 'preload.mjs'),
    },
  })

  overlayWindow.setOpacity(APP_CONFIG.gameOverlayOpacity)

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
    console.log('游戏覆盖层窗口已显示')
  })

  overlayWindow.on('closed', () => {
    console.log('游戏覆盖层窗口已关闭')
    isGameOverlayVisible = false
  })

  isGameOverlayVisible = true
  return overlayWindow
}

function createSystemTray() {
  try {
    console.log('创建系统托盘...')
    const iconPath = join(__dirname, '../../assets/icons/icon.ico')
    const trayIcon = nativeImage.createFromPath(iconPath)

    if (trayIcon.isEmpty()) {
      console.warn('托盘图标为空，跳过创建')
      return null
    }

    const resizedIcon = trayIcon.resize({ width: 16, height: 16 })
    tray = new Tray(resizedIcon)

    const contextMenu = Menu.buildFromTemplate([
      {
        label: '显示主窗口',
        click: () => { if (mainWindow) { mainWindow.show(); mainWindow.focus() } },
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
      { label: '关于', click: showAboutDialog },
      { type: 'separator' },
      { label: '退出', click: () => { app.quit() } },
    ])

    tray.setToolTip(APP_CONFIG.name)
    tray.setContextMenu(contextMenu)

    tray.on('click', () => {
      if (mainWindow) {
        if (mainWindow.isVisible()) mainWindow.hide()
        else { mainWindow.show(); mainWindow.focus() }
      }
    })

    return tray
  } catch (error) {
    console.warn('创建托盘失败:', error.message)
    return null
  }
}

function findGameWindow() {
  const windows = BrowserWindow.getAllWindows()
  for (const window of windows) {
    const title = window.getTitle()
    if (title.includes('崩坏3') || title.includes('Honkai Impact 3rd')) {
      return window
    }
  }
  return null
}

function startGameMonitor() {
  console.log('开始游戏监控...')

  if (gameMonitorInterval) {
    clearInterval(gameMonitorInterval)
  }

  gameMonitorInterval = setInterval(() => {
    const gameWindow = findGameWindow()
    if (gameWindow) {
      if (mainWindow) {
        mainWindow.webContents.send('game-status', {
          isRunning: true,
          windowTitle: gameWindow.getTitle(),
          timestamp: Date.now(),
        })
      }
      if (!isGameOverlayVisible) {
        const overlayWindow = createGameOverlayWindow()
        if (overlayWindow) {
          overlayWindow.show()
        }
      }
    } else {
      if (mainWindow) {
        mainWindow.webContents.send('game-status', {
          isRunning: false,
          timestamp: Date.now(),
        })
      }
      if (isGameOverlayVisible) {
        BrowserWindow.getAllWindows().forEach((window) => {
          if (window !== mainWindow) {
            window.close()
          }
        })
        isGameOverlayVisible = false
      }
    }
  }, 2000)
}

function stopGameMonitor() {
  console.log('停止游戏监控...')

  if (gameMonitorInterval) {
    clearInterval(gameMonitorInterval)
    gameMonitorInterval = null
  }
}

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
          background: linear-gradient(135deg, #ffffff, #f0f0f0);
          color: #1a1a1a;
          text-align: center;
        }
        .logo {
          width: 80px;
          height: 80px;
          margin: 0 auto 20px;
          background: linear-gradient(135deg, #f472b6, #8b5cf6);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 24px;
          font-weight: bold;
          color: white;
        }
        h1 { margin: 0 0 10px; color: #333; }
        .version { color: #999; margin-bottom: 20px; }
        .info {
          text-align: left;
          margin: 20px 0;
          padding: 15px;
          background: #f5f5f5;
          border-radius: 8px;
          font-size: 14px;
        }
        .button {
          background: #333;
          color: white;
          border: none;
          padding: 10px 20px;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
        }
        .button:hover { background: #555; }
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

function setupIpcHandlers() {
  console.log('设置IPC处理器...')

  ipcMain.handle('window:minimize', () => {
    if (mainWindow) mainWindow.minimize()
  })

  ipcMain.handle('window:maximize', () => {
    if (mainWindow) {
      if (mainWindow.isMaximized()) mainWindow.unmaximize()
      else mainWindow.maximize()
    }
  })

  ipcMain.handle('window:close', () => {
    if (mainWindow) mainWindow.close()
  })

  ipcMain.handle('tray:create', () => {
    createSystemTray()
  })

  ipcMain.handle('tray:show-notification', (event, title, body) => {
    if (tray) {
      tray.displayBalloon({ title, content: body, iconType: 'info' })
    }
  })

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

  ipcMain.handle('system:get-platform', () => process.platform)
  ipcMain.handle('system:get-version', () => APP_CONFIG.version)

  ipcMain.handle('game:is-running', () => {
    return !!findGameWindow()
  })

  const configStore = new Map()

  ipcMain.handle('config:get', (event, key) => configStore.get(key))
  ipcMain.handle('config:set', (event, key, value) => {
    configStore.set(key, value)
    return true
  })
}

function initializeApp() {
  console.log(`初始化应用: ${APP_CONFIG.name} v${APP_CONFIG.version}`)

  app.setName(APP_CONFIG.name)

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

  app.whenReady().then(() => {
    Menu.setApplicationMenu(null)
    createMainWindow()
    createSystemTray()
    setupIpcHandlers()
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
    console.log('应用正在退出...')
  })

  process.on('uncaughtException', (error) => {
    console.error('未捕获的异常:', error)
    if (mainWindow) {
      mainWindow.webContents.send('system-error', {
        message: error.message,
        stack: error.stack,
        timestamp: Date.now(),
      })
    }
  })
}

initializeApp()

export {
  createMainWindow,
  createGameOverlayWindow,
  createSystemTray,
  startGameMonitor,
  stopGameMonitor,
  findGameWindow,
  APP_CONFIG,
}
