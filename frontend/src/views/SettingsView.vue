<template>
  <div class="settings-view">
    <div class="settings-header">
      <h2>设置</h2>
      <p>配置AI模型的连接方式和参数</p>
    </div>

    <!-- Tab bar -->
    <div class="tab-bar">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="tab-btn"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >{{ tab.label }}</button>
    </div>

    <div class="settings-content">
      <!-- ================================================================ -->
      <!-- Tab 1: LLM 设置 -->
      <!-- ================================================================ -->
      <div v-show="activeTab === 'llm'">
        <section class="setting-section">
          <h3 class="section-title">LLM 提供商</h3>
          <div class="provider-tabs">
            <button
              v-for="provider in providers"
              :key="provider.id"
              class="provider-tab"
              :class="{ active: settingsStore.llmProvider === provider.id }"
              @click="settingsStore.setProvider(provider.id)"
            >
              <span class="provider-radio">
                <span v-if="settingsStore.llmProvider === provider.id" class="radio-dot"></span>
              </span>
              <div class="provider-info">
                <span class="provider-name">{{ provider.name }}</span>
                <span class="provider-desc">{{ provider.desc }}</span>
              </div>
            </button>
          </div>
        </section>

        <section v-if="settingsStore.llmProvider === 'deepseek'" class="setting-section">
          <h3 class="section-title">API 配置</h3>
          <div class="form-group">
            <label>API 密钥</label>
            <div class="input-wrapper">
              <input
                :type="showApiKey ? 'text' : 'password'"
                v-model="settingsStore.apiKey"
                class="form-input"
                placeholder="sk-xxxxxxxxxxxxxxxx"
              />
              <button class="toggle-vis" @click="showApiKey = !showApiKey">
                <svg v-if="!showApiKey" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
              </button>
            </div>
          </div>
          <div class="form-group">
            <label>API 地址</label>
            <input v-model="settingsStore.apiBaseUrl" class="form-input" placeholder="https://api.example.com/v1" />
          </div>
          <div class="form-group">
            <label>模型名称</label>
            <input v-model="settingsStore.model" class="form-input" placeholder="例如: deepseek-chat, gpt-4o, qwen-plus" />
          </div>
        </section>

        <section v-if="settingsStore.llmProvider === 'lmstudio'" class="setting-section">
          <h3 class="section-title">LM Studio 配置</h3>
          <div class="form-group">
            <label>API 地址</label>
            <input v-model="settingsStore.lmstudioUrl" class="form-input" placeholder="http://localhost:1234/v1" />
          </div>
          <div class="form-group">
            <label>模型名称</label>
            <input v-model="settingsStore.lmstudioModel" class="form-input" placeholder="自动检测或手动输入" />
          </div>
          <p class="form-hint">请确保 LM Studio 已启动并加载了模型。如果留空将自动使用当前加载的模型。</p>
        </section>
      </div>

      <!-- ================================================================ -->
      <!-- Tab 2: 图片描述 -->
      <!-- ================================================================ -->
      <div v-show="activeTab === 'image'">
        <section class="setting-section">
          <h3 class="section-title">图片描述后端</h3>
          <p class="form-hint" style="margin: 4px 0 12px;">用户上传图片时，使用哪个后端进行图片识别和分析。</p>
          <div class="provider-tabs">
            <button
              v-for="opt in imageDescriberOptions"
              :key="opt.id"
              class="provider-tab"
              :class="{ active: settingsStore.imageDescriberBackend === opt.id }"
              @click="settingsStore.imageDescriberBackend = opt.id"
            >
              <span class="provider-radio">
                <span v-if="settingsStore.imageDescriberBackend === opt.id" class="radio-dot"></span>
              </span>
              <div class="provider-info">
                <span class="provider-name">{{ opt.name }}</span>
                <span class="provider-desc">{{ opt.desc }}</span>
              </div>
            </button>
          </div>
          <div class="form-group" style="margin-top: 16px;">
            <label>阿里百炼 API 密钥</label>
            <div class="input-wrapper">
              <input
                :type="showBailianKey ? 'text' : 'password'"
                v-model="settingsStore.bailianApiKey"
                class="form-input"
                placeholder="sk-xxxxxxxxxxxxxxxx"
              />
              <button class="toggle-vis" @click="showBailianKey = !showBailianKey">
                <svg v-if="!showBailianKey" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
              </button>
            </div>
            <p class="form-hint" style="margin: 6px 0 0;">
              用于阿里百炼 Qwen-VL 图片识别，<a href="https://bailian.console.aliyun.com" target="_blank">点此注册</a>
            </p>
          </div>
        </section>
      </div>

      <!-- ================================================================ -->
      <!-- Tab 3: Live2D 看板娘 -->
      <!-- ================================================================ -->
      <div v-show="activeTab === 'live2d'">
        <!-- Enable toggle -->
        <section class="setting-section">
          <div class="provider-tabs">
            <button
              class="provider-tab"
              :class="{ active: settingsStore.live2dEnabled }"
              @click="settingsStore.live2dEnabled = !settingsStore.live2dEnabled"
            >
              <span class="provider-radio">
                <span v-if="settingsStore.live2dEnabled" class="radio-dot"></span>
              </span>
              <div class="provider-info">
                <span class="provider-name">启用 Live2D 看板娘</span>
                <span class="provider-desc">启动后在桌面显示Live2D角色模型，支持表情、动作和口型同步</span>
              </div>
            </button>
          </div>
        </section>

        <template v-if="settingsStore.live2dEnabled">
          <!-- Model selection -->
          <section class="setting-section">
            <h3 class="section-title">已安装模型</h3>
            <p class="form-hint" style="margin: 4px 0 12px;">
              模型存放在 <code>backend/data/models/live2d/</code>，或从外部文件夹导入。
            </p>

            <div v-if="settingsStore.live2dModelsLoading" class="loading-row">加载中...</div>

            <div v-else-if="settingsStore.live2dModels.length === 0" class="empty-hint">
              暂无模型。请在下方导入，或手动将模型文件夹放入 live2d 目录。
            </div>

            <div v-else class="model-list">
              <div
                v-for="m in settingsStore.live2dModels"
                :key="m.name"
                class="model-card"
                :class="{ selected: settingsStore.live2dModelName === m.name }"
                @click="settingsStore.live2dModelName = m.name"
              >
                <span class="model-radio">
                  <span v-if="settingsStore.live2dModelName === m.name" class="radio-dot"></span>
                </span>
                <div class="model-info">
                  <span class="model-name">{{ m.name }}</span>
                  <span class="model-meta">
                    表情: {{ m.has_expressions ? '✓' : '✗' }} &nbsp; 动作: {{ m.has_motions ? '✓' : '✗' }}
                  </span>
                </div>
                <button
                  class="model-delete-btn"
                  :disabled="settingsStore.live2dDeleting === m.name"
                  @click.stop="handleDeleteModel(m.name)"
                  :title="'删除 ' + m.name"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                  </svg>
                </button>
              </div>
            </div>

            <button class="refresh-btn" @click="settingsStore.fetchLive2dModels()" :disabled="settingsStore.live2dModelsLoading">
              刷新列表
            </button>
          </section>

          <!-- Import model -->
          <section class="setting-section">
            <h3 class="section-title">从外部导入模型</h3>
            <p class="form-hint" style="margin: 4px 0 12px;">
              粘贴外部 Live2D 模型文件夹路径，模型将被复制到项目目录中。
              选择包含 <code>.model3.json</code> 文件的目录。
            </p>
            <div class="import-row">
              <input
                v-model="settingsStore.live2dImportPath"
                class="form-input flex-1"
                placeholder="例如: D:\Live2D\Models\Haru"
              />
              <button
                class="import-btn"
                :disabled="!settingsStore.live2dImportPath || settingsStore.live2dImporting"
                @click="handleImportModel"
              >{{ settingsStore.live2dImporting ? '导入中...' : '导入' }}</button>
            </div>
            <p v-if="importMessage" class="form-hint" :style="{ color: importOk ? '#22aa44' : '#cc3333', marginTop: '8px' }">
              {{ importMessage }}
            </p>
          </section>

          <!-- Auto emotion -->
          <section class="setting-section">
            <h3 class="section-title">行为设置</h3>
            <div class="provider-tabs">
              <button
                class="provider-tab"
                :class="{ active: settingsStore.live2dAutoEmotion }"
                @click="settingsStore.live2dAutoEmotion = !settingsStore.live2dAutoEmotion"
              >
                <span class="provider-radio">
                  <span v-if="settingsStore.live2dAutoEmotion" class="radio-dot"></span>
                </span>
                <div class="provider-info">
                  <span class="provider-name">自动情绪切换</span>
                  <span class="provider-desc">根据对话内容自动切换看板娘表情和动作</span>
                </div>
              </button>
            </div>
          </section>

          <!-- Window alpha -->
          <section class="setting-section">
            <h3 class="section-title">窗口透明度</h3>
            <input
              v-model.number="settingsStore.live2dWindowAlpha"
              type="range"
              class="form-range"
              min="0.1" max="1.0" step="0.05"
              @input="settingsStore.applyWindowSettings()"
            />
            <p class="form-hint" style="margin: 6px 0 0;">当前值: {{ (settingsStore.live2dWindowAlpha * 100).toFixed(0) }}%</p>
          </section>

          <!-- Screen map for position + size -->
          <section class="setting-section">
            <h3 class="section-title">位置与大小</h3>
            <p class="form-hint">点击或拖拽蓝色方块移动看板娘，下方滑块调整大小</p>
            <div
              ref="mapContainer"
              class="screen-map"
              :style="{ height: mapH + 'px' }"
              @mousedown="onMapMouseDown"
              @mousemove="onMapMouseMove"
              @mouseup="onMapMouseUp"
              @mouseleave="onMapMouseUp"
            >
              <div
                class="window-marker"
                :style="windowMarkerStyle"
              ></div>
            </div>
            <div class="size-control">
              <input
                v-model.number="settingsStore.live2dWindowWidth"
                type="range"
                class="form-range"
                :min="200" :max="windowSizeMax" step="10"
                @input="onSizeSliderInput"
              />
              <p class="form-hint">大小: {{ settingsStore.live2dWindowWidth }}×{{ settingsStore.live2dWindowHeight }}</p>
            </div>
          </section>
        </template>
      </div>

      <!-- Save button -->
      <div class="settings-actions">
        <button class="save-btn" @click="handleSave">保存设置</button>
      </div>

      <transition name="toast">
        <div v-if="savedToast" class="toast">设置已保存</div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useSettingsStore } from '@/stores/settings'

