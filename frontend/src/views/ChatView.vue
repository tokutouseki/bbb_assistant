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
      <div class="header-actions">
        <button
          class="clear-context-btn"
          @click="clearContext"
          :disabled="isClearingContext"
          title="清除对话上下文和任务检查点"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>
            <line x1="10" y1="11" x2="10" y2="17"/>
            <line x1="14" y1="11" x2="14" y2="17"/>
          </svg>
          <span>{{ isClearingContext ? '清除中...' : '刷新上下文' }}</span>
        </button>
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
        <div v-else class="message-bubble assistant-bubble" v-html="renderMarkdown(msg.content)"></div>
        <div v-if="msg.images && msg.images.length" class="msg-images">
          <img
            v-for="(img, i) in msg.images"
            :key="i"
            :src="img"
            class="msg-image"
            @click="previewFullImage(img)"
            alt="attached image"
          />
        </div>
        <div v-if="msg.audios && msg.audios.length" class="msg-audios">
          <audio
            v-for="(aud, i) in msg.audios"
            :key="i"
            :src="aud"
            controls
            class="msg-audio"
          ></audio>
        </div>
      </div>

      <div v-if="todoList.length > 0" class="message-wrapper assistant">
        <div class="todo-card">
          <div class="todo-header">任务计划</div>
          <div
            v-for="task in todoList"
            :key="task.id"
            class="todo-item"
            :class="'todo-' + task.status"
          >
            <span class="todo-icon">
              <template v-if="task.status === 'completed'">✓</template>
              <template v-else-if="task.status === 'in_progress'">◷</template>
              <template v-else>○</template>
            </span>
            <span class="todo-content" :class="{ 'todo-done': task.status === 'completed' }">
              {{ task.content }}
            </span>
          </div>
        </div>
      </div>

      <template v-if="currentSteps.length > 0">
        <div
          v-for="(step, idx) in currentSteps"
          :key="idx"
          class="message-wrapper assistant"
        >
          <div class="thought-bubble" v-if="step.thought && step.action !== '_Exception'">
            <div class="thought-label">Thought</div>
            <div class="thought-text">{{ step.thought }}</div>
          </div>
        </div>
        <div v-if="chatStore.isLoading && lastStepHasObservation" class="loading-indicator">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
      </template>

      <div v-if="chatStore.isLoading && currentSteps.length === 0" class="loading-indicator">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
      </div>
    </div>

    <div class="chat-input-area">
      <div v-if="selectedImages.length > 0" class="image-preview-row">
        <div v-for="(img, idx) in selectedImages" :key="idx" class="preview-thumb">
          <img :src="previewUrls[idx]" alt="preview" />
          <button class="remove-img-btn" @click="removeImage(idx)" title="移除图片">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      </div>
      <div v-if="selectedAudios.length > 0" class="audio-preview-row">
        <div v-for="(audio, idx) in selectedAudios" :key="idx" class="preview-audio-item">
          <audio :src="audioPreviewUrls[idx]" controls class="audio-preview-player"></audio>
          <button class="remove-img-btn" @click="removeAudio(idx)" title="移除音频">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      </div>
      <div v-if="recordingState === 'recording'" class="recording-indicator">
        <span class="recording-dot"></span>
        <span class="recording-timer">{{ formatDuration(recordingDuration) }}</span>
        <span class="recording-hint">点击麦克风按钮停止录音</span>
      </div>
      <div class="input-box">
        <input
          ref="imageInput"
          type="file"
          accept="image/*"
          multiple
          style="display:none"
          @change="handleImageSelect"
        />
        <input
          ref="audioFileInput"
          type="file"
          accept="audio/*"
          style="display:none"
          @change="handleAudioFileSelect"
        />
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
            class="attach-btn"
            @click="triggerImageSelect"
            title="上传图片"
            :disabled="chatStore.isLoading"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
              <circle cx="8.5" cy="8.5" r="1.5"/>
              <polyline points="21 15 16 10 5 21"/>
            </svg>
          </button>
          <button
            class="attach-btn"
            @click="audioFileInput?.click()"
            title="上传音频文件"
            :disabled="chatStore.isLoading || recordingState !== 'idle'"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
              <path d="M9 18V5l12-2v13"/>
              <circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>
            </svg>
          </button>
          <button
            class="attach-btn mic-btn"
            :class="{ 'is-recording': recordingState === 'recording' }"
            @click="toggleRecording"
            :disabled="recordingState === 'requesting'"
            :title="recordingState === 'idle' ? '录制语音' : '停止录制'"
          >
            <svg v-if="recordingState !== 'recording'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
              <rect x="9" y="2" width="6" height="12" rx="3"/>
              <path d="M5 10a7 7 0 0014 0"/>
              <line x1="12" y1="19" x2="12" y2="22"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
              <rect x="6" y="6" width="12" height="12" rx="2"/>
            </svg>
          </button>
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

    <!-- 图片灯箱 -->
    <teleport to="body">
      <div v-if="lightboxSrc" class="lightbox-backdrop" @click="closeLightbox">
        <img :src="lightboxSrc" class="lightbox-image" @click.stop />
        <button class="lightbox-close" @click="closeLightbox" title="关闭">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    </teleport>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useSettingsStore } from '@/stores/settings'
