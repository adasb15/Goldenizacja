import { useEffect, useState } from 'react'

import { getGoldenRecords, getPartyDetail, getPersonDetail } from '../../api/serving'
import { Pager } from '../../components/ui/Pager'
import {
  EMPTY_GOLDEN_RECORDS_PAGE,
  GOLDEN_RECORD_ENTITY_OPTIONS,
  GOLDEN_RECORDS_LIMIT,
} from '../../constants/goldenRecords'
import { formatDateTime, formatValue } from '../../utils/formatters'
import { GoldenRecordDetailModal } from './GoldenRecordDetailModal'

function GoldenRecordsView({ refreshToken }) {
  const [filters, setFilters] = useState({ search: '', entity_type: '' })
  const [query, setQuery] = useState({ search: '', entity_type: '', offset: 0 })
  const [state, setState] = useState({
    status: 'idle',
    data: EMPTY_GOLDEN_RECORDS_PAGE,
    error: '',
  })
  const [detail, setDetail] = useState({
    open: false,
    status: 'idle',
    data: null,
    error: '',
    entityType: '',
    recordId: null,
  })

  useEffect(() => {
    let cancelled = false

    async function loadGoldenRecords() {
      setState((current) => ({ ...current, status: 'loading', error: '' }))

      try {
        const data = await getGoldenRecords({
          search: query.search,
          entity_type: query.entity_type,
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
      entity_type: filters.entity_type,
      offset: 0,
    })
  }

  function clearFilters() {
    setFilters({ search: '', entity_type: '' })
    setQuery({ search: '', entity_type: '', offset: 0 })
  }

  async function openDetail(record) {
    setDetail({
      open: true,
      status: 'loading',
      data: null,
      error: '',
      entityType: record.entity_type,
      recordId: record.record_id,
    })

    try {
      const data =
        record.entity_type === 'PERSON'
          ? await getPersonDetail(record.record_id)
          : await getPartyDetail(record.record_id)

      setDetail({
        open: true,
        status: 'success',
        data,
        error: '',
        entityType: record.entity_type,
        recordId: record.record_id,
      })
    } catch (error) {
      setDetail({
        open: true,
        status: 'error',
        data: null,
        error: String(error.message || error),
        entityType: record.entity_type,
        recordId: record.record_id,
      })
    }
  }

  function closeDetail() {
    setDetail({
      open: false,
      status: 'idle',
      data: null,
      error: '',
      entityType: '',
      recordId: null,
    })
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
            {GOLDEN_RECORD_ENTITY_OPTIONS.map((option) => (
              <option key={option.value || 'ALL'} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
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
              <th></th>
            </tr>
          </thead>
          <tbody>
            {state.status === 'loading' ? (
              <tr>
                <td colSpan="7" className="table-state">
                  Ładowanie golden rekordów...
                </td>
              </tr>
            ) : null}

            {state.status !== 'loading' && state.data.items.length === 0 ? (
              <tr>
                <td colSpan="7" className="table-state">
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
                <td>
                  <button type="button" className="button button--secondary" onClick={() => openDetail(item)}>
                    Szczegóły
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pager page={page} onPrev={() => changePage(-1)} onNext={() => changePage(1)} />

      {detail.open ? <GoldenRecordDetailModal detail={detail} onClose={closeDetail} /> : null}
    </section>
  )
}

export { GoldenRecordsView }
