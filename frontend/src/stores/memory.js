import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useMemoryStore = defineStore('memory', () => {
  const memoryItems = ref([])
  const userProfile = ref(null)

  function setUserProfile(profile) {
    userProfile.value = profile
  }

  function addMemory(item) {
    memoryItems.value.unshift(item)
  }

  return {
    memoryItems,
    userProfile,
    setUserProfile,
    addMemory
  }
})