import { marked } from 'marked'

marked.use({
  breaks: true,
  gfm: true,
})

function renderMarkdown(text) {
  if (!text) return ''
  return marked.parse(text)
}

const chatStore = useChatStore()
const settingsStore = useSettingsStore()

const inputText = ref('')
const inputRef = ref(null)
const imageInput = ref(null)
const messagesContainer = ref(null)
const abortController = ref(null)
const currentRequestId = ref('')
const currentSteps = ref([])
const todoList = ref([])

const selectedImages = ref([])
const previewUrls = ref([])
const lightboxSrc = ref(null)

// Audio recording state
const recordingState = ref('idle')  // 'idle' | 'requesting' | 'recording'
const recordingDuration = ref(0)
let recordingTimer = null
const mediaRecorder = ref(null)
const audioChunks = ref([])
const audioFileInput = ref(null)
const selectedAudios = ref([])      // File or Blob objects
const audioPreviewUrls = ref([])    // blob URLs for playback

const isClearingContext = ref(false)

const canSend = computed(() => {
  return (inputText.value.trim().length > 0 || selectedImages.value.length > 0 || selectedAudios.value.length > 0) && !chatStore.isLoading
})

function triggerImageSelect() {
  imageInput.value?.click()
}

function handleImageSelect(e) {
  const files = Array.from(e.target.files || [])
  for (const file of files) {
    if (!file.type.startsWith('image/')) continue
    selectedImages.value.push(file)
    previewUrls.value.push(URL.createObjectURL(file))
  }
  // Reset input so same file can be re-selected
  if (imageInput.value) imageInput.value.value = ''
}

function removeImage(idx) {
  URL.revokeObjectURL(previewUrls.value[idx])
  selectedImages.value.splice(idx, 1)
  previewUrls.value.splice(idx, 1)
}

function compressImage(file) {
  return new Promise((resolve) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const img = new Image()
      img.onload = () => {
        const maxDim = 1024
        let { width, height } = img
        if (width <= maxDim && height <= maxDim) {
          resolve(e.target.result)
          return
        }
        if (width > height) {
          height = Math.round(height * maxDim / width)
          width = maxDim
        } else {
          width = Math.round(width * maxDim / height)
          height = maxDim
        }
        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        const ctx = canvas.getContext('2d')
        ctx.drawImage(img, 0, 0, width, height)
        resolve(canvas.toDataURL('image/jpeg', 0.8))
      }
      img.src = e.target.result
    }
    reader.readAsDataURL(file)
  })
}

const lastStepHasObservation = computed(() => {
  const steps = currentSteps.value
  if (steps.length === 0) return true
  return steps[steps.length - 1].observation != null
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
  tool: '请使用工具帮我完成：',
  audio: '请用爱莉希雅的声音说：'
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

function previewFullImage(src) {
  lightboxSrc.value = src
}

function closeLightbox() {
  lightboxSrc.value = null
}

// --- Audio recording ---

function formatDuration(seconds) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

async function toggleRecording() {
  if (recordingState.value === 'recording') {
    if (mediaRecorder.value && mediaRecorder.value.state === 'recording') {
      mediaRecorder.value.stop()
    }
    return
  }

  recordingState.value = 'requesting'
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/webm'
    const recorder = new MediaRecorder(stream, { mimeType })

    audioChunks.value = []
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.value.push(e.data)
    }

    recorder.onstop = () => {
      stream.getTracks().forEach(t => t.stop())
      finishRecording()
    }

    mediaRecorder.value = recorder
    recorder.start()
    recordingState.value = 'recording'
    recordingDuration.value = 0
    recordingTimer = setInterval(() => {
      recordingDuration.value++
    }, 1000)
  } catch (err) {
    console.error('麦克风访问失败:', err)
    recordingState.value = 'idle'
    alert('无法访问麦克风，请检查浏览器权限设置。')
  }
}

