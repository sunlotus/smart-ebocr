// Copyright 2026 smart-ebocr Contributors
// SPDX-License-Identifier: Apache-2.0

import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Usage API
export const usageApi = {
  list: (year, month, familyMemberId) => api.get('/usage/', { params: { year, month, family_member_id: familyMemberId || undefined } }),
  add: (data, familyMemberId) => api.post('/usage/', data, { params: { family_member_id: familyMemberId || undefined } }),
  batchAdd: (records, familyMemberId) => api.post('/usage/batch', { records }, { params: { family_member_id: familyMemberId || undefined } }),
  delete: (date, familyMemberId) => api.delete(`/usage/${date}`, { params: { family_member_id: familyMemberId || undefined } }),
  batchDelete: (dates, familyMemberId) => api.delete('/usage/batch', { data: { dates }, params: { family_member_id: familyMemberId || undefined } }),
  checkConflicts: (dates, familyMemberId) => api.post('/usage/check-conflicts', { dates }, { params: { family_member_id: familyMemberId || undefined } }),
}

// Billing API
export const billingApi = {
  compare: (year, month, familyMemberId) => api.get('/billing/compare', { params: { year, month, family_member_id: familyMemberId || undefined } }),
  annual: (year, familyMemberId) => api.get('/billing/annual', { params: { year, family_member_id: familyMemberId || undefined } }),
}

// Policy API
export const policyApi = {
  get: (params) => api.get('/policy/', { params }),
  update: (data) => api.put('/policy/', data),
}

// Screenshot API
export const screenshotApi = {
  upload: (file, familyMemberId) => {
    const formData = new FormData()
    formData.append('file', file)
    if (familyMemberId) formData.append('family_member_id', familyMemberId)
    return api.post('/screenshot/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    })
  },
  scanDir: (baseDir) => api.get('/screenshot/scan-dir', { params: { base_dir: baseDir } }),
  batchProcess: (directory, year, month, familyMemberId) =>
    api.post('/screenshot/batch', { directory, year, month, family_member_id: familyMemberId || undefined }),
  batchUpload: (files, year, month, familyMemberId) => {
    const formData = new FormData()
    files.forEach(f => formData.append('files', f))
    if (year) formData.append('year', year)
    if (month) formData.append('month', month)
    if (familyMemberId) formData.append('family_member_id', familyMemberId)
    return api.post('/screenshot/batch-upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
  },
  confirm: (records, conflictMode, familyMemberId) => api.post('/screenshot/confirm', {
    records, conflict_mode: conflictMode, family_member_id: familyMemberId || undefined,
  }),
}

// Meters API
export const metersApi = {
  list: () => api.get('/meters/'),
  create: (data) => api.post('/meters/', data),
  get: (id) => api.get(`/meters/${id}`),
  update: (id, data) => api.put(`/meters/${id}`, data),
  delete: (id) => api.delete(`/meters/${id}`),
}

// Advanced Usage API (premium)
export const advancedUsageApi = {
  compareTrend: (year, month, familyMemberId) => api.get('/usage/compare-trend', { params: { year, month, family_member_id: familyMemberId || undefined } }),
  forecast: (year, familyMemberId) => api.get('/usage/forecast', { params: { year, family_member_id: familyMemberId || undefined } }),
}

// Dashboard API (premium)
export const dashboardApi = {
  annualDashboard: (year, familyMemberId) => api.get('/usage/annual-dashboard', { params: { year, family_member_id: familyMemberId || undefined } }),
}

// Advanced Policy API (premium)
export const advancedPolicyApi = {
  list: (familyMemberId) => api.get('/policy/advanced', { params: { family_member_id: familyMemberId || undefined } }),
  create: (data) => api.post('/policy/advanced', data),
  update: (id, data) => api.put(`/policy/advanced/${id}`, data),
  delete: (id) => api.delete(`/policy/advanced/${id}`),
}

// PDF Export API (premium)
export const pdfApi = {
  annualPdf: (year, familyMemberId) => api.get('/billing/annual-pdf', { params: { year, family_member_id: familyMemberId || undefined }, responseType: 'blob' }),
}

/**
 * Create an SSE connection for batch job progress.
 * @param {string} jobId - The batch job ID.
 * @param {function} onProgress - Callback fired on each SSE event with job data.
 * @param {function} onComplete - Callback fired when job status === 'completed'.
 * @param {function} onError - Callback fired on error.
 * @returns {function} Cleanup function to close the EventSource.
 */
export function createBatchSSE(jobId, { onProgress, onComplete, onError }) {
  const es = new EventSource(`/api/screenshot/batch/${jobId}/stream`)

  es.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onProgress?.(data)
      if (data.status === 'completed') {
        es.close()
        onComplete?.(data)
      }
    } catch (e) {
      console.error('SSE parse error:', e)
    }
  }

  es.onerror = () => {
    es.close()
    onError?.(new Error('SSE connection lost'))
  }

  return () => es.close()
}

export default api