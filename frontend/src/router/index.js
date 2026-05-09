import { createRouter, createWebHashHistory } from 'vue-router'

const ChatView = () => import('@/views/ChatView.vue')
const SettingsView = () => import('@/views/SettingsView.vue')

const routes = [
  {
    path: '/',
    name: 'chat',
    component: ChatView,
    meta: {
      title: 'AI对话 - 崩坏3专属AI陪伴助手'
    }
  },
  {
    path: '/settings',
    name: 'settings',
    component: SettingsView,
    meta: {
      title: '设置 - 崩坏3专属AI陪伴助手'
    }
  }
]

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

router.beforeEach((to, from, next) => {
  if (to.meta.title) {
    document.title = to.meta.title
  }
  next()
})

export default router