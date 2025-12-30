<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const handleBackButton = () => {
  router.push('/history')
}

onMounted(() => {
  if (window.Telegram?.WebApp) {
    window.Telegram.WebApp.BackButton.onClick(handleBackButton)

    // Apply Telegram theme
    const root = document.documentElement
    const theme = window.Telegram.WebApp.themeParams

    if (theme.bg_color) root.style.setProperty('--tg-theme-bg-color', theme.bg_color)
    if (theme.text_color) root.style.setProperty('--tg-theme-text-color', theme.text_color)
    if (theme.hint_color) root.style.setProperty('--tg-theme-hint-color', theme.hint_color)
    if (theme.link_color) root.style.setProperty('--tg-theme-link-color', theme.link_color)
    if (theme.button_color) root.style.setProperty('--tg-theme-button-color', theme.button_color)
    if (theme.button_text_color) root.style.setProperty('--tg-theme-button-text-color', theme.button_text_color)
    if (theme.secondary_bg_color) root.style.setProperty('--tg-theme-secondary-bg-color', theme.secondary_bg_color)
  }
})

onUnmounted(() => {
  if (window.Telegram?.WebApp) {
    window.Telegram.WebApp.BackButton.offClick(handleBackButton)
  }
})
</script>

<template>
  <router-view />
</template>
