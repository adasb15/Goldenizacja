function formatMatchScore(item, algorithm) {
  if (!item) {
    return '-'
  }

  const score =
    algorithm === 'jaro-winkler'
      ? item.jaro_winkler_score ?? item.levenshtein_score
      : item.levenshtein_score

  return typeof score === 'number' ? score.toFixed(3) : '-'
}

export { formatMatchScore }