function finishRecording() {
  if (recordingTimer) {
    clearInterval(recordingTimer)
    recordingTimer = null
  }
  if (audioChunks.value.length === 0) {
    recordingState.value = 'idle'
    return
  }
  const blob = new Blob(audioChunks.value, { type: 'audio/webm' })
  selectedAudios.value.push(blob)
  audioPreviewUrls.value.push(URL.createObjectURL(blob))
  audioChunks.value = []
  recordingState.value = 'idle'
}

async function handleAudioFileSelect(e) {
  const file = e.target.files?.[0]
  if (!file || !file.type.startsWith('audio/')) return
  selectedAudios.value.push(file)
  audioPreviewUrls.value.push(URL.createObjectURL(file))
  if (audioFileInput.value) audioFileInput.value.value = ''
}

function removeAudio(idx) {
  URL.revokeObjectURL(audioPreviewUrls.value[idx])
  selectedAudios.value.splice(idx, 1)
  audioPreviewUrls.value.splice(idx, 1)
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

async function stopMessage() {
  if (currentRequestId.value) {
    try {
      await fetch('/api/chat/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request_id: currentRequestId.value })
      })
    } catch (e) {
    }
  }
  if (abortController.value) {
    abortController.value.abort()
    abortController.value = null
  }

  chatStore.addMessage({ role: 'assistant', content: '生成已终止。' })

  currentSteps.value = []
  todoList.value = []
  currentRequestId.value = ''
  chatStore.isLoading = false
  chatStore.streamingContent = ''
}

async function clearContext() {
  if (isClearingContext.value) return
  isClearingContext.value = true
  try {
    const response = await fetch('/api/chat/clear', { method: 'POST' })
    if (response.ok) {
      const result = await response.json()
      chatStore.clearMessages()
      currentSteps.value = []
      todoList.value = []
      console.log('上下文已清除:', result.message)
    } else {
      console.error('清除上下文失败:', response.status)
    }
  } catch (e) {
    console.error('清除上下文请求失败:', e)
  } finally {
    isClearingContext.value = false
  }
}

function encodeAudioToBase64(blob) {
  return new Promise((resolve) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve(e.target.result)
    reader.readAsDataURL(blob)
  })
}

