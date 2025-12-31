import axios from 'axios'

// In production (served from /admin), API is at root level
// In dev mode, proxy handles /api -> localhost:8000
const baseURL = import.meta.env.PROD ? '/' : '/api'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || baseURL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  console.log('API Request:', config.url, 'Token:', token ? 'present' : 'missing')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      // Always use /admin/login (base path is /admin/ in both dev and prod)
      window.location.href = '/admin/login'
    }
    return Promise.reject(error)
  }
)

export default api
