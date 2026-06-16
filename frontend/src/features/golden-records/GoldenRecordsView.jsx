import { useEffect, useState } from 'react'

import { getGoldenRecords } from '../../api/serving'
import { Pager } from '../../components/ui/Pager'
import { EMPTY_GOLDEN_RECORDS_PAGE, GOLDEN_RECORDS_LIMIT } from '../../constants/goldenRecords'
import { formatDateTime, formatValue } from '../../utils/formatters'

function GoldenRecordsView({ refreshToken }) {
  const [filters, setFilters] = useState({ search: '' })
  const [query, setQuery] = useState({ search: '', offset: 0 })
  const [state, setState] = useState({
    status: 'idle',
    data: EMPTY_GOLDEN_RECORDS_PAGE,
    error: '',
  })

  useEffect(() => {
    let cancelled = false

    async function loadGoldenRecords() {
      setState((current) => ({ ...current, status: 'loading', error: '' }))

      try {
        const data = await getGoldenRecords({
          search: query.search,
          limit: GOLDEN_RECORDS_LIMIT,
          offset: query.offset,
        })

        if (!cancelled) {
          setState({ status: 'success', data, error: '' })
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            status: 'error',
            data: EMPTY_GOLDEN_RECORDS_PAGE,
            error: String(error.message || error),
          })
        }
      }
    }

    loadGoldenRecords()

    return () => {
      cancelled = true
    }
  }, [query, refreshToken])

  function changePage(direction) {
    setQuery((current) => ({
      ...current,
      offset: Math.max(0, current.offset + direction * GOLDEN_RECORDS_LIMIT),
    }))
  }

  function submitFilters(event) {
    event.preventDefault()
    setQuery({
      search: filters.search.trim(),
      offset: 0,
    })
  }

  function clearFilters() {
    setFilters({ search: '' })
    setQuery({ search: '', offset: 0 })
  }

  const page = state.data.page || EMPTY_GOLDEN_RECORDS_PAGE.page
  const currentFrom = page.total === 0 ? 0 : page.offset + 1
  const currentTo = Math.min(page.offset + page.limit, page.total)

  return (
    <section className="panel">
      <div className="section-header">
        <div>
          <p className="eyebrow">Golden records</p>
          <h2>Lista golden rekordów</h2>
        </div>
        <span className="section-meta">
          {page.total} rekordów, zakres {currentFrom}-{currentTo}
        </span>
      </div>

      <form className="filters" onSubmit={submitFilters}>
        <label>
          Wyszukaj
          <input
            value={filters.search}
            onChange={(event) =>
              setFilters((current) => ({
                ...current,
                search: event.target.value,
              }))
            }
            placeholder="np. Kowalski, PESEL, NIP, REGON, KRS, LEI"
          />
        </label>

        <button type="submit" className="button">
          Szukaj
        </button>

        <button type="button" className="button button--secondary" onClick={clearFilters}>
          Wyczyść
        </button>
      </form>

      {state.status === 'error' ? (
        <div className="banner banner--danger">Błąd pobierania golden rekordów: {state.error}</div>
      ) : null}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Typ encji</th>
              <th>Nazwa</th>
              <th>Główny identyfikator</th>
              <th>Utworzono</th>
              <th>Zaktualizowano</th>
            </tr>
          </thead>
          <tbody>
            {state.status === 'loading' ? (
              <tr>
                <td colSpan="6" className="table-state">
                  Ładowanie golden rekordów...
                </td>
              </tr>
            ) : null}

            {state.status !== 'loading' && state.data.items.length === 0 ? (
              <tr>
                <td colSpan="6" className="table-state">
                  Brak golden rekordów.
                </td>
              </tr>
            ) : null}

            {state.data.items.map((item) => (
              <tr key={`${item.entity_type}-${item.record_id}`}>
                <td>{item.record_id}</td>
                <td>{item.entity_type}</td>
                <td className="cell-break">{formatValue(item.display_name)}</td>
                <td>{formatValue(item.primary_identifier)}</td>
                <td>{formatDateTime(item.created_at)}</td>
                <td>{formatDateTime(item.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pager page={page} onPrev={() => changePage(-1)} onNext={() => changePage(1)} />
    </section>
  )
}

export { GoldenRecordsView }
