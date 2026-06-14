const IDENTIFIER_RULE_MARKERS = ['PESEL', 'NIP', 'REGON', 'KRS', 'LEI']

function getValidationHighlight(item) {
  const ruleCode = String(item.rule_code || '').toUpperCase()
  const isError = String(item.status || '').toUpperCase() === 'ERROR'

  if (ruleCode.startsWith('ADDR_TERYT_')) {
    return {
      tone: isError ? 'teryt-error' : 'teryt',
      label: 'TERYT',
    }
  }

  if (IDENTIFIER_RULE_MARKERS.some((marker) => ruleCode.includes(marker))) {
    return {
      tone: isError ? 'identifier-error' : 'identifier',
      label: 'IDENTYFIKATOR',
    }
  }

  return null
}

export { getValidationHighlight }
