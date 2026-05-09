<template>
  <div class="chat-view">
    <div class="chat-header">
      <div class="agent-avatar">
        <div class="avatar-circle">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="avatar-svg">
            <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
        </div>
        <div class="agent-info">
          <span class="agent-name">崩坏3 AI助手</span>
          <span class="agent-status">在线</span>
        </div>
      </div>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <div v-if="chatStore.messages.length === 0" class="empty-state">
        <div class="empty-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
          </svg>
        </div>
        <p>开始和崩坏3 AI助手对话吧</p>
        <p class="empty-hint">可以问我游戏攻略、角色信息、故事剧情等</p>
      </div>

      <div
        v-for="msg in chatStore.messages"
        :key="msg.id"
        class="message-wrapper"
        :class="msg.role"
      >
        <div v-if="msg.role === 'user'" class="message-bubble user-bubble">
          {{ msg.content }}
        </div>
        <div v-else class="message-bubble assistant-bubble">
          {{ msg.content }}
        </div>
      </div>

      <div v-if="chatStore.streamingContent" class="message-wrapper assistant">
        <div class="message-bubble assistant-bubble streaming">
          {{ chatStore.streamingContent }}
          <span class="cursor-blink">|</span>
        </div>
      </div>

      <div v-if="chatStore.isLoading && !chatStore.streamingContent" class="loading-indicator">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
      </div>
    </div>

    <div class="chat-input-area">
      <div class="input-box">
        <textarea
          v-model="inputText"
          class="message-input"
          placeholder="输入消息..."
          rows="3"
          @keydown.enter.exact.prevent="sendMessage"
          @input="autoResize"
          ref="inputRef"
        ></textarea>
        <div class="skills-bar">
          <button
            v-for="skill in chatStore.agentSkills"
            :key="skill.id"
            class="skill-tag"
            :title="skill.description"
            @click="useSkill(skill)"
          >
            <span class="skill-dot"></span>
            {{ skill.name }}
          </button>
          <button
            v-if="!chatStore.isLoading"
            class="send-btn"
            :disabled="!canSend"
            @click="sendMessage"
            title="发送"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
          <button
            v-else
            class="stop-btn"
            @click="stopMessage"
            title="停止生成"
          >
            <svg viewBox="0 0 24 24" fill="currentColor">
              <rect x="4" y="4" width="16" height="16" rx="3"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useSettingsStore } from '@/stores/settings'

const chatStore = useChatStore()
const settingsStore = useSettingsStore()

const inputText = ref('')
const inputRef = ref(null)
const messagesContainer = ref(null)
const abortController = ref(null)

const canSend = computed(() => {
  return inputText.value.trim().length > 0 && !chatStore.isLoading
})

function autoResize() {
  const el = inputRef.value
  if (el) {
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }
}

const SKILL_PROMPTS = {
  rag: '请帮我查一下崩坏3的攻略：',
  vision: '请识别当前游戏画面中的内容，',
  memory: '回顾一下我们之前的对话，',
  tool: '请使用工具帮我完成：'
}

