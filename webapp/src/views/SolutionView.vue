<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { solutionsApi, type Solution } from '@/api/client'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'

const route = useRoute()
const solution = ref<Solution | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(async () => {
  try {
    const id = Number(route.params.id)
    solution.value = await solutionsApi.getById(id)
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Не удалось загрузить решение'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="solution-view">
    <!-- Loading state -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Загрузка решения...</p>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="error-state">
      <div class="error-icon">:(</div>
      <p>{{ error }}</p>
    </div>

    <!-- Solution content -->
    <div v-else-if="solution">
      <div class="solution-header">
        <span v-if="solution.detected_subject" class="subject-badge">
          {{ solution.detected_subject }}
        </span>
        <span class="solution-date">{{ formatDate(solution.created_at) }}</span>
      </div>

      <div class="question-section">
        <h3>Вопрос</h3>
        <p class="question-text">{{ solution.question }}</p>
        <span v-if="solution.had_image" class="image-badge">+ Изображение</span>
      </div>

      <div class="answer-section">
        <h3>Решение</h3>
        <MarkdownRenderer :content="solution.answer" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.solution-view {
  padding-bottom: 24px;
}

.solution-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.solution-date {
  color: var(--tg-theme-hint-color);
  font-size: 0.875rem;
}

.question-section {
  background-color: var(--tg-theme-secondary-bg-color);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.question-section h3 {
  font-size: 0.875rem;
  color: var(--tg-theme-hint-color);
  margin-bottom: 8px;
  font-weight: 500;
}

.question-text {
  font-size: 1rem;
  margin-bottom: 0;
}

.image-badge {
  display: inline-block;
  background-color: var(--tg-theme-button-color);
  color: var(--tg-theme-button-text-color);
  padding: 4px 8px;
  border-radius: 8px;
  font-size: 0.75rem;
  margin-top: 8px;
}

.answer-section h3 {
  font-size: 0.875rem;
  color: var(--tg-theme-hint-color);
  margin-bottom: 12px;
  font-weight: 500;
}

.error-icon {
  font-size: 3rem;
  margin-bottom: 16px;
}
</style>
