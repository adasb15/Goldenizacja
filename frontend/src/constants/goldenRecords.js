const GOLDEN_RECORDS_LIMIT = 50

const EMPTY_GOLDEN_RECORDS_PAGE = {
  items: [],
  page: { limit: GOLDEN_RECORDS_LIMIT, offset: 0, total: 0 },
}

const GOLDEN_RECORD_ENTITY_OPTIONS = [
  { value: '', label: 'Wszystkie' },
  { value: 'PERSON', label: 'Osoba' },
  { value: 'PARTY', label: 'Podmiot' },
]

export { GOLDEN_RECORDS_LIMIT, EMPTY_GOLDEN_RECORDS_PAGE, GOLDEN_RECORD_ENTITY_OPTIONS }
