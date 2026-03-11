import axios from 'axios'
import { API_BASE_URL } from '@/config/env'
import { notifyGlobalApiError } from '@/api/errors'

function getCookieValue(name) {
  if (typeof document === 'undefined' || !document.cookie) {
    return null
  }

  const encodedName = `${encodeURIComponent(name)}=`
  const found = document.cookie
    .split(';')
    .map((entry) => entry.trim())
    .find((entry) => entry.startsWith(encodedName))

  if (!found) {
    return null
  }

  return decodeURIComponent(found.slice(encodedName.length))
}

function withCsrfHeader(config) {
  const method = String(config?.method || 'get').toUpperCase()
  const isUnsafe = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)
  if (!isUnsafe) {
    return config
  }

  const csrfToken = getCookieValue('csrftoken')
  if (!csrfToken) {
    return config
  }

  return {
    ...config,
    headers: {
      ...(config?.headers || {}),
      'X-CSRFToken': csrfToken,
    },
  }
}

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
  const requestInterceptor = api.interceptors.request.use(withCsrfHeader)
  const refreshRequestInterceptor = refreshApi.interceptors.request.use(withCsrfHeader)

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
    refreshApi.interceptors.request.eject(refreshRequestInterceptor)
    api.interceptors.response.eject(responseInterceptor)
  }
}
