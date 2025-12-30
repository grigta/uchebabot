import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add Telegram initData to all requests
api.interceptors.request.use((config) => {
  if (window.Telegram?.WebApp?.initData) {
    config.headers['X-Telegram-Init-Data'] = window.Telegram.WebApp.initData
  }
  return config
})

export interface Solution {
  id: number
  question: string
  answer: string
  detected_subject: string | null
  had_image: boolean
  created_at: string
}

export interface SolutionListResponse {
  items: Solution[]
  total: number
  page: number
  per_page: number
}

export const solutionsApi = {
  async getMy(page: number = 1, perPage: number = 20): Promise<SolutionListResponse> {
    const response = await api.get<SolutionListResponse>('/solutions/my', {
      params: { page, per_page: perPage }
    })
    return response.data
  },

  async getById(id: number): Promise<Solution> {
    const response = await api.get<Solution>(`/solutions/${id}`)
    return response.data
  }
}

export default api
