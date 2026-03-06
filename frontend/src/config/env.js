const browserHost = typeof window !== 'undefined' ? window.location.hostname : 'localhost'
const FALLBACK_API_URL = `http://${browserHost}:8000/api`

export const API_BASE_URL =
  import.meta.env.VITE_API_URL?.replace(/\/$/, '') || FALLBACK_API_URL