const settingsStore = useSettingsStore()
const showApiKey = ref(false)
const showBailianKey = ref(false)
const savedToast = ref(false)
const activeTab = ref('llm')
const importMessage = ref('')
const importOk = ref(false)

// ---- screen map state ----
const mapContainer = ref(null)
const screenW = ref(1920)
const screenH = ref(1080)
const mapMaxW = 400
const dragging = ref(false)
const windowSizeMax = ref(2000)

const mapScale = computed(() => {
  return mapMaxW / screenW.value
})

const mapH = computed(() => {
  return Math.round(screenH.value * mapScale.value)
})

const windowMarkerStyle = computed(() => {
  const s = mapScale.value
  const w = Math.max(8, settingsStore.live2dWindowWidth * s)
  const h = Math.max(8, settingsStore.live2dWindowHeight * s)
  const x = settingsStore.live2dWindowX * s
  const y = settingsStore.live2dWindowY * s
  return {
    left: `${x}px`,
    top: `${y}px`,
    width: `${w}px`,
    height: `${h}px`,
  }
})

function onMapMouseDown(e) {
  dragging.value = true
}
function onMapMouseMove(e) {
  if (!dragging.value) return
  updateMarkerPos(e)
}
function onMapMouseUp(e) {
  if (dragging.value) {
    updateMarkerPos(e)
    settingsStore.applyWindowSettings()  // Only apply on release
  }
  dragging.value = false
}
function updateMarkerPos(e) {
  const rect = mapContainer.value?.getBoundingClientRect()
  if (!rect) return
  const s = mapScale.value
  const rx = (e.clientX - rect.left) / s
  const ry = (e.clientY - rect.top) / s
  const w = settingsStore.live2dWindowWidth
  const h = settingsStore.live2dWindowHeight
  settingsStore.live2dWindowX = Math.max(0, Math.round(rx - w / 2))
  settingsStore.live2dWindowY = Math.max(0, Math.round(ry - h / 2))
}
function onSizeSliderInput() {
  const ratio = settingsStore.live2dWindowHeight / (settingsStore.live2dWindowWidth || 400)
  settingsStore.live2dWindowHeight = Math.round(settingsStore.live2dWindowWidth * ratio)
  settingsStore.applyWindowSettings()
}
// ---- end screen map ----

