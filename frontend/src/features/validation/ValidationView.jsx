import { useEffect, useState } from 'react'

import { getValidationResults } from '../../api/serving'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { EMPTY_VALIDATION_PAGE, VALIDATION_LIMIT } from '../../constants/validation'
import {
  VALIDATION_ENTITY_OPTIONS,
  VALIDATION_SEVERITY_OPTIONS,
  VALIDATION_STATUS_OPTIONS,
} from '../../constants/validationFilters'
import { formatDateTime, formatValue } from '../../utils/formatters'
import { getValidationHighlight } from './ruleHighlight'

function ValidationView({ refreshToken }) {
  const [filters, setFilters] = useState({
    entity_type: '',
    source_system_code: '',
    rule_code: '',
    status: '',
    severity: '',
  })
  const [query, setQuery] = useState({
    entity_type: '',
    source_system_code: '',
    rule_code: '',
    status: '',
    severity: '',
  })
  const [state, setState] = useState({
    status: 'idle',
    data: EMPTY_VALIDATION_PAGE,
    error: '',
  })

  useEffect(() => {
    let cancelled = false

    async function loadValidation() {
      setState((current) => ({ ...current, status: 'loading', error: '' }))

      try {
        const data = await getValidationResults({
          ...query,
          limit: VALIDATION_LIMIT,
          offset: 0,
        })

        if (!cancelled) {
          setState({ status: 'success', data, error: '' })
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            status: 'error',
            data: EMPTY_VALIDATION_PAGE,
            error: String(error.message || error),
          })
        }
      }
    }

    loadValidation()

    return () => {
      cancelled = true
    }
  }, [query, refreshToken])

  function submitFilters(event) {
    event.preventDefault()
    setQuery(filters)
  }

  return (
    <section className="panel">
      <div className="section-header">
        <div>
          <p className="eyebrow">Validation results</p>
          <h2>Tabela wynikow walidacji</h2>
        </div>
        <span className="section-meta">
          {state.data.page?.total ?? 0} rekordow, pokazane pierwsze {VALIDATION_LIMIT}
        </span>
      </div>

      <form className="filters" onSubmit={submitFilters}>
        <label>
          Zrodlo
          <input
            value={filters.source_system_code}
            onChange={(event) =>
              setFilters((current) => ({
                ...current,
                source_system_code: event.target.value.toUpperCase(),
              }))
            }
            placeholder="np. KRS"
          />
        </label>

        <label>
          Typ encji
          <select
            value={filters.entity_type}
            onChange={(event) =>
              setFilters((current) => ({
                ...current,
                entity_type: event.target.value,
              }))
            }
          >
            {VALIDATION_ENTITY_OPTIONS.map((option) => (
              <option key={option.label} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          Kod bledu
          <input
            value={filters.rule_code}
            onChange={(event) =>
              setFilters((current) => ({
                ...current,
                rule_code: event.target.value.toUpperCase(),
              }))
            }
            placeholder="np. PARTY_NIP_CHECKSUM"
          />
        </label>

        <label>
          Status
          <select
            value={filters.status}
            onChange={(event) =>
              setFilters((current) => ({
                ...current,
                status: event.target.value,
              }))
            }
          >
            {VALIDATION_STATUS_OPTIONS.map((option) => (
              <option key={option.label} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          Severity
          <select
            value={filters.severity}
            onChange={(event) =>
              setFilters((current) => ({
                ...current,
                severity: event.target.value,
              }))
            }
          >
            {VALIDATION_SEVERITY_OPTIONS.map((option) => (
              <option key={option.label} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <button type="submit" className="button">
          Filtruj
        </button>
      </form>

      {state.status === 'error' ? (
        <div className="banner banner--danger">Blad pobierania walidacji: {state.error}</div>
      ) : null}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Zrodlo</th>
              <th>Encja</th>
              <th>Regula</th>
              <th>Pole</th>
              <th>Status</th>
              <th>Severity</th>
              <th>Checked value</th>
              <th>Komunikat</th>
              <th>Utworzono</th>
            </tr>
          </thead>
          <tbody>
            {state.status === 'loading' ? (
              <tr>
                <td colSpan="10" className="table-state">
                  Ladowanie wynikow walidacji...
                </td>
              </tr>
            ) : null}

            {state.status !== 'loading' && state.data.items.length === 0 ? (
              <tr>
                <td colSpan="10" className="table-state">
                  Brak wynikow dla podanych filtrow.
                </td>
              </tr>
            ) : null}

            {state.data.items.map((item) => {
              const highlight = getValidationHighlight(item)
              const rowClassName = highlight ? `validation-row validation-row--${highlight.tone}` : ''

              return (
                <tr key={item.validation_id} className={rowClassName}>
                  <td>{item.validation_id}</td>
                  <td>{item.source_system_code || '-'}</td>
                  <td>{item.entity_type}</td>
                  <td>
                    <div className="rule-cell">
                      <span>{item.rule_code}</span>
                      {highlight ? (
                        <span className={`highlight-chip highlight-chip--${highlight.tone}`}>
                          {highlight.label}
                        </span>
                      ) : null}
                    </div>
                  </td>
                  <td>{item.field_name}</td>
                  <td>
                    <StatusBadge value={item.status} />
                  </td>
                  <td>
                    <StatusBadge value={item.severity} />
                  </td>
                  <td className="cell-break">{formatValue(item.checked_value)}</td>
                  <td className="cell-break">{item.message}</td>
                  <td>{formatDateTime(item.created_at)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export { ValidationView }
