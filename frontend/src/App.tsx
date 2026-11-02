import { useEffect, useState } from 'react'
import './App.css'

type User = { id: number; email: string }
type Template = { id: number; name: string }
type LaunchItem = {
  index: number
  status: string
  external_campaign_id: string | null
  error_message: string | null
}
type Launch = { id: number; status: string; count: number; items: LaunchItem[] }
type ApiError = { detail?: string | { msg?: string }[] }

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = sessionStorage.getItem('access_token')
  const headers = new Headers(init.headers)
  if (init.body) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(path, { ...init, headers })
  const data = await response.json().catch(() => ({})) as T & ApiError

  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((item) => item.msg).filter(Boolean).join(', ')
      : data.detail
    throw new Error(detail || `Ошибка запроса (${response.status})`)
  }

  return data
}

function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem('access_token'))
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isRegistering, setIsRegistering] = useState(false)
  const [user, setUser] = useState<User | null>(null)
  const [templates, setTemplates] = useState<Template[]>([])
  const [templateName, setTemplateName] = useState('')
  const [campaignName, setCampaignName] = useState('')
  const [budget, setBudget] = useState('')
  const [geo, setGeo] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState('')
  const [launchCount, setLaunchCount] = useState('1')
  const [launch, setLaunch] = useState<Launch | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  async function loadDashboard() {
    const [currentUser, savedTemplates] = await Promise.all([
      api<User>('/users/me'),
      api<Template[]>('/templates'),
    ])
    setUser(currentUser)
    setTemplates(savedTemplates)
    if (savedTemplates.length) setSelectedTemplate(String(savedTemplates[0].id))
  }

  useEffect(() => {
    if (!token) return
    void loadDashboard().catch((err: unknown) => {
      sessionStorage.removeItem('access_token')
      setToken(null)
      setError(err instanceof Error ? err.message : 'Не удалось загрузить аккаунт')
    })
  }, [])

  async function handleLogin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (isRegistering) {
        await api<User>('/register', {
          method: 'POST',
          body: JSON.stringify({ email, password }),
        })
      }
      const result = await api<{ access_token: string }>('/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      sessionStorage.setItem('access_token', result.access_token)
      setToken(result.access_token)
      setPassword('')
      await loadDashboard()
      setNotice(isRegistering ? 'Аккаунт создан' : '')
    } catch (err) {
      sessionStorage.removeItem('access_token')
      setToken(null)
      setError(err instanceof Error ? err.message : 'Не удалось войти')
    } finally {
      setBusy(false)
    }
  }

  async function handleCreateTemplate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const created = await api<Template>('/templates', {
        method: 'POST',
        body: JSON.stringify({
          name: templateName,
          settings: {
            name: campaignName,
            budget: Number(budget),
            geo: geo.split(',').map((place) => place.trim()).filter(Boolean),
          },
        }),
      })
      setTemplates((previous) => [created, ...previous])
      setSelectedTemplate(String(created.id))
      setTemplateName('')
      setCampaignName('')
      setBudget('')
      setGeo('')
      setNotice('Шаблон создан')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать шаблон')
    } finally {
      setBusy(false)
    }
  }

  async function handleLaunch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const accepted = await api<{ id: number }>('/launches', {
        method: 'POST',
        body: JSON.stringify({
          template_id: Number(selectedTemplate),
          count: Number(launchCount),
        }),
      })
      const status = await api<Launch>(`/launches/${accepted.id}`)
      setLaunch(status)
      setNotice(`Задача #${status.id} создана`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось запустить задачу')
    } finally {
      setBusy(false)
    }
  }

  async function refreshLaunch() {
    if (!launch) return
    setError('')
    try {
      setLaunch(await api<Launch>(`/launches/${launch.id}`))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось обновить задачу')
    }
  }

  function handleLogout() {
    sessionStorage.removeItem('access_token')
    setToken(null)
    setUser(null)
    setTemplates([])
    setLaunch(null)
    setNotice('')
  }

  if (!token) {
    return (
      <main className="auth-card">
        <h1>{isRegistering ? 'Создать аккаунт' : 'Вход'}</h1>
        <form onSubmit={handleLogin}>
          <label htmlFor="email">Email</label>
          <input id="email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
          <label htmlFor="password">Пароль</label>
          <input id="password" type="password" autoComplete={isRegistering ? 'new-password' : 'current-password'} minLength={isRegistering ? 8 : undefined} required value={password} onChange={(event) => setPassword(event.target.value)} />
          {error && <p className="error-message" role="alert">{error}</p>}
          <button type="submit" disabled={busy}>{busy ? 'Подождите…' : isRegistering ? 'Зарегистрироваться' : 'Войти'}</button>
        </form>
        <button className="text-button" type="button" onClick={() => { setIsRegistering(!isRegistering); setError('') }}>
          {isRegistering ? 'Уже есть аккаунт? Войти' : 'Нет аккаунта? Зарегистрироваться'}
        </button>
      </main>
    )
  }

  return (
    <main className="dashboard">
      <header className="topbar">
        <div><strong>Campaign Launcher</strong><span>{user?.email ?? 'Загружаем аккаунт…'}</span></div>
        <button className="secondary-button" type="button" onClick={handleLogout}>Выйти</button>
      </header>

      {error && <p className="error-message banner" role="alert">{error}</p>}
      {notice && <p className="notice-message" role="status">{notice}</p>}

      <section className="panel">
        <h1>Шаблоны кампаний</h1>
        {templates.length === 0 ? <p>Шаблонов пока нет — создай первый ниже.</p> : (
          <ul className="template-list">
            {templates.map((item) => <li key={item.id}><span>{item.name}</span><small>#{item.id}</small></li>)}
          </ul>
        )}
      </section>

      <div className="content-grid">
        <section className="panel">
          <h2>Создать шаблон</h2>
          <form onSubmit={handleCreateTemplate}>
            <label htmlFor="template-name">Название шаблона</label>
            <input id="template-name" required value={templateName} onChange={(event) => setTemplateName(event.target.value)} placeholder="Например, Летняя кампания" />
            <label htmlFor="campaign-name">Название кампании</label>
            <input id="campaign-name" required value={campaignName} onChange={(event) => setCampaignName(event.target.value)} placeholder="Название для рекламной платформы" />
            <label htmlFor="budget">Бюджет</label>
            <input id="budget" type="number" min="0.01" step="0.01" required value={budget} onChange={(event) => setBudget(event.target.value)} />
            <label htmlFor="geo">Гео (через запятую)</label>
            <input id="geo" required value={geo} onChange={(event) => setGeo(event.target.value)} placeholder="US, CA" />
            <button type="submit" disabled={busy}>{busy ? 'Сохраняем…' : 'Сохранить шаблон'}</button>
          </form>
        </section>

        <section className="panel">
          <h2>Запустить кампанию</h2>
          {templates.length === 0 ? <p>Сначала создай шаблон.</p> : (
            <form onSubmit={handleLaunch}>
              <label htmlFor="template-select">Шаблон</label>
              <select id="template-select" required value={selectedTemplate} onChange={(event) => setSelectedTemplate(event.target.value)}>
                {templates.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
              <label htmlFor="launch-count">Количество кампаний</label>
              <input id="launch-count" type="number" min="1" required value={launchCount} onChange={(event) => setLaunchCount(event.target.value)} />
              <button type="submit" disabled={busy}>{busy ? 'Запускаем…' : 'Запустить'}</button>
            </form>
          )}

          {launch && (
            <div className="job-card">
              <div className="job-heading"><strong>Задача #{launch.id}</strong><span>{launch.status}</span></div>
              <p>Кампаний: {launch.count}</p>
              <button className="secondary-button" type="button" onClick={() => void refreshLaunch()}>Обновить статус</button>
              {launch.items.map((item) => (
                <div className="job-item" key={item.index}>
                  <span>Кампания {item.index + 1}: {item.status}</span>
                  {item.error_message && <small className="error-message">{item.error_message}</small>}
                  {item.external_campaign_id && <small>ID: {item.external_campaign_id}</small>}
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <section className="panel tiktok-placeholder">
        <h2>Подключение TikTok</h2>
        <p>Ожидаем одобрения приложения. Сейчас запуск выполняется через тестовую платформу.</p>
      </section>
    </main>
  )
}

export default App