async function sendMessage() {
  const text = inputText.value.trim()
  const hasImages = selectedImages.value.length > 0
  const hasAudios = selectedAudios.value.length > 0
  if ((!text && !hasImages && !hasAudios) || chatStore.isLoading) return

  // Compress images to base64
  let imageBase64List = null
  if (hasImages) {
    imageBase64List = await Promise.all(
      selectedImages.value.map(f => compressImage(f))
    )
  }

  // Encode audios to base64
  let audioBase64List = null
  if (hasAudios) {
    audioBase64List = await Promise.all(
      selectedAudios.value.map(f => encodeAudioToBase64(f))
    )
  }

  abortController.value = new AbortController()
  const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 8)}`
  currentRequestId.value = requestId
  currentSteps.value = []
  todoList.value = []

  chatStore.addMessage({ role: 'user', content: text || '(音频)', images: imageBase64List, audios: audioBase64List })
  inputText.value = ''
  // Cleanup image previews
  previewUrls.value.forEach(url => URL.revokeObjectURL(url))
  selectedImages.value = []
  previewUrls.value = []
  // Cleanup audio previews
  audioPreviewUrls.value.forEach(url => URL.revokeObjectURL(url))
  selectedAudios.value = []
  audioPreviewUrls.value = []
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
  }
  scrollToBottom()

  chatStore.isLoading = true
  chatStore.setError(null)

  let finalOutput = ''

  try {
    const body = {
      messages: [{ role: 'user', content: text || '请转写这段音频' }],
      request_id: requestId,
      use_rag: true,
      stream: true,
      show_thinking: true,
      llm_provider: settingsStore.llmProvider,
      llm_model: settingsStore.activeModel,
      llm_api_key: settingsStore.apiKey || undefined,
      llm_api_base_url: settingsStore.activeApiUrl || undefined,
      llm_temperature: settingsStore.temperature,
      llm_max_tokens: settingsStore.maxTokens,
      image_describer_backend: settingsStore.imageDescriberBackend
    }
    if (settingsStore.bailianApiKey) {
      body.bailian_api_key = settingsStore.bailianApiKey
    }
    if (imageBase64List) {
      body.images = imageBase64List
    }
    if (audioBase64List) {
      body.audios = audioBase64List
    }
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: abortController.value.signal
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `HTTP ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const event = JSON.parse(line.slice(6))
          switch (event.type) {
            case 'step': {
              currentSteps.value.push({
                thought: event.thought || '',
                action: event.action || '',
                action_input: event.action_input || '',
                observation: null
              })
              break
            }
            case 'observation': {
              const steps = currentSteps.value
              for (let i = steps.length - 1; i >= 0; i--) {
                if (steps[i].observation == null) {
                  steps[i].observation = event.observation || ''
                  break
                }
              }
              break
            }
            case 'todo':
              todoList.value = event.tasks || []
              break
            case 'finish':
              finalOutput = event.output || ''
              break
            case 'cancelled':
              finalOutput = ''
              break
            case 'error':
              finalOutput = ''
              break
          }
          scrollToBottom()
        } catch (e) {
          // 忽略 JSON 解析错误的行
        }
      }
    }

    // 完成 — 仅保留最终答案
    if (finalOutput) {
      chatStore.addMessage({ role: 'assistant', content: finalOutput, images: imageBase64List })
    } else if (currentSteps.value.length > 0) {
      chatStore.addMessage({ role: 'assistant', content: '请求已完成', images: imageBase64List })
    }
  } catch (error) {
    chatStore.streamingContent = ''
    if (error.name === 'AbortError') {
      chatStore.addMessage({ role: 'assistant', content: '生成已终止。', images: imageBase64List })
    } else {
      console.error('发送消息失败:', error)
      chatStore.setError(error.message || '发送失败')
      chatStore.addMessage({
        role: 'assistant',
        content: '抱歉，消息发送失败了。请检查网络连接和后端服务是否正常运行。',
        images: imageBase64List
      })
    }
  } finally {
    currentSteps.value = []
    todoList.value = []
    abortController.value = null
    currentRequestId.value = ''
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
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.clear-context-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f9fafb;
  color: #6b7280;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.clear-context-btn:hover:not(:disabled) {
  background: #fee2e2;
  border-color: #fca5a5;
  color: #ef4444;
}

.clear-context-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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
  flex-direction: column;
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

