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

            <!-- Telegram Login Widget placeholder -->
            <div id="telegram-login-widget"></div>

            <!-- For development/testing -->
            <v-btn
              v-if="isDev"
              color="primary"
              class="mt-4"
              @click="devLogin"
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const error = ref('')
const isDev = import.meta.env.DEV

// Telegram callback handler
declare global {
  interface Window {
    onTelegramAuth: (user: any) => void
  }
}

onMounted(() => {
  // Set up Telegram callback
  window.onTelegramAuth = async (user: any) => {
    try {
      await authStore.login(user)
      router.push('/')
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Login failed'
    }
  }

  // Load Telegram widget script
  // In production, uncomment and configure:
  /*
  const script = document.createElement('script')
  script.src = 'https://telegram.org/js/telegram-widget.js?22'
  script.setAttribute('data-telegram-login', 'YOUR_BOT_USERNAME')
  script.setAttribute('data-size', 'large')
  script.setAttribute('data-onauth', 'onTelegramAuth(user)')
  script.setAttribute('data-request-access', 'write')
  document.getElementById('telegram-login-widget')?.appendChild(script)
  */
})

// Development login for testing
async function devLogin() {
  const mockUser = {
    id: 123456789,
    first_name: 'Test',
    last_name: 'Admin',
    username: 'testadmin',
    auth_date: Math.floor(Date.now() / 1000),
    hash: 'dev_hash'
  }

  try {
    await authStore.login(mockUser)
    router.push('/')
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Login failed'
  }
}
</script>
