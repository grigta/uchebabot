<template>
  <v-app>
    <template v-if="authStore.isAuthenticated">
      <v-app-bar color="primary" density="compact">
        <v-app-bar-nav-icon @click="drawer = !drawer" />
        <v-app-bar-title>EduHelper Admin</v-app-bar-title>
        <v-spacer />
        <v-btn icon="mdi-logout" @click="logout" />
      </v-app-bar>

      <v-navigation-drawer v-model="drawer">
        <v-list nav>
          <v-list-item
            prepend-icon="mdi-view-dashboard"
            title="Dashboard"
            to="/"
          />
          <v-list-item
            prepend-icon="mdi-account-group"
            title="Users"
            to="/users"
          />
        </v-list>
      </v-navigation-drawer>
    </template>

    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const drawer = ref(true)

function logout() {
  authStore.logout()
  router.push('/login')
}
</script>
