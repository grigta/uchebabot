<template>
  <v-container>
    <h1 class="text-h4 mb-6">Dashboard</h1>

    <v-row>
      <v-col cols="12" md="4">
        <v-card>
          <v-card-text>
            <div class="text-overline">Daily Active Users</div>
            <div class="text-h3">{{ stats.dau }}</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card>
          <v-card-text>
            <div class="text-overline">Monthly Active Users</div>
            <div class="text-h3">{{ stats.mau }}</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card>
          <v-card-text>
            <div class="text-overline">Total Users</div>
            <div class="text-h3">{{ stats.total_users }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-4">
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Requests</v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item>
                <template #prepend>
                  <v-icon color="primary">mdi-calendar-today</v-icon>
                </template>
                <v-list-item-title>Today</v-list-item-title>
                <template #append>
                  <span class="text-h6">{{ stats.requests_today }}</span>
                </template>
              </v-list-item>
              <v-list-item>
                <template #prepend>
                  <v-icon color="primary">mdi-calendar-week</v-icon>
                </template>
                <v-list-item-title>This Week</v-list-item-title>
                <template #append>
                  <span class="text-h6">{{ stats.requests_week }}</span>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Popular Subjects</v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item
                v-for="subject in stats.popular_subjects"
                :key="subject.subject"
              >
                <v-list-item-title>{{ subject.subject }}</v-list-item-title>
                <template #append>
                  <v-chip size="small" color="primary">
                    {{ subject.count }}
                  </v-chip>
                </template>
              </v-list-item>
              <v-list-item v-if="!stats.popular_subjects.length">
                <v-list-item-title class="text-grey">
                  No data yet
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api/client'

interface Stats {
  dau: number
  mau: number
  total_users: number
  requests_today: number
  requests_week: number
  popular_subjects: { subject: string; count: number }[]
}

const stats = ref<Stats>({
  dau: 0,
  mau: 0,
  total_users: 0,
  requests_today: 0,
  requests_week: 0,
  popular_subjects: []
})

onMounted(async () => {
  try {
    const response = await api.get('/stats')
    stats.value = response.data
  } catch (e) {
    console.error('Failed to load stats:', e)
  }
})
</script>
