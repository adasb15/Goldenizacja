import { API_URL } from './api/serving'
import { ValidationView } from './features/validation/ValidationView'
import { useState } from 'react'

export default function App() {
  const [refreshToken, setRefreshToken] = useState(0)

  function refreshData() {
    setRefreshToken((current) => current + 1)
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">React serving console</p>
          <h1>Widok walidacji</h1>
          <p className="hero__copy">
            Tabela wynikow walidacji oparta o endpoint warstwy serving.
          </p>
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
        <ValidationView refreshToken={refreshToken} />
      </section>
    </main>
  )
}