function useSkill(skill) {
  const prefix = SKILL_PROMPTS[skill.id] || ''
  inputText.value = prefix + (inputText.value || '')
  const el = inputRef.value
  if (el) {
    el.focus()
    autoResize()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

function stopMessage() {
  if (abortController.value) {
    abortController.value.abort()
    abortController.value = null
  }
  chatStore.isLoading = false
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || chatStore.isLoading) return

  abortController.value = new AbortController()

  chatStore.addMessage({ role: 'user', content: text })
  inputText.value = ''
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
  }
  scrollToBottom()

  chatStore.isLoading = true
  chatStore.setError(null)

  try {
    const response = await fetch('/api/chat/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        messages: [{ role: 'user', content: text }],
        use_rag: true,
        stream: false,
        show_thinking: true,
        llm_provider: settingsStore.llmProvider,
        llm_model: settingsStore.activeModel,
        llm_api_key: settingsStore.apiKey || undefined,
        llm_api_base_url: settingsStore.activeApiUrl || undefined,
        llm_temperature: settingsStore.temperature,
        llm_max_tokens: settingsStore.maxTokens
      }),
      signal: abortController.value.signal
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}`)
    }

    const data = await response.json()

    if (data.message) {
      chatStore.addMessage({
        role: 'assistant',
        content: data.message.content || data.message
      })
    } else if (data.content) {
      chatStore.addMessage({
        role: 'assistant',
        content: data.content
      })
    } else if (typeof data === 'string') {
      chatStore.addMessage({
        role: 'assistant',
        content: data
      })
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      chatStore.addMessage({
        role: 'assistant',
        content: '生成已终止。'
      })
    } else {
      console.error('发送消息失败:', error)
      chatStore.setError(error.message || '发送失败')
      chatStore.addMessage({
        role: 'assistant',
        content: '抱歉，消息发送失败了。请检查网络连接和后端服务是否正常运行。'
      })
    }
  } finally {
    abortController.value = null
    chatStore.isLoading = false
    scrollToBottom()
  }
}

watch(() => chatStore.messages.length, () => {
  scrollToBottom()
})

onMounted(() => {
  settingsStore.loadSettings()
  scrollToBottom()
})
</script>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #ffffff;
}

.chat-header {
  flex-shrink: 0;
  padding: 12px 20px;
  border-bottom: 1px solid #eeeeee;
}

.agent-avatar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar-circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #f472b6, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  flex-shrink: 0;
}

.avatar-svg {
  width: 22px;
  height: 22px;
}

.agent-info {
  display: flex;
  flex-direction: column;
}

.agent-name {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
}

.agent-status {
  font-size: 12px;
  color: #22c55e;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999999;
  gap: 8px;
}

.empty-icon {
  width: 48px;
  height: 48px;
  color: #cccccc;
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 13px;
  color: #bbbbbb;
}

.message-wrapper {
  display: flex;
  max-width: 80%;
}

.message-wrapper.user {
  align-self: flex-end;
}

.message-wrapper.assistant {
  align-self: flex-start;
}

.message-bubble {
  padding: 10px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.user-bubble {
  background: #333333;
  color: #ffffff;
  border-bottom-right-radius: 4px;
}

.assistant-bubble {
  background: #f3f3f3;
  color: #1a1a1a;
  border-bottom-left-radius: 4px;
}

.streaming .cursor-blink {
  animation: blink 0.8s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.loading-indicator {
  display: flex;
  gap: 6px;
  padding: 12px 16px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #cccccc;
  animation: dotPulse 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }
.dot:nth-child(3) { animation-delay: 0s; }

@keyframes dotPulse {
  0%, 80%, 100% { transform: scale(0); opacity: 0.3; }
  40% { transform: scale(1); opacity: 1; }
}

.chat-input-area {
  flex-shrink: 0;
  border-top: 1px solid #eeeeee;
  display: flex;
  flex-direction: column;
  height: 30%;
  min-height: 160px;
  padding: 12px 16px;
}

.input-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  border: 1px solid #999999;
  border-radius: 16px;
  background: #ffffff;
  overflow: hidden;
  transition: border-color 0.2s;
}

.skills-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
}

.skill-tag {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #555555;
  background: #f0f0f0;
  border: 1px solid #e0e0e0;
  border-radius: 14px;
  padding: 3px 10px;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}

.skill-tag:hover {
  background: #333333;
  color: #ffffff;
  border-color: #333333;
}

.skill-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #22c55e;
}

.skill-tag:hover .skill-dot {
  background: #4ade80;
}

.message-input,
.message-input:focus,
.message-input:focus-visible {
  flex: 1;
  width: 100%;
  border: none !important;
  box-shadow: none !important;
  padding: 14px 16px 8px;
  font-size: 14px;
  line-height: 1.5;
  color: #1a1a1a;
  background: transparent;
  resize: none;
  outline: none !important;
  font-family: inherit;
  min-height: 64px;
  max-height: 120px;
}

.message-input::placeholder {
  color: #bbbbbb;
}

.send-btn {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: #333333;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border: none;
  flex-shrink: 0;
  transition: all 0.15s;
  margin-left: auto;
}

.send-btn:hover:not(.disabled) {
  background: #555555;
  transform: scale(1.05);
}

.send-btn.disabled {
  background: #cccccc;
  cursor: not-allowed;
}

.send-btn svg {
  width: 18px;
  height: 18px;
}

.stop-btn {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: #ef4444;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border: none;
  flex-shrink: 0;
  transition: all 0.15s;
  margin-left: auto;
}

.stop-btn:hover {
  background: #dc2626;
  transform: scale(1.05);
}

.stop-btn svg {
  width: 16px;
  height: 16px;
}
</style>