const tabs = [
  { id: 'llm', label: 'LLM 设置' },
  { id: 'image', label: '图片描述' },
  { id: 'live2d', label: 'Live2D 看板娘' },
]

const providers = [
  { id: 'deepseek', name: '云端 API', desc: '支持OpenAI兼容接口的云端大模型' },
  { id: 'lmstudio', name: 'LM Studio', desc: '本地运行，免费无限制' }
]

const imageDescriberOptions = [
  {
    id: 'bailian',
    name: '阿里百炼 Qwen-VL (推荐)',
    desc: '云端多模态模型，中文理解强，价格约¥0.0015/千tokens，需配置API Key'
  },
  {
    id: 'bailian,pixai_tagger,lmstudio',
    name: '百炼 → PixAI标签 → LM Studio',
    desc: '优先云端，百炼不可用时降级到本地 PixAI 标签器，最后尝试 LM Studio'
  },
  {
    id: 'pixai_tagger,bailian',
    name: 'PixAI标签 (本地优先)',
    desc: '优先本地动漫标签器（角色识别F1 0.86），不可用时降级到百炼 API'
  },
  {
    id: 'pixai_tagger,lmstudio',
    name: '仅本地模型',
    desc: '完全离线使用，PixAI 标签器 + LM Studio 视觉模型'
  }
]

