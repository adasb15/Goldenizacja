import { useEffect, useState } from 'react'

import { getMatchResults } from '../../api/serving'
import { Pager } from '../../components/ui/Pager'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { MATCHING_ALGORITHM_OPTIONS, MATCHING_LIMIT, EMPTY_MATCHING_PAGE } from '../../constants/matching'
import { formatDateTime, formatValue } from '../../utils/formatters'
import { formatMatchScore } from '../../utils/matching'

function MatchFieldList({ values, tone }) {
  if (!values || values.length === 0) {
    return <span className="match-field-list__empty">-</span>
  }

  return (
    <div className="match-field-list">
      {values.map((value) => (
        <span key={value} className={`match-field-chip match-field-chip--${tone}`}>
          {value}
        </span>
      ))}
    </div>
  )
}

function MatchingView({ refreshToken }) {
  const [algorithm, setAlgorithm] = useState('levenshtein')
  const [query, setQuery] = useState({
    algorithm: 'levenshtein',
    offset: 0,
  })
  const [state, setState] = useState({
    status: 'idle',
    data: EMPTY_MATCHING_PAGE,
    error: '',
  })

  useEffect(() => {
    let cancelled = false

    async function loadMatching() {
      setState((current) => ({ ...current, status: 'loading', error: '' }))

      try {
        const data = await getMatchResults({
          algorithm: query.algorithm,
          limit: MATCHING_LIMIT,
          offset: query.offset,
        })

        if (!cancelled) {
          setState({ status: 'success', data, error: '' })
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            status: 'error',
            data: EMPTY_MATCHING_PAGE,
            error: String(error.message || error),
          })
        }
      }
    }

    loadMatching()

    return () => {
      cancelled = true
    }
  }, [query, refreshToken])

  function switchAlgorithm(nextAlgorithm) {
    setAlgorithm(nextAlgorithm)
    setQuery({
      algorithm: nextAlgorithm,
      offset: 0,
    })
  }

  function changePage(direction) {
    setQuery((current) => ({
      ...current,
      offset: Math.max(0, current.offset + direction * MATCHING_LIMIT),
    }))
  }

  const page = state.data.page || EMPTY_MATCHING_PAGE.page
  const currentFrom = page.total === 0 ? 0 : page.offset + 1
  const currentTo = Math.min(page.offset + page.limit, page.total)

  return (
    <section className="panel">
      <div className="section-header">
        <div>
          <p className="eyebrow">Matching results</p>
          <h2>Widok matchingu</h2>
        </div>
        <span className="section-meta">
          {page.total} rekordow, zakres {currentFrom}-{currentTo}
        </span>
      </div>

      <div className="segmented">
        {MATCHING_ALGORITHM_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={algorithm === option.value ? 'segmented__item is-active' : 'segmented__item'}
            onClick={() => switchAlgorithm(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>

      {state.status === 'error' ? (
        <div className="banner banner--danger">Blad pobierania matchingu: {state.error}</div>
      ) : null}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Encja</th>
              <th>Wynik liczbowy</th>
              <th>Decyzja</th>
              <th>Silne pola</th>
              <th>Pola konfliktowe</th>
              <th>Pola tekstowe</th>
              <th>Para rekordow</th>
              <th>Utworzono</th>
            </tr>
          </thead>
          <tbody>
            {state.status === 'loading' ? (
              <tr>
                <td colSpan="9" className="table-state">
                  Ladowanie wynikow matchingu...
                </td>
              </tr>
            ) : null}

            {state.status !== 'loading' && state.data.items.length === 0 ? (
              <tr>
                <td colSpan="9" className="table-state">
                  Brak wynikow matchingu.
                </td>
              </tr>
            ) : null}

            {state.data.items.map((item) => (
              <tr key={`${query.algorithm}-${item.candidate_id}`}>
                <td>{item.candidate_id}</td>
                <td>{item.entity_type}</td>
                <td>{formatMatchScore(item, query.algorithm)}</td>
                <td>
                  <StatusBadge value={item.decision} />
                </td>
                <td className="cell-break">
                  <MatchFieldList values={item.strong_match_fields} tone="strong" />
                </td>
                <td className="cell-break">
                  <MatchFieldList values={item.conflict_fields} tone="conflict" />
                </td>
                <td className="cell-break">{formatValue(item.text_match_fields)}</td>
                <td className="cell-break">
                  {item.left_preprocessed_id} / {item.right_preprocessed_id}
                </td>
                <td>{formatDateTime(item.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pager page={page} onPrev={() => changePage(-1)} onNext={() => changePage(1)} />
    </section>
  )
}

export { MatchingView }
