export const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '')
export const BILL_UPLOAD_ENABLED = import.meta.env.VITE_ENABLE_BILL_UPLOAD !== 'false'
