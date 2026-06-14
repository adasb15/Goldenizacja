import { useEffect } from 'react'

import { StatusBadge } from '../../components/ui/StatusBadge'
import { formatValue } from '../../utils/formatters'
import { formatMatchScore } from '../../utils/matching'

function normalizeFieldName(fieldName) {
  return String(fieldName || '')
    .replace(/_Normalized/g, '')
    .replace(/_JSON/g, '')
    .replace(/_/g, ' ')
    .trim()
}

function toLookup(values) {
  return new Set((values || []).map((value) => String(value).toUpperCase()))
}

function getFieldCategory(fieldName, comparison) {
  const normalized = normalizeFieldName(fieldName).replace(/ /g, '_').toUpperCase()
  const strong = toLookup(comparison?.levenshtein?.strong_match_fields)
  const conflict = toLookup(comparison?.levenshtein?.conflict_fields)
  const text = toLookup(comparison?.jaro_winkler?.text_match_fields)

  if (strong.has(normalized)) {
    return { label: 'SILNE', tone: 'strong' }
  }

  if (conflict.has(normalized)) {
    return { label: 'KONFLIKT', tone: 'conflict' }
  }

  if (text.has(normalized)) {
    return { label: 'TEKST', tone: 'text' }
  }

  return null
}

function buildRows(comparison) {
  const leftRecord = comparison?.left_record || {}
  const rightRecord = comparison?.right_record || {}
  const keys = Array.from(new Set([...Object.keys(leftRecord), ...Object.keys(rightRecord)])).sort()

  return keys.map((key) => {
    const leftValue = leftRecord[key]
    const rightValue = rightRecord[key]
    const same = formatValue(leftValue) === formatValue(rightValue)

    return {
      field: key,
      leftValue,
      rightValue,
      same,
      category: getFieldCategory(key, comparison),
    }
  })
}

function MatchingComparisonPanel({ comparison, onClose }) {
  const rows = comparison.data ? buildRows(comparison.data) : []

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    document.body.classList.add('modal-open')

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.classList.remove('modal-open')
    }
  }, [onClose])

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <section className="comparison comparison-modal" onClick={(event) => event.stopPropagation()}>
        <div className="comparison__header">
          <div>
            <p className="eyebrow">Record comparison</p>
            <h2>Szczegóły porównania rekordów</h2>
          </div>

          <button type="button" className="button button--secondary" onClick={onClose}>
            Zamknij
          </button>
        </div>

        {comparison.status === 'loading' ? (
          <div className="banner">Ładowanie szczegółów porównania...</div>
        ) : null}

        {comparison.status === 'error' ? (
          <div className="banner banner--danger">Błąd porównania: {comparison.error}</div>
        ) : null}

        {comparison.data ? (
          <>
            <div className="comparison-summary-grid">
              <article className="comparison-metric">
                <span>Levenshtein</span>
                <strong>{formatMatchScore(comparison.data.levenshtein, 'levenshtein')}</strong>
                <StatusBadge value={comparison.data.levenshtein?.decision || 'BRAK'} />
              </article>

              <article className="comparison-metric">
                <span>Drugie sito</span>
                <strong>{comparison.data.jaro_winkler ? 'TAK' : 'NIE'}</strong>
                <StatusBadge value={comparison.data.jaro_winkler ? comparison.data.jaro_winkler.decision : 'BRAK'} />
              </article>
            </div>

            <div className="table-wrap comparison-modal__table">
              <table>
                <thead>
                  <tr>
                    <th>Pole</th>
                    <th>Lewa wartość</th>
                    <th>Prawa wartość</th>
                    <th>Porównanie</th>
                    <th>Kategoria</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.field} className={row.same ? 'comparison-row comparison-row--same' : ''}>
                      <td>{normalizeFieldName(row.field)}</td>
                      <td className="cell-break">{formatValue(row.leftValue)}</td>
                      <td className="cell-break">{formatValue(row.rightValue)}</td>
                      <td>
                        <StatusBadge value={row.same ? 'ZGODNE' : 'RÓŻNICA'} />
                      </td>
                      <td>
                        {row.category ? (
                          <span className={`match-field-chip match-field-chip--${row.category.tone}`}>
                            {row.category.label}
                          </span>
                        ) : (
                          <span className="match-field-list__empty">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : null}
      </section>
    </div>
  )
}

export { MatchingComparisonPanel }
