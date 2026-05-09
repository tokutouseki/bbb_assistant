import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAudioStore = defineStore('audio', () => {
  const currentAudioUrl = ref(null)
  const isPlaying = ref(false)
  const recordings = ref([])

  const hasAudio = computed(() => !!currentAudioUrl.value)

  function setAudio(url) {
    currentAudioUrl.value = url
    isPlaying.value = true
  }

  function clearCurrentAudio() {
    currentAudioUrl.value = null
    isPlaying.value = false
  }

  function addRecording(recording) {
    recordings.value.unshift(recording)
  }

  return {
    currentAudioUrl,
    isPlaying,
    recordings,
    hasAudio,
    setAudio,
    clearCurrentAudio,
    addRecording
  }
})
