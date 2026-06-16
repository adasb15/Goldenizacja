import { useState } from 'react'

import { API_URL } from './api/serving'
import { GoldenRecordsView } from './features/golden-records/GoldenRecordsView'
import { MatchingView } from './features/matching/MatchingView'
import { ValidationView } from './features/validation/ValidationView'

const HERO_BY_VIEW = {
  'golden-records': {
    title: 'Lista golden rekordów',
    copy: 'Tabela rekordów golden oparta o endpoint warstwy serving.',
  },
  validation: {
    title: 'Widok walidacji',
    copy: 'Tabela wyników walidacji oparta o endpoint warstwy serving.',
  },
  matching: {
    title: 'Widok matchingu',
    copy: 'Tabela kandydatów matchingu oparta o endpointy Levenshtein i Jaro-Winkler.',
  },
}

export default function App() {
  const [activeView, setActiveView] = useState('golden-records')
  const [refreshToken, setRefreshToken] = useState(0)

  function refreshData() {
    setRefreshToken((current) => current + 1)
  }

  const hero = HERO_BY_VIEW[activeView]

  return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">React serving console</p>
          <h1>{hero.title}</h1>
          <p className="hero__copy">{hero.copy}</p>
        </div>

        <div className="hero__actions">
          <div className="api-target">
            <span>API</span>
            <strong>{API_URL}</strong>
          </div>

          <button type="button" className="button" onClick={refreshData}>
            Odśwież dane
          </button>
        </div>
      </section>

      <section className="workspace">
        <div className="segmented">
          <button
            type="button"
            className={activeView === 'golden-records' ? 'segmented__item is-active' : 'segmented__item'}
            onClick={() => setActiveView('golden-records')}
          >
            Golden Records
          </button>
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

        {activeView === 'golden-records' ? (
          <GoldenRecordsView refreshToken={refreshToken} />
        ) : activeView === 'validation' ? (
          <ValidationView refreshToken={refreshToken} />
        ) : (
          <MatchingView refreshToken={refreshToken} />
        )}
      </section>
    </main>
  )
}
