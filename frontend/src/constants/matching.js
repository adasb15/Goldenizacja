const MATCHING_LIMIT = 50

const EMPTY_MATCHING_PAGE = {
  items: [],
  page: { limit: MATCHING_LIMIT, offset: 0, total: 0 },
}

const MATCHING_ALGORITHM_OPTIONS = [
  { value: 'levenshtein', label: 'Levenshtein' },
  { value: 'jaro-winkler', label: 'Jaro-Winkler' },
]

export { MATCHING_LIMIT, EMPTY_MATCHING_PAGE, MATCHING_ALGORITHM_OPTIONS }
