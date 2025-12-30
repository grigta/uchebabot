import { createRouter, createWebHistory } from 'vue-router'
import SolutionView from '@/views/SolutionView.vue'
import HistoryView from '@/views/HistoryView.vue'

const router = createRouter({
  history: createWebHistory('/webapp/'),
  routes: [
    {
      path: '/',
      redirect: '/history'
    },
    {
      path: '/solution/:id',
      name: 'solution',
      component: SolutionView,
      props: true
    },
    {
      path: '/history',
      name: 'history',
      component: HistoryView
    }
  ]
})

// Handle Telegram back button
router.afterEach((to, from) => {
  if (window.Telegram?.WebApp) {
    if (to.name === 'history') {
      window.Telegram.WebApp.BackButton.hide()
    } else {
      window.Telegram.WebApp.BackButton.show()
    }
  }
})

export default router
