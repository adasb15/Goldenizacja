import { useState } from 'react'

import { API_URL } from './api/serving'
import { MatchingView } from './features/matching/MatchingView'
import { ValidationView } from './features/validation/ValidationView'

export default function App() {
  const [activeView, setActiveView] = useState('validation')
  const [refreshToken, setRefreshToken] = useState(0)

  function refreshData() {
    setRefreshToken((current) => current + 1)
  }

  const heroTitle = activeView === 'validation' ? 'Widok walidacji' : 'Widok matchingu'
  const heroCopy =
    activeView === 'validation'
      ? 'Tabela wynikow walidacji oparta o endpoint warstwy serving.'
      : 'Tabela kandydatow matchingu oparta o endpointy Levenshtein i Jaro-Winkler.'

  return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">React serving console</p>
          <h1>{heroTitle}</h1>
          <p className="hero__copy">{heroCopy}</p>
        </div>

        <div className="hero__actions">
          <div className="api-target">
            <span>API</span>
            <strong>{API_URL}</strong>
          </div>

          <button type="button" className="button" onClick={refreshData}>
            Odswiez dane
          </button>
        </div>
      </section>

      <section className="workspace">
        <div className="segmented">
          <button
            type="button"
            className={activeView === 'validation' ? 'segmented__item is-active' : 'segmented__item'}
            onClick={() => setActiveView('validation')}
          >
            Walidacja
          </button>
          <button
            type="button"
            className={activeView === 'matching' ? 'segmented__item is-active' : 'segmented__item'}
            onClick={() => setActiveView('matching')}
          >
            Matching
          </button>
        </div>

        {activeView === 'validation' ? (
          <ValidationView refreshToken={refreshToken} />
        ) : (
          <MatchingView refreshToken={refreshToken} />
        )}
      </section>
    </main>
  )
}
