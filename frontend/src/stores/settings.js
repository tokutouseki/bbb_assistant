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
  const imageDescriberBackend = ref('bailian')
  const bailianApiKey = ref('')
  const live2dEnabled = ref(false)
  const live2dModelName = ref('')
  const live2dAutoEmotion = ref(true)
  const live2dWindowAlpha = ref(1.0)
  const live2dWindowWidth = ref(400)
  const live2dWindowHeight = ref(500)
  const live2dWindowX = ref(100)
  const live2dWindowY = ref(100)

  // Live2D model management
  const live2dModels = ref([])
  const live2dModelsLoading = ref(false)
  const live2dImportPath = ref('')
  const live2dImporting = ref(false)
  const live2dDeleting = ref(null)

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

  async function fetchLive2dModels() {
    live2dModelsLoading.value = true
    try {
      const res = await fetch('/api/live2d/models')
      const data = await res.json()
      if (data.success) {
        live2dModels.value = data.models
      }
    } catch (e) {
      console.warn('获取Live2D模型列表失败:', e)
    } finally {
      live2dModelsLoading.value = false
    }
  }

  async function importLive2dModel(sourcePath) {
    live2dImporting.value = true
    try {
      const res = await fetch('/api/live2d/models/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_path: sourcePath })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || '导入失败')
      await fetchLive2dModels()
      return { success: true, message: data.message }
    } catch (e) {
      return { success: false, message: e.message }
    } finally {
      live2dImporting.value = false
    }
  }

  async function deleteLive2dModel(modelName) {
    live2dDeleting.value = modelName
    try {
      const res = await fetch(`/api/live2d/models/${encodeURIComponent(modelName)}`, {
        method: 'DELETE'
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || '删除失败')
      if (live2dModelName.value === modelName) {
        live2dModelName.value = ''
      }
      await fetchLive2dModels()
      return { success: true, message: data.message }
    } catch (e) {
      return { success: false, message: e.message }
    } finally {
      live2dDeleting.value = null
    }
  }

  let _applyTimer = null
  function applyWindowSettings() {
    if (_applyTimer) clearTimeout(_applyTimer)
    _applyTimer = setTimeout(async () => {
      try {
        await fetch('/api/live2d/apply', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            window_x: live2dWindowX.value,
            window_y: live2dWindowY.value,
            window_width: live2dWindowWidth.value,
            window_height: live2dWindowHeight.value,
            window_alpha: live2dWindowAlpha.value,
          })
        })
      } catch (e) {
        // Server may not be running — silently ignore
      }
    }, 50)
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
        imageDescriberBackend.value = parsed.imageDescriberBackend || 'bailian'
        bailianApiKey.value = parsed.bailianApiKey || ''
        live2dEnabled.value = parsed.live2dEnabled ?? false
        live2dModelName.value = parsed.live2dModelName || ''
        live2dAutoEmotion.value = parsed.live2dAutoEmotion ?? true
        live2dWindowAlpha.value = parsed.live2dWindowAlpha ?? 1.0
        live2dWindowWidth.value = parsed.live2dWindowWidth ?? 400
        live2dWindowHeight.value = parsed.live2dWindowHeight ?? 500
        live2dWindowX.value = parsed.live2dWindowX ?? 100
        live2dWindowY.value = parsed.live2dWindowY ?? 100
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
      maxTokens: maxTokens.value,
      imageDescriberBackend: imageDescriberBackend.value,
      bailianApiKey: bailianApiKey.value,
      live2dEnabled: live2dEnabled.value,
      live2dModelName: live2dModelName.value,
      live2dAutoEmotion: live2dAutoEmotion.value,
      live2dWindowAlpha: live2dWindowAlpha.value,
      live2dWindowWidth: live2dWindowWidth.value,
      live2dWindowHeight: live2dWindowHeight.value,
      live2dWindowX: live2dWindowX.value,
      live2dWindowY: live2dWindowY.value
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
    imageDescriberBackend,
    bailianApiKey,
    live2dEnabled,
    live2dModelName,
    live2dAutoEmotion,
    live2dWindowAlpha,
    live2dWindowWidth,
    live2dWindowHeight,
    live2dWindowX,
    live2dWindowY,
    live2dModels,
    live2dModelsLoading,
    live2dImportPath,
    live2dImporting,
    live2dDeleting,
    activeModel,
    activeApiUrl,
    setProvider,
    setApiKey,
    fetchLive2dModels,
    importLive2dModel,
    deleteLive2dModel,
    applyWindowSettings,
    loadSettings,
    saveSettings
  }
})
