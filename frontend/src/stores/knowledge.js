import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useKnowledgeStore = defineStore('knowledge', () => {
  const items = ref([])
  const queryResults = ref([])

  function setItems(list) {
    items.value = list
  }

  function setQueryResults(results) {
    queryResults.value = results
  }

  return {
    items,
    queryResults,
    setItems,
    setQueryResults
  }
})
