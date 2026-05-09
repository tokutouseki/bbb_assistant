<template>
  <div class="settings-view">
    <div class="settings-header">
      <h2>设置</h2>
      <p>配置AI模型的连接方式和参数</p>
    </div>

    <div class="settings-content">
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
          <input
            v-model="settingsStore.apiBaseUrl"
            class="form-input"
            placeholder="https://api.example.com/v1"
          />
        </div>
        <div class="form-group">
          <label>模型名称</label>
          <input
            v-model="settingsStore.model"
            class="form-input"
            placeholder="例如: deepseek-chat, gpt-4o, qwen-plus"
          />
        </div>
      </section>

      <section v-if="settingsStore.llmProvider === 'lmstudio'" class="setting-section">
        <h3 class="section-title">LM Studio 配置</h3>
        <div class="form-group">
          <label>API 地址</label>
          <input
            v-model="settingsStore.lmstudioUrl"
            class="form-input"
            placeholder="http://localhost:1234/v1"
          />
        </div>
        <div class="form-group">
          <label>模型名称</label>
          <input
            v-model="settingsStore.lmstudioModel"
            class="form-input"
            placeholder="自动检测或手动输入"
          />
        </div>
        <p class="form-hint">
          请确保 LM Studio 已启动并加载了模型。如果留空将自动使用当前加载的模型。
        </p>
      </section>
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
import { ref } from 'vue'
import { useSettingsStore } from '@/stores/settings'

const settingsStore = useSettingsStore()
const showApiKey = ref(false)
const savedToast = ref(false)

const providers = [
  { id: 'deepseek', name: '云端 API', desc: '支持OpenAI兼容接口的云端大模型' },
  { id: 'lmstudio', name: 'LM Studio', desc: '本地运行，免费无限制' }
]

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
        llm_max_tokens: settingsStore.maxTokens
      })
    })
  } catch (e) {
    console.warn('同步设置到后端失败:', e)
  }
  setTimeout(() => {
    savedToast.value = false
  }, 2000)
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
}

.form-input:focus {
  border-color: #333333;
}

.form-input::placeholder {
  color: #bbbbbb;
}

select.form-input {
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23666666' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 36px;
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

.toggle-vis:hover {
  color: #333333;
}

.toggle-vis svg {
  width: 18px;
  height: 18px;
}

.form-hint {
  font-size: 12px;
  color: #999999;
  margin: -8px 0 16px;
  line-height: 1.5;
}

.form-hint code {
  background: #f3f3f3;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-family: 'Consolas', 'Monaco', monospace;
  color: #555555;
}

.form-row {
  display: flex;
  gap: 20px;
}

.flex-1 {
  flex: 1;
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
</style>