onMounted(async () => {
  settingsStore.fetchLive2dModels()
  screenW.value = window.screen.width || 1920
  screenH.value = window.screen.height || 1080
  windowSizeMax.value = Math.max(screenW.value, screenH.value)
  // Sync position from backend so map matches actual window location
  try {
    const res = await fetch('/api/settings/')
    const data = await res.json()
    if (data.success) {
      const d = data.data
      if (d.live2d_window_x != null) settingsStore.live2dWindowX = d.live2d_window_x
      if (d.live2d_window_y != null) settingsStore.live2dWindowY = d.live2d_window_y
      if (d.live2d_window_width != null) settingsStore.live2dWindowWidth = d.live2d_window_width
      if (d.live2d_window_height != null) settingsStore.live2dWindowHeight = d.live2d_window_height
      if (d.live2d_window_alpha != null) settingsStore.live2dWindowAlpha = d.live2d_window_alpha
    }
  } catch (e) {
    // Backend may not be ready yet
  }
})

async function handleImportModel() {
  const path = settingsStore.live2dImportPath.trim()
  if (!path) return
  const result = await settingsStore.importLive2dModel(path)
  importOk.value = result.success
  importMessage.value = result.message
  if (result.success) {
    settingsStore.live2dImportPath = ''
  }
  setTimeout(() => { importMessage.value = '' }, 5000)
}

async function handleDeleteModel(name) {
  if (!confirm(`确定要删除模型 "${name}" 吗？此操作不可恢复。`)) return
  const result = await settingsStore.deleteLive2dModel(name)
  importOk.value = result.success
  importMessage.value = result.message
  setTimeout(() => { importMessage.value = '' }, 5000)
}

async function handleSave() {
  settingsStore.saveSettings()
  savedToast.value = true
  try {
    await fetch('/api/settings/', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        llm_provider: settingsStore.llmProvider,
        llm_model: settingsStore.activeModel,
        llm_api_key: settingsStore.apiKey || null,
        llm_api_base_url: settingsStore.activeApiUrl || null,
        llm_temperature: settingsStore.temperature,
        llm_max_tokens: settingsStore.maxTokens,
        image_describer_backend: settingsStore.imageDescriberBackend,
        bailian_api_key: settingsStore.bailianApiKey || null,
        live2d_enabled: settingsStore.live2dEnabled,
        live2d_model_name: settingsStore.live2dModelName || null,
        live2d_auto_emotion: settingsStore.live2dAutoEmotion,
        live2d_window_alpha: settingsStore.live2dWindowAlpha,
        live2d_window_width: settingsStore.live2dWindowWidth,
        live2d_window_height: settingsStore.live2dWindowHeight,
        live2d_window_x: settingsStore.live2dWindowX,
        live2d_window_y: settingsStore.live2dWindowY
      })
    })
  } catch (e) {
    console.warn('同步设置到后端失败:', e)
  }
  setTimeout(() => { savedToast.value = false }, 2000)
}
</script>

<style scoped>
.settings-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

.settings-header {
  flex-shrink: 0;
  padding: 24px 32px 16px;
  border-bottom: 1px solid #eeeeee;
}

.settings-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.settings-header p {
  font-size: 13px;
  color: #999999;
  margin: 4px 0 0;
}

/* -- Tab bar -- */

.tab-bar {
  flex-shrink: 0;
  display: flex;
  gap: 0;
  padding: 0 32px;
  border-bottom: 1px solid #eeeeee;
}

.tab-btn {
  padding: 10px 20px;
  border: none;
  background: transparent;
  font-size: 13px;
  font-weight: 500;
  color: #999999;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
  font-family: inherit;
}

.tab-btn:hover {
  color: #555555;
}

.tab-btn.active {
  color: #1a1a1a;
  border-bottom-color: #333333;
}

/* -- Content -- */

.settings-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

.setting-section {
  margin-bottom: 28px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #333333;
  margin: 0 0 16px;
}

