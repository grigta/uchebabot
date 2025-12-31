<template>
  <v-container class="fill-height">
    <v-row justify="center" align="center">
      <v-col cols="12" sm="8" md="4">
        <v-card class="pa-4">
          <v-card-title class="text-center text-h5">
            EduHelper Admin
          </v-card-title>

          <v-card-text class="text-center">
            <p class="mb-4">Sign in with your Telegram account</p>

            <!-- Telegram Login Widget from vue-tg -->
            <LoginWidget
              v-if="botUsername"
              :bot-username="botUsername"
              size="large"
              @auth="onTelegramAuth"
            />

            <v-alert v-else-if="!isDev" type="warning" class="mb-4">
              Bot username not configured (VITE_BOT_USERNAME)
            </v-alert>

            <!-- For development/testing -->
            <v-btn
              v-if="isDev"
              color="primary"
              class="mt-4"
              @click="devLogin"
              :loading="loading"
            >
              Dev Login (Test)
            </v-btn>
          </v-card-text>

          <v-alert v-if="error" type="error" class="mt-4">
            {{ error }}
          </v-alert>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { LoginWidget } from 'vue-tg'
import type { LoginWidgetUser } from 'vue-tg'

const authStore = useAuthStore()
const router = useRouter()
const error = ref('')
const loading = ref(false)
const isDev = import.meta.env.DEV
const botUsername = import.meta.env.VITE_BOT_USERNAME || ''

// Telegram Login Widget callback
async function onTelegramAuth(user: LoginWidgetUser) {
  loading.value = true
  error.value = ''

  try {
    await authStore.login({
      id: user.id,
      first_name: user.first_name,
      last_name: user.last_name,
      username: user.username,
      photo_url: user.photo_url,
      auth_date: user.auth_date,
      hash: user.hash,
    })
    router.push('/')
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Login failed'
  } finally {
    loading.value = false
  }
}

// Development login for testing
async function devLogin() {
  loading.value = true
  error.value = ''

  const mockUser = {
    id: 594887941, // Use actual admin ID from ADMIN_IDS
    first_name: 'Test',
    last_name: 'Admin',
    username: 'testadmin',
    auth_date: Math.floor(Date.now() / 1000),
    hash: 'dev_hash',
  }

  try {
    await authStore.login(mockUser)
    router.push('/')
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>
