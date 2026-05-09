import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/styles/main.css'

// 全局样式
import './assets/styles/tailwind.css'

// 创建Vue应用
const app = createApp(App)

// 使用Pinia状态管理
const pinia = createPinia()
app.use(pinia)

// 使用路由
app.use(router)

// 全局错误处理
app.config.errorHandler = (err, instance, info) => {
  console.error('Vue错误:', err)
  console.error('组件实例:', instance)
  console.error('错误信息:', info)
  
  // 发送错误到后端日志
  if (window.electronAPI) {
    window.electronAPI.sendErrorLog?.({
      error: err.toString(),
      component: instance?.$options.name,
      info,
      timestamp: new Date().toISOString()
    })
  }
}

// 全局配置
app.config.globalProperties.$appVersion = import.meta.env.VITE_APP_VERSION || '0.1.0'
app.config.globalProperties.$isElectron = !!window.electronAPI
app.config.globalProperties.$isDevelopment = import.meta.env.DEV

// 挂载应用
app.mount('#app')

// 开发工具
if (import.meta.env.DEV) {
  console.log('崩坏3专属AI陪伴助手 - 开发模式')
  console.log('应用版本:', app.config.globalProperties.$appVersion)
  console.log('Electron环境:', app.config.globalProperties.$isElectron)
  console.log('API基础URL:', import.meta.env.VITE_API_BASE_URL)
}

// 应用就绪回调
if (window.appReady) {
  window.appReady()
}