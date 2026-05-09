import { createRouter, createWebHistory } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useGameStore } from '@/stores/game'

// 路由组件
const HomeView = () => import('@/views/HomeView.vue')
const ChatView = () => import('@/views/ChatView.vue')
const SettingsView = () => import('@/views/SettingsView.vue')
const DashboardView = () => import('@/views/DashboardView.vue')
const GameOverlayView = () => import('@/views/GameOverlayView.vue')
const CharacterSelectView = () => import('@/views/CharacterSelectView.vue')
const KnowledgeBaseView = () => import('@/views/KnowledgeBaseView.vue')
const MemoryView = () => import('@/views/MemoryView.vue')
const NotFoundView = () => import('@/views/NotFoundView.vue')

// 路由配置
const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView,
    meta: {
      title: '首页 - 崩坏3专属AI陪伴助手',
      requiresAuth: false,
      showInNav: true,
      icon: 'home',
      description: '应用主页，显示概览信息'
    }
  },
  {
    path: '/chat',
    name: 'chat',
    component: ChatView,
    meta: {
      title: 'AI对话 - 崩坏3专属AI陪伴助手',
      requiresAuth: false,
      showInNav: true,
      icon: 'message-square',
      description: '与AI助手进行文字或语音对话'
    }
  },
  {
    path: '/settings',
    name: 'settings',
    component: SettingsView,
    meta: {
      title: '设置 - 崩坏3专属AI陪伴助手',
      requiresAuth: false,
      showInNav: true,
      icon: 'settings',
      description: '应用设置和配置管理'
    }
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: DashboardView,
    meta: {
      title: '仪表盘 - 崩坏3专属AI陪伴助手',
      requiresAuth: false,
      showInNav: true,
      icon: 'bar-chart',
      description: '数据统计和系统监控'
    }
  },
  {
    path: '/game-overlay',
    name: 'game-overlay',
    component: GameOverlayView,
    meta: {
      title: '游戏覆盖层',
      requiresAuth: false,
      showInNav: false,
      overlay: true,
      description: '在游戏上方显示的覆盖层界面'
    }
  },
  {
    path: '/character',
    name: 'character-select',
    component: CharacterSelectView,
    meta: {
      title: '角色选择 - 崩坏3专属AI陪伴助手',
      requiresAuth: false,
      showInNav: true,
      icon: 'users',
      description: '选择AI陪伴的角色和语音'
    }
  },
  {
    path: '/knowledge',
    name: 'knowledge-base',
    component: KnowledgeBaseView,
    meta: {
      title: '知识库 - 崩坏3专属AI陪伴助手',
      requiresAuth: false,
      showInNav: true,
      icon: 'book-open',
      description: '崩坏3游戏攻略和知识库'
    }
  },
  {
    path: '/memory',
    name: 'memory',
    component: MemoryView,
    meta: {
      title: '对话记忆 - 崩坏3专属AI陪伴助手',
      requiresAuth: false,
      showInNav: true,
      icon: 'database',
      description: '查看和管理对话历史记录'
    }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: NotFoundView,
    meta: {
      title: '页面未找到 - 崩坏3专属AI陪伴助手',
      requiresAuth: false,
      showInNav: false
    }
  }
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// 全局前置守卫
router.beforeEach((to, from, next) => {
  const appStore = useAppStore()
  const gameStore = useGameStore()
  
  // 设置页面标题
  if (to.meta.title) {
    document.title = to.meta.title
  }
  
  // 检查是否需要身份验证
  if (to.meta.requiresAuth && !appStore.isAuthenticated) {
    // 重定向到登录页
    next({ name: 'home' })
    return
  }
  
  // 检查是否是游戏覆盖层路由
  if (to.meta.overlay && !gameStore.isGameDetected) {
    // 如果没有检测到游戏，重定向到主页
    next({ name: 'home' })
    return
  }
  
  // 记录路由跳转
  appStore.addNavigationHistory({
    from: from.fullPath,
    to: to.fullPath,
    timestamp: new Date().toISOString()
  })
  
  // 显示加载状态
  appStore.setLoading(true, `正在加载${to.meta.title || '页面'}...`)
  
  next()
})

// 全局后置守卫
router.afterEach((to, from) => {
  const appStore = useAppStore()
  
  // 隐藏加载状态
  appStore.setLoading(false)
  
  // 发送页面浏览事件
  if (window.electronAPI) {
    window.electronAPI.sendAnalyticsEvent?.({
      type: 'page_view',
      page: to.fullPath,
      title: to.meta.title,
      timestamp: new Date().toISOString()
    })
  }
  
  // 如果是游戏覆盖层，调整窗口
  if (to.meta.overlay && window.electronAPI) {
    window.electronAPI.setOverlayMode?.(true)
  } else if (from.meta.overlay && window.electronAPI) {
    window.electronAPI.setOverlayMode?.(false)
  }
})

// 路由错误处理
router.onError((error) => {
  console.error('路由错误:', error)
  
  const appStore = useAppStore()
  appStore.showNotification({
    title: '页面加载失败',
    message: '无法加载请求的页面，请稍后重试',
    type: 'error'
  })
})

// 导出路由实例
export default router

// 导出路由工具函数
export function getRouteByName(name) {
  return router.getRoutes().find(route => route.name === name)
}

export function getNavRoutes() {
  return router.getRoutes().filter(route => route.meta.showInNav)
}

export function isCurrentRoute(routeName) {
  return router.currentRoute.value.name === routeName
}

export function navigateTo(name, params = {}, query = {}) {
  return router.push({ name, params, query })
}

export function navigateBack() {
  return router.go(-1)
}

export function navigateForward() {
  return router.go(1)
}

export function replaceRoute(name, params = {}, query = {}) {
  return router.replace({ name, params, query })
}