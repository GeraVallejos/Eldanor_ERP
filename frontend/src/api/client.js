import axios from 'axios'
import { API_BASE_URL } from '@/config/env'

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
})

export function setupApiInterceptors({
  getAccessToken,
  getRefreshToken,
  onTokenRefreshed,
  onAuthFailed,
}) {
  const requestInterceptor = api.interceptors.request.use((config) => {
    const token = getAccessToken()

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    return config
  })

  const responseInterceptor = api.interceptors.response.use(
    (response) => response,
    async (error) => {
      const status = error?.response?.status
      const originalRequest = error?.config

      if (!originalRequest || status !== 401 || originalRequest._retry) {
        return Promise.reject(error)
      }

      if (originalRequest.url?.includes('/token/refresh/')) {
        onAuthFailed()
        return Promise.reject(error)
      }

      const refreshToken = getRefreshToken()

      if (!refreshToken) {
        onAuthFailed()
        return Promise.reject(error)
      }

      originalRequest._retry = true

      try {
        const { data } = await axios.post(`${API_BASE_URL}/token/refresh/`, {
          refresh: refreshToken,
        })

        const nextAccessToken = data?.access
        const nextRefreshToken = data?.refresh || refreshToken

        if (!nextAccessToken) {
          throw new Error('No access token returned from refresh endpoint')
        }

        onTokenRefreshed({
          accessToken: nextAccessToken,
          refreshToken: nextRefreshToken,
        })

        originalRequest.headers.Authorization = `Bearer ${nextAccessToken}`
        return api(originalRequest)
      } catch (refreshError) {
        onAuthFailed()
        return Promise.reject(refreshError)
      }
    },
  )

  return () => {
    api.interceptors.request.eject(requestInterceptor)
    api.interceptors.response.eject(responseInterceptor)
  }
}
