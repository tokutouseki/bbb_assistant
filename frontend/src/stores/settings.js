import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useSettingsStore = defineStore('settings', () => {
  const llmProvider = ref('deepseek')
  const apiKey = ref('')
  const apiBaseUrl = ref('https://api.deepseek.com/v1')
  const model = ref('deepseek-chat')
  const lmstudioUrl = ref('http://localhost:1234/v1')
  const lmstudioModel = ref('')
  const ollamaUrl = ref('http://localhost:11434/api')
  const ollamaModel = ref('qwen2.5:7b')
  const temperature = ref(0.7)
  const maxTokens = ref(4096)

  const activeModel = computed(() => {
    if (llmProvider.value === 'deepseek') return model.value
    if (llmProvider.value === 'lmstudio') return lmstudioModel.value || 'local-model'
    if (llmProvider.value === 'ollama') return ollamaModel.value
    return ''
  })

  const activeApiUrl = computed(() => {
    if (llmProvider.value === 'deepseek') return apiBaseUrl.value
    if (llmProvider.value === 'lmstudio') return lmstudioUrl.value
    if (llmProvider.value === 'ollama') return ollamaUrl.value
    return ''
  })

  function setProvider(provider) {
    llmProvider.value = provider
  }

  function setApiKey(key) {
    apiKey.value = key
  }

  function loadSettings() {
    try {
      const saved = localStorage.getItem('bbb-assistant-settings-llm')
      if (saved) {
        const parsed = JSON.parse(saved)
        llmProvider.value = parsed.llmProvider || 'deepseek'
        apiKey.value = parsed.apiKey || ''
        apiBaseUrl.value = parsed.apiBaseUrl || 'https://api.deepseek.com/v1'
        model.value = parsed.model || 'deepseek-chat'
        lmstudioUrl.value = parsed.lmstudioUrl || 'http://localhost:1234/v1'
        lmstudioModel.value = parsed.lmstudioModel || ''
        ollamaUrl.value = parsed.ollamaUrl || 'http://localhost:11434/api'
        ollamaModel.value = parsed.ollamaModel || 'qwen2.5:7b'
        temperature.value = parsed.temperature ?? 0.7
        maxTokens.value = parsed.maxTokens ?? 4096
      }
    } catch (e) {
      console.warn('加载设置失败:', e)
    }
  }

  function saveSettings() {
    const settings = {
      llmProvider: llmProvider.value,
      apiKey: apiKey.value,
      apiBaseUrl: apiBaseUrl.value,
      model: model.value,
      lmstudioUrl: lmstudioUrl.value,
      lmstudioModel: lmstudioModel.value,
      ollamaUrl: ollamaUrl.value,
      ollamaModel: ollamaModel.value,
      temperature: temperature.value,
      maxTokens: maxTokens.value
    }
    localStorage.setItem('bbb-assistant-settings-llm', JSON.stringify(settings))
  }

  return {
    llmProvider,
    apiKey,
    apiBaseUrl,
    model,
    lmstudioUrl,
    lmstudioModel,
    ollamaUrl,
    ollamaModel,
    temperature,
    maxTokens,
    activeModel,
    activeApiUrl,
    setProvider,
    setApiKey,
    loadSettings,
    saveSettings
  }
})
