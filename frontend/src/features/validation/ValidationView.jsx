import { useEffect, useState } from 'react'

import { getValidationResults } from '../../api/serving'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { EMPTY_VALIDATION_PAGE, VALIDATION_LIMIT } from '../../constants/validation'
import { formatDateTime, formatValue } from '../../utils/formatters'

function ValidationView({ refreshToken }) {
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
        const data = await getValidationResults({ limit: VALIDATION_LIMIT, offset: 0 })

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
  }, [refreshToken])

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

            {state.data.items.map((item) => (
              <tr key={item.validation_id}>
                <td>{item.validation_id}</td>
                <td>{item.source_system_code || '-'}</td>
                <td>{item.entity_type}</td>
                <td>{item.rule_code}</td>
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
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export { ValidationView }