.provider-tabs {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.provider-tab {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  background: #ffffff;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.provider-tab:hover {
  background: #f9f9f9;
  border-color: #cccccc;
}

.provider-tab.active {
  border-color: #333333;
  background: #f9f9f9;
}

.provider-radio {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid #cccccc;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: border-color 0.2s;
}

.provider-tab.active .provider-radio {
  border-color: #333333;
}

.radio-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #333333;
}

.provider-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.provider-name {
  font-size: 14px;
  font-weight: 500;
  color: #1a1a1a;
}

.provider-desc {
  font-size: 12px;
  color: #999999;
}

/* -- Form -- */

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #555555;
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #d0d0d0;
  border-radius: 10px;
  font-size: 14px;
  color: #1a1a1a;
  background: #ffffff;
  outline: none;
  transition: border-color 0.2s;
  font-family: inherit;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: #333333;
}

.form-input::placeholder {
  color: #bbbbbb;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-wrapper .form-input {
  padding-right: 44px;
}

.toggle-vis {
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  cursor: pointer;
  color: #999999;
  border-radius: 8px;
  transition: color 0.2s;
}

.toggle-vis:hover { color: #333333; }

.toggle-vis svg {
  width: 18px;
  height: 18px;
}

.form-hint {
  font-size: 12px;
  color: #999999;
  margin: 4px 0 8px;
  line-height: 1.6;
}

.form-hint code {
  background: #f3f3f3;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-family: 'Consolas', 'Monaco', monospace;
  color: #555555;
}

.form-range {
  width: 100%;
  height: 6px;
  appearance: none;
  background: #e0e0e0;
  border-radius: 3px;
  outline: none;
  cursor: pointer;
}

.form-range::-webkit-slider-thumb {
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #333333;
  cursor: pointer;
}

.flex-1 { flex: 1; }

/* -- Model list -- */

.empty-hint {
  padding: 20px;
  text-align: center;
  font-size: 13px;
  color: #aaaaaa;
  background: #fafafa;
  border: 1px dashed #e0e0e0;
  border-radius: 10px;
}

.loading-row {
  padding: 12px;
  font-size: 13px;
  color: #999999;
  text-align: center;
}

.model-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.model-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border: 1px solid #e8e8e8;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s;
}

.model-card:hover {
  border-color: #cccccc;
  background: #fafafa;
}

.model-card.selected {
  border-color: #333333;
  background: #f9f9f9;
}

.model-radio {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid #cccccc;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: border-color 0.2s;
}

.model-card.selected .model-radio {
  border-color: #333333;
}

.model-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.model-name {
  font-size: 13px;
  font-weight: 500;
  color: #333333;
}

.model-meta {
  font-size: 11px;
  color: #aaaaaa;
  font-family: 'Consolas', monospace;
}

.model-delete-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: #ffffff;
  color: #999999;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.15s;
}

.model-delete-btn:hover {
  color: #cc3333;
  border-color: #eecccc;
  background: #fff5f5;
}

.model-delete-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.refresh-btn {
  padding: 8px 16px;
  border: 1px solid #d0d0d0;
  border-radius: 8px;
  background: #ffffff;
  font-size: 12px;
  color: #666666;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.15s;
}

.refresh-btn:hover {
  border-color: #999999;
  color: #333333;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* -- Import row -- */

.import-row {
  display: flex;
  gap: 10px;
}

.import-btn {
  padding: 10px 20px;
  background: #333333;
  color: #ffffff;
  border: none;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  white-space: nowrap;
  transition: all 0.2s;
}

.import-btn:hover {
  background: #555555;
}

.import-btn:disabled {
  background: #cccccc;
  cursor: not-allowed;
}

/* -- Save & toast -- */

.settings-actions {
  padding-top: 8px;
}

.save-btn {
  padding: 12px 32px;
  background: #333333;
  color: #ffffff;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.save-btn:hover {
  background: #555555;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

.toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: #333333;
  color: #ffffff;
  padding: 10px 24px;
  border-radius: 10px;
  font-size: 13px;
  z-index: 1000;
}

.size-row {
  display: flex;
  gap: 16px;
}

.size-field {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.screen-map {
  position: relative;
  width: 100%;
  max-width: 400px;
  margin: 0 auto;
  background: #1a1a2e;
  border: 1px solid #333;
  border-radius: 8px;
  cursor: crosshair;
  overflow: hidden;
}

.window-marker {
  position: absolute;
  background: rgba(100, 180, 255, 0.35);
  border: 2px solid rgba(100, 180, 255, 0.8);
  border-radius: 4px;
  pointer-events: none;
  transition: none;
}

.size-control {
  margin-top: 12px;
}

.size-field label {
  font-size: 12px;
  color: #888;
}
</style>
