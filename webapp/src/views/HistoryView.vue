<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { solutionsApi, type Solution } from '@/api/client'

const router = useRouter()
const solutions = ref<Solution[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const page = ref(1)
const total = ref(0)
const perPage = 20

const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) {
    return 'Сегодня, ' + date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
  } else if (days === 1) {
    return 'Вчера, ' + date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
  } else if (days < 7) {
    return date.toLocaleDateString('ru-RU', { weekday: 'long', hour: '2-digit', minute: '2-digit' })
  } else {
    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
  }
}

const truncateText = (text: string, maxLength: number = 100): string => {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength).trim() + '...'
}

const loadSolutions = async () => {
  try {
    const response = await solutionsApi.getMy(page.value, perPage)
    solutions.value = response.items
    total.value = response.total
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Не удалось загрузить историю'
  } finally {
    loading.value = false
  }
}

const openSolution = (id: number) => {
  router.push(`/solution/${id}`)
}

onMounted(() => {
  loadSolutions()
})
</script>

<template>
  <div class="history-view">
    <h1>История решений</h1>

    <!-- Loading state -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Загрузка...</p>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="solutions.length === 0" class="empty-state">
      <div class="empty-state-icon">📚</div>
      <p>Пока нет решений</p>
      <p>Задай первый вопрос в боте!</p>
    </div>

    <!-- Solutions list -->
    <div v-else class="history-list">
      <div
        v-for="solution in solutions"
        :key="solution.id"
        class="card history-item"
        @click="openSolution(solution.id)"
      >
        <div class="card-header">
          <span v-if="solution.detected_subject" class="subject-badge">
            {{ solution.detected_subject }}
          </span>
          <span class="card-subtitle">{{ formatDate(solution.created_at) }}</span>
        </div>
        <p class="question-preview">{{ truncateText(solution.question) }}</p>
      </div>

      <!-- Pagination info -->
      <div v-if="total > perPage" class="pagination-info">
        Показано {{ solutions.length }} из {{ total }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.history-view h1 {
  margin-bottom: 20px;
  font-size: 1.5rem;
}

.pagination-info {
  text-align: center;
  color: var(--tg-theme-hint-color);
  font-size: 0.875rem;
  padding: 16px 0;
}
</style>
