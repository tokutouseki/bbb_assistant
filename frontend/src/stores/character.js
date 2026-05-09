import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useCharacterStore = defineStore('character', () => {
  const currentCharacter = ref('kiana')
  const availableCharacters = ref([
    { id: 'kiana', name: '琪亚娜', color: '#f472b6' },
    { id: 'mei', name: '芽衣', color: '#8b5cf6' },
    { id: 'bronya', name: '布洛妮娅', color: '#06b6d4' },
    { id: 'seele', name: '希儿', color: '#10b981' },
    { id: 'rita', name: '丽塔', color: '#ec4899' },
    { id: 'durandal', name: '幽兰黛尔', color: '#f59e0b' }
  ])

  function selectCharacter(id) {
    currentCharacter.value = id
  }

  return {
    currentCharacter,
    availableCharacters,
    selectCharacter
  }
})
