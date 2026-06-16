function formatDateTime(value) {
  if (!value) {
    return '-'
  }

  return new Intl.DateTimeFormat('pl-PL', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value))
}

function formatDate(value) {
  if (!value) {
    return '-'
  }

  return new Intl.DateTimeFormat('pl-PL', {
    dateStyle: 'short',
  }).format(new Date(value))
}

function formatValue(value) {
  if (value === null || value === undefined || value === '') {
    return '-'
  }

  if (Array.isArray(value)) {
    return value.length ? value.join(', ') : '-'
  }

  if (typeof value === 'boolean') {
    return value ? 'true' : 'false'
  }

  if (typeof value === 'object') {
    return JSON.stringify(value)
  }

  return String(value)
}

function badgeTone(value) {
  const normalized = String(value || '').toUpperCase()

  if (normalized === 'PASS' || normalized === 'AUTO_MERGE' || normalized === 'POPRAWNY') {
    return 'success'
  }

  if (normalized === 'WARNING' || normalized === 'REVIEW' || normalized === 'CANDIDATE') {
    return 'warning'
  }

  if (normalized === 'ERROR' || normalized === 'NO_MATCH' || normalized === 'CRITICAL' || normalized === 'BŁĘDNY') {
    return 'danger'
  }

  return 'neutral'
}

export { formatDate, formatDateTime, formatValue, badgeTone }
