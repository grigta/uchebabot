import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/client'

export interface User {
  id: number
  telegram_id: number
  username: string | null
  first_name: string | null
  last_name: string | null
  daily_requests: number
  total_requests: number
  total_tokens: number
  is_banned: boolean
  custom_daily_limit: number | null
  created_at: string
  updated_at: string
}

export const useUsersStore = defineStore('users', () => {
  const users = ref<User[]>([])
  const total = ref(0)
  const loading = ref(false)

  async function fetchUsers(page = 1, perPage = 20, search?: string) {
    loading.value = true
    try {
      const params: any = { page, per_page: perPage }
      if (search) params.search = search

      const response = await api.get('/users', { params })
      users.value = response.data.items
      total.value = response.data.total
    } finally {
      loading.value = false
    }
  }

  async function banUser(userId: number) {
    await api.post(`/users/${userId}/ban`)
    await fetchUsers()
  }

  async function unbanUser(userId: number) {
    await api.post(`/users/${userId}/unban`)
    await fetchUsers()
  }

  async function updateUser(userId: number, data: { is_banned?: boolean; custom_daily_limit?: number }) {
    await api.patch(`/users/${userId}`, data)
    await fetchUsers()
  }

  return {
    users,
    total,
    loading,
    fetchUsers,
    banUser,
    unbanUser,
    updateUser
  }
})
