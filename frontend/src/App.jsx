import { useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function App() {
  const [status, setStatus] = useState('idle')
  const [backendHealth, setBackendHealth] = useState(null)

  const checkHealth = async () => {
    setStatus('loading')
    try {
      const res = await fetch(`${API_URL}/health`)
      const data = await res.json()
      setBackendHealth(data)
      setStatus('ok')
    } catch (error) {
      setBackendHealth({ error: String(error) })
      setStatus('error')
    }
  }

  return (
    <main className="page">
      <section className="card">
        <h1>Goldenizacja Frontend</h1>
        <p>Prosty frontend React do testu połączenia z backendem FastAPI.</p>
        <button onClick={checkHealth} disabled={status === 'loading'}>
          {status === 'loading' ? 'Sprawdzam...' : 'Sprawdź /health'}
        </button>
        <pre>{backendHealth ? JSON.stringify(backendHealth, null, 2) : 'Brak wyniku'}</pre>
      </section>
    </main>
  )
}
