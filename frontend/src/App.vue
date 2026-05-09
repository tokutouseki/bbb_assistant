<template>
  <div id="app" class="app-container">
    <!-- 系统托盘区域（仅Electron） -->
    <div v-if="isElectron" class="system-tray-area">
      <SystemTray />
    </div>
    
    <!-- 主路由视图 -->
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
    
    <!-- 全局通知 -->
    <NotificationCenter />
    
    <!-- 全局音频播放器 -->
    <AudioPlayer v-if="audioStore.hasAudio" />
    
    <!-- 游戏覆盖层（在游戏上方显示） -->
    <GameOverlay v-if="gameStore.isGameDetected && settingsStore.showGameOverlay" />
    
    <!-- 全局加载状态 -->
    <div v-if="appStore.isLoading" class="global-loading">
      <div class="loading-spinner">
        <div class="spinner"></div>
        <p class="loading-text">{{ appStore.loadingMessage || '加载中...' }}</p>
      </div>
    </div>
    
    <!-- 开发者工具（仅开发模式） -->
    <DevTools v-if="isDevelopment" />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useGameStore } from '@/stores/game'
import { useAudioStore } from '@/stores/audio'
import { useSettingsStore } from '@/stores/settings'

// 组件导入
import SystemTray from '@/components/features/SystemTray.vue'
import NotificationCenter from '@/components/features/NotificationCenter.vue'
import AudioPlayer from '@/components/features/AudioPlayer.vue'
import GameOverlay from '@/components/features/GameOverlay.vue'
import DevTools from '@/components/features/DevTools.vue'

// 状态管理
const appStore = useAppStore()
const gameStore = useGameStore()
const audioStore = useAudioStore()
const settingsStore = useSettingsStore()

// 计算属性
const isElectron = computed(() => window.electronAPI !== undefined)
const isDevelopment = computed(() => import.meta.env.DEV)

// 生命周期
onMounted(() => {
  console.log('崩坏3专属AI陪伴助手 - 应用启动')
  
  // 初始化应用
  appStore.initialize()
  
  // 如果是Electron环境，设置IPC监听
  if (isElectron.value) {
    setupElectronListeners()
  }
  
  // 连接WebSocket
  connectWebSocket()
  
  // 检查游戏运行状态
  checkGameStatus()
  
  // 加载用户设置
  settingsStore.loadSettings()
})

onUnmounted(() => {
  // 清理工作
  if (isElectron.value) {
    cleanupElectronListeners()
  }
  
  // 断开WebSocket
  disconnectWebSocket()
})

// Electron IPC监听设置
function setupElectronListeners() {
  if (!window.electronAPI) return
  
  // 游戏检测事件
  window.electronAPI.onGameDetected?.((gameName) => {
    gameStore.setGameDetected(true, gameName)
    appStore.showNotification({
      title: '游戏检测',
      message: `检测到 ${gameName} 正在运行`,
      type: 'info'
    })
  })
  
  // 屏幕捕获事件
  window.electronAPI.onScreenCapture?.((imageData) => {
    // 处理屏幕捕获数据
    gameStore.updateScreenCapture(imageData)
  })
  
  // 音频播放完成事件
  window.electronAPI.onAudioPlaybackComplete?.(() => {
    audioStore.clearCurrentAudio()
  })
}

// 清理Electron监听器
function cleanupElectronListeners() {
  // 如果有清理方法，调用它们
}

// 连接WebSocket
function connectWebSocket() {
  const wsUrl = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/ws'
  
  try {
    appStore.connectWebSocket(wsUrl)
  } catch (error) {
    console.error('WebSocket连接失败:', error)
    appStore.showNotification({
      title: '连接错误',
      message: '无法连接到AI服务器',
      type: 'error'
    })
  }
}

// 断开WebSocket
function disconnectWebSocket() {
  appStore.disconnectWebSocket()
}

// 检查游戏状态
function checkGameStatus() {
  if (isElectron.value) {
    window.electronAPI.isGameRunning?.('崩坏3').then((isRunning) => {
      if (isRunning) {
        gameStore.setGameDetected(true, '崩坏3')
      }
    })
  }
}
</script>

<style scoped>
.app-container {
  width: 100vw;
  height: 100vh;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
}

.system-tray-area {
  position: absolute;
  top: 0;
  right: 0;
  z-index: 1000;
  padding: 8px;
}

.global-loading {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.9);
  backdrop-filter: blur(10px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-spinner {
  text-align: center;
}

.spinner {
  width: 60px;
  height: 60px;
  border: 4px solid rgba(236, 72, 153, 0.3);
  border-radius: 50%;
  border-top-color: #ec4899;
  animation: spin 1s ease-in-out infinite;
  margin: 0 auto 20px;
}

.loading-text {
  color: #ec4899;
  font-size: 1.1rem;
  font-weight: 500;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 页面切换动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>