/* Markdown 渲染样式 */
.assistant-bubble :deep(h1) { font-size: 1.3em; font-weight: 700; margin: 12px 0 6px; }
.assistant-bubble :deep(h2) { font-size: 1.15em; font-weight: 700; margin: 10px 0 5px; }
.assistant-bubble :deep(h3) { font-size: 1.05em; font-weight: 600; margin: 8px 0 4px; }
.assistant-bubble :deep(p) { margin: 4px 0; }
.assistant-bubble :deep(ul), .assistant-bubble :deep(ol) { padding-left: 20px; margin: 4px 0; }
.assistant-bubble :deep(li) { margin: 2px 0; }
.assistant-bubble :deep(strong) { font-weight: 600; color: #111; }
.assistant-bubble :deep(hr) { border: none; border-top: 1px solid #ddd; margin: 10px 0; }
.assistant-bubble :deep(code) { background: #e8e8e8; padding: 1px 5px; border-radius: 3px; font-size: 0.9em; }
.assistant-bubble :deep(pre) { background: #2d2d2d; color: #f0f0f0; padding: 10px 14px; border-radius: 6px; overflow-x: auto; margin: 8px 0; }
.assistant-bubble :deep(pre code) { background: transparent; padding: 0; }
.assistant-bubble :deep(a) { color: #2563eb; text-decoration: underline; }
.assistant-bubble :deep(blockquote) { border-left: 3px solid #ccc; padding-left: 12px; margin: 6px 0; color: #555; }
.assistant-bubble :deep(*:first-child) { margin-top: 0; }
.assistant-bubble :deep(*:last-child) { margin-bottom: 0; }

.msg-images {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}

.msg-image {
  max-width: 240px;
  max-height: 320px;
  border-radius: 10px;
  border: 1px solid #e0e0e0;
  object-fit: contain;
  cursor: pointer;
  transition: transform 0.15s;
}

.msg-image:hover {
  transform: scale(1.03);
}

.todo-card {
  padding: 12px 16px;
  border-radius: 12px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  font-size: 13px;
  max-width: 85%;
}

.todo-header {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #22c55e;
  margin-bottom: 8px;
}

.todo-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 4px 0;
}

.todo-icon {
  flex-shrink: 0;
  width: 18px;
  font-size: 13px;
  text-align: center;
  line-height: 1.6;
}

.todo-pending .todo-icon { color: #a0a0a0; }
.todo-in_progress .todo-icon { color: #f59e0b; animation: spin 2s linear infinite; }
.todo-completed .todo-icon { color: #22c55e; }

.todo-content {
  color: #333;
  line-height: 1.6;
}

.todo-done {
  color: #a0a0a0;
  text-decoration: line-through;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.thought-bubble {
  padding: 10px 14px;
  border-radius: 12px;
  background: #faf5ff;
  border: 1px solid #e9d5ff;
  font-size: 13px;
  line-height: 1.6;
  color: #4a3560;
  max-width: 85%;
}

.thought-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #a78bfa;
  margin-bottom: 4px;
}

.thought-text {
  white-space: pre-wrap;
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

.image-preview-row {
  display: flex;
  gap: 6px;
  padding: 0 0 4px 0;
  overflow-x: auto;
  flex-shrink: 0;
}

.preview-thumb {
  position: relative;
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #e0e0e0;
}

.preview-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.remove-img-btn {
  position: absolute;
  top: 0px;
  right: 0px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgba(0,0,0,0.55);
  color: #fff;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
  font-size: 10px;
}

.remove-img-btn:hover {
  background: rgba(0,0,0,0.8);
}

.attach-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: transparent;
  color: #888888;
  border: 1px solid #dddddd;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.15s;
}

.attach-btn:hover:not(:disabled) {
  background: #f0f0f0;
  color: #333333;
  border-color: #999999;
}

.attach-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
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

/* 图片灯箱 */
.lightbox-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  cursor: zoom-out;
}

.lightbox-image {
  max-width: 90vw;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 8px;
  cursor: default;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.5);
}

.lightbox-close {
  position: fixed;
  top: 20px;
  right: 20px;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
  cursor: pointer;
  transition: background 0.2s;
  z-index: 10000;
}

.lightbox-close:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* --- Audio Preview Row --- */
.audio-preview-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 0 0 4px 0;
  flex-shrink: 0;
}

.preview-audio-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
}

.audio-preview-player {
  flex: 1;
  height: 32px;
  border-radius: 6px;
}

/* --- Audio Recording --- */
.recording-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 0 6px 0;
  flex-shrink: 0;
}

.recording-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ef4444;
  animation: pulse-recording 1s ease-in-out infinite;
  flex-shrink: 0;
}

@keyframes pulse-recording {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.3); opacity: 0.5; }
}

.recording-timer {
  font-size: 14px;
  font-weight: 600;
  color: #ef4444;
  font-variant-numeric: tabular-nums;
}

.recording-hint {
  font-size: 12px;
  color: #999;
  margin-left: 4px;
}

/* Mic button states */
.mic-btn.is-recording {
  background: #fee2e2;
  color: #ef4444;
  border-color: #fca5a5;
  animation: mic-pulse 1.2s ease-in-out infinite;
}

@keyframes mic-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.3); }
  50% { box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }
}

/* --- Audio in Messages --- */
.msg-audios {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}

.msg-audio {
  max-width: 280px;
  height: 32px;
  border-radius: 8px;
}
</style>
