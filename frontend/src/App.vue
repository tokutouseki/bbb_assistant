<template>
  <div class="app-shell">
    <aside class="sidebar">
      <nav class="sidebar-nav">
        <button
          class="sidebar-btn"
          :class="{ active: currentRoute === 'chat' }"
          @click="navigateToChat"
          title="聊天"
        >
          <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
          </svg>
          <span class="sidebar-label">聊天</span>
        </button>
        <button
          class="sidebar-btn"
          :class="{ active: currentRoute === 'settings' }"
          @click="navigateToSettings"
          title="设置"
        >
          <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>
          </svg>
          <span class="sidebar-label">设置</span>
        </button>
      </nav>
    </aside>
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useChatStore } from '@/stores/chat'

const router = useRouter()
const route = useRoute()
const chatStore = useChatStore()

const currentRoute = computed(() => route.name)

onMounted(() => {
  chatStore.clearMessages()
})

function navigateToChat() {
  router.push({ name: 'chat' })
}

function navigateToSettings() {
  router.push({ name: 'settings' })
}
</script>

<style scoped>
.app-shell {
  display: flex;
  width: 100vw;
  height: 100vh;
  background: #ffffff;
  overflow: hidden;
}

.sidebar {
  width: 64px;
  flex-shrink: 0;
  background: #f5f5f5;
  border-right: 1px solid #333333;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 16px;
  gap: 4px;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  align-items: center;
}

.sidebar-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #666666;
  background: transparent;
  border: none;
  gap: 2px;
}

.sidebar-btn:hover {
  background: #e5e5e5;
  color: #333333;
}

.sidebar-btn.active {
  background: #333333;
  color: #ffffff;
}

.sidebar-icon {
  width: 22px;
  height: 22px;
}

.sidebar-label {
  font-size: 10px;
  font-weight: 500;
  line-height: 1;
}

.main-content {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  background: #ffffff;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
