import axios from 'axios'
import { API_BASE_URL } from '@/config/env'
import { notifyGlobalApiError } from '@/api/errors'

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  withCredentials: true,
})

const refreshApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  withCredentials: true,
})

export function setupApiInterceptors({ onAuthFailed }) {
  const requestInterceptor = api.interceptors.request.use((config) => config)

  const responseInterceptor = api.interceptors.response.use(
    (response) => response,
    async (error) => {
      const status = error?.response?.status
      const originalRequest = error?.config
      const suppressGlobalErrorToast = originalRequest?.suppressGlobalErrorToast

      if (!originalRequest || status !== 401 || originalRequest._retry) {
        notifyGlobalApiError(error, { suppressGlobalErrorToast })
        return Promise.reject(error)
      }

      if (
        originalRequest.url?.includes('/token/refresh/') ||
        originalRequest.url?.includes('/token/') ||
        originalRequest.url?.includes('/auth/logout/') ||
        originalRequest.url?.includes('/auth/me/')
      ) {
        onAuthFailed()
        notifyGlobalApiError(error, { suppressGlobalErrorToast })
        return Promise.reject(error)
      }

      originalRequest._retry = true

      try {
        await refreshApi.post('/token/refresh/', {})

        return api(originalRequest)
      } catch (refreshError) {
        onAuthFailed()
        notifyGlobalApiError(refreshError, {
          fallback: 'Tu sesion expiro. Inicia sesion nuevamente.',
          suppressGlobalErrorToast,
        })
        return Promise.reject(refreshError)
      }
    },
  )

  return () => {
    api.interceptors.request.eject(requestInterceptor)
    api.interceptors.response.eject(responseInterceptor)
  }
}
