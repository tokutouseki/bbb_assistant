import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const isLoading = ref(false)
  const streamingContent = ref('')
  const currentError = ref(null)

  const agentSkills = ref([
    { id: 'rag', name: '知识库检索', icon: 'book', description: '崩坏3攻略与知识点查询' },
    { id: 'vision', name: '游戏识别', icon: 'eye', description: '识别游戏画面中的元素' },
    { id: 'memory', name: '对话记忆', icon: 'brain', description: '记住之前的对话内容' },
    { id: 'tool', name: '工具调用', icon: 'wrench', description: '调用外部工具完成任务' }
  ])

  const lastMessage = computed(() =>
    messages.value.length > 0 ? messages.value[messages.value.length - 1] : null
  )

  const messageCount = computed(() => messages.value.length)

  function addMessage(message) {
    messages.value.push({
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`,
      timestamp: new Date().toISOString(),
      ...message
    })
  }

  function updateLastAssistantMessage(content) {
    const lastAssistantIndex = [...messages.value].reverse().findIndex(m => m.role === 'assistant')
    if (lastAssistantIndex !== -1) {
      const realIndex = messages.value.length - 1 - lastAssistantIndex
      messages.value[realIndex].content = content
    }
  }

  function setStreaming(content) {
    streamingContent.value = content
  }

  function clearStreaming() {
    const content = streamingContent.value
    if (content) {
      addMessage({ role: 'assistant', content })
    }
    streamingContent.value = ''
  }

  function clearMessages() {
    messages.value = []
    streamingContent.value = ''
    currentError.value = null
  }

  function setError(error) {
    currentError.value = error
  }

  function clearError() {
    currentError.value = null
  }

  return {
    messages,
    isLoading,
    streamingContent,
    currentError,
    agentSkills,
    lastMessage,
    messageCount,
    addMessage,
    updateLastAssistantMessage,
    setStreaming,
    clearStreaming,
    clearMessages,
    setError,
    clearError
  }
})
