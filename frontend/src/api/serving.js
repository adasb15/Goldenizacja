const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function buildQuery(params) {
  const query = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value === '' || value === null || value === undefined) {
      return
    }

    query.set(key, String(value))
  })

  const encoded = query.toString()
  return encoded ? `?${encoded}` : ''
}

async function fetchJson(path, params = {}) {
  const response = await fetch(`${API_URL}${path}${buildQuery(params)}`)

  if (!response.ok) {
    let detail = `HTTP ${response.status}`

    try {
      const payload = await response.json()
      detail = payload.detail || payload.message || JSON.stringify(payload)
    } catch {
      detail = response.statusText || detail
    }

    throw new Error(detail)
  }

  return response.json()
}

function getValidationResults(params) {
  return fetchJson('/layers/serving/validation-results', params)
}

function getGoldenRecords(params) {
  return fetchJson('/layers/serving/golden-records', params)
}

function getMatchResults({ algorithm, ...params }) {
  return fetchJson(`/layers/serving/match-results/${algorithm}`, params)
}

function getMatchComparison(params) {
  return fetchJson('/layers/serving/match-results/comparison', params)
}

export { API_URL, getGoldenRecords, getValidationResults, getMatchResults, getMatchComparison }
