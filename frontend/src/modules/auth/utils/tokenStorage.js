const ACCESS_TOKEN_KEY = 'erp_access_token'
const REFRESH_TOKEN_KEY = 'erp_refresh_token'
const USER_EMAIL_KEY = 'erp_user_email'

const hasWindow = typeof window !== 'undefined'

export function readStoredSession() {
  if (!hasWindow) {
    return null
  }

  const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY)
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
  const userEmail = localStorage.getItem(USER_EMAIL_KEY)

  if (!accessToken || !refreshToken) {
    return null
  }

  return { accessToken, refreshToken, userEmail }
}

export function writeStoredSession({ accessToken, refreshToken, userEmail }) {
  if (!hasWindow || !accessToken || !refreshToken) {
    return
  }

  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)

  if (userEmail) {
    localStorage.setItem(USER_EMAIL_KEY, userEmail)
  }
}

export function clearStoredSession() {
  if (!hasWindow) {
    return
  }

  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(USER_EMAIL_KEY)
}
