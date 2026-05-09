// Pinia Store 统一导出
// 崩坏3专属AI陪伴助手 - 状态管理

import { createPinia } from 'pinia'
import { useAppStore } from './app'
import { useGameStore } from './game'
import { useChatStore } from './chat'
import { useAudioStore } from './audio'
import { useSettingsStore } from './settings'
import { useMemoryStore } from './memory'
import { useCharacterStore } from './character'
import { useKnowledgeStore } from './knowledge'

// 创建Pinia实例
const pinia = createPinia()

// 插件：状态持久化
pinia.use(({ store }) => {
  // 从localStorage加载状态
  const savedState = localStorage.getItem(`bbb-assistant-${store.$id}`)
  if (savedState) {
    try {
      store.$patch(JSON.parse(savedState))
    } catch (error) {
      console.warn(`Failed to load state for store ${store.$id}:`, error)
    }
  }
  
  // 保存状态到localStorage
  store.$subscribe((mutation, state) => {
    try {
      localStorage.setItem(`bbb-assistant-${store.$id}`, JSON.stringify(state))
    } catch (error) {
      console.warn(`Failed to save state for store ${store.$id}:`, error)
    }
  })
})

// 插件：状态重置
pinia.use(({ store }) => {
  // 添加重置方法
  store.$reset = () => {
    const initialState = {}
    for (const key in store.$state) {
      initialState[key] = typeof store.$state[key] === 'object' && store.$state[key] !== null
        ? (Array.isArray(store.$state[key]) ? [] : {})
        : store.$state[key]
    }
    store.$patch(initialState)
  }
})

// 导出Pinia实例
export default pinia

// 导出所有store
export {
  useAppStore,
  useGameStore,
  useChatStore,
  useAudioStore,
  useSettingsStore,
  useMemoryStore,
  useCharacterStore,
  useKnowledgeStore
}

// 导出工具函数
export function resetAllStores() {
  const stores = [
    useAppStore(),
    useGameStore(),
    useChatStore(),
    useAudioStore(),
    useSettingsStore(),
    useMemoryStore(),
    useCharacterStore(),
    useKnowledgeStore()
  ]
  
  stores.forEach(store => {
    if (store.$reset) {
      store.$reset()
    }
  })
  
  // 清空localStorage
  Object.keys(localStorage).forEach(key => {
    if (key.startsWith('bbb-assistant-')) {
      localStorage.removeItem(key)
    }
  })
  
  console.log('所有状态已重置')
}

export function getStoreSnapshot() {
  const stores = [
    useAppStore(),
    useGameStore(),
    useChatStore(),
    useAudioStore(),
    useSettingsStore(),
    useMemoryStore(),
    useCharacterStore(),
    useKnowledgeStore()
  ]
  
  const snapshot = {}
  stores.forEach(store => {
    snapshot[store.$id] = store.$state
  })
  
  return snapshot
}

export function restoreStoreSnapshot(snapshot) {
  Object.entries(snapshot).forEach(([storeId, state]) => {
    const storeMap = {
      'app': useAppStore,
      'game': useGameStore,
      'chat': useChatStore,
      'audio': useAudioStore,
      'settings': useSettingsStore,
      'memory': useMemoryStore,
      'character': useCharacterStore,
      'knowledge': useKnowledgeStore
    }
    
    const storeCreator = storeMap[storeId]
    if (storeCreator) {
      const store = storeCreator()
      store.$patch(state)
    }
  })
}

// 开发工具
if (import.meta.env.DEV) {
  // 将store添加到全局对象，方便调试
  window.__BBB_STORES__ = {
    useAppStore,
    useGameStore,
    useChatStore,
    useAudioStore,
    useSettingsStore,
    useMemoryStore,
    useCharacterStore,
    useKnowledgeStore,
    resetAllStores,
    getStoreSnapshot,
    restoreStoreSnapshot
  }
  
  console.log('崩坏3专属AI陪伴助手 - Store已加载到全局对象 window.__BBB_STORES__')
}