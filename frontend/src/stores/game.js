import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useGameStore = defineStore('game', () => {
  const isGameDetected = ref(false)
  const gameName = ref('')
  const screenCaptures = ref([])
  const showGameOverlay = ref(false)

  const hasActiveGame = computed(() => isGameDetected.value && !!gameName.value)

  function setGameDetected(detected, name = '') {
    isGameDetected.value = detected
    gameName.value = name
  }

  function updateScreenCapture(imageData) {
    screenCaptures.value.unshift({
      id: Date.now().toString(),
      imageData,
      timestamp: new Date().toISOString()
    })
    if (screenCaptures.value.length > 50) {
      screenCaptures.value = screenCaptures.value.slice(0, 50)
    }
  }

  return {
    isGameDetected,
    gameName,
    screenCaptures,
    showGameOverlay,
    hasActiveGame,
    setGameDetected,
    updateScreenCapture
  }
})
