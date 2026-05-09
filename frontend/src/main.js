import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/styles/main.css'
import './assets/styles/tailwind.css'

const app = createApp(App)

const pinia = createPinia()

pinia.use(({ store }) => {
  const savedState = localStorage.getItem(`bbb-assistant-${store.$id}`)
  if (savedState) {
    try {
      store.$patch(JSON.parse(savedState))
    } catch (error) {
      console.warn(`Failed to load state for store ${store.$id}:`, error)
    }
  }

  store.$subscribe((mutation, state) => {
    try {
      localStorage.setItem(`bbb-assistant-${store.$id}`, JSON.stringify(state))
    } catch (error) {
      console.warn(`Failed to save state for store ${store.$id}:`, error)
    }
  })
})

app.use(pinia)
app.use(router)

app.config.errorHandler = (err, instance, info) => {
  console.error('Vue错误:', err)
  console.error('组件实例:', instance)
  console.error('错误信息:', info)

  if (window.electronAPI) {
    window.electronAPI.sendErrorLog?.({
      error: err.toString(),
      component: instance?.$options.name,
      info,
      timestamp: new Date().toISOString()
    })
  }
}

app.config.globalProperties.$appVersion = import.meta.env.VITE_APP_VERSION || '0.1.0'
app.config.globalProperties.$isElectron = !!window.electronAPI
app.config.globalProperties.$isDevelopment = import.meta.env.DEV

app.mount('#app')

if (import.meta.env.DEV) {
  console.log('崩坏3专属AI陪伴助手 - 开发模式')
  console.log('应用版本:', app.config.globalProperties.$appVersion)
  console.log('Electron环境:', app.config.globalProperties.$isElectron)
  console.log('API基础URL:', import.meta.env.VITE_API_BASE_URL)
}

if (window.appReady) {
  window.appReady()
}