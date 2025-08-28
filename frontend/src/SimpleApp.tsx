import { useState, useEffect } from 'react'

function SimpleApp() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  useEffect(() => {
    const loadData = async () => {
      try {
        console.log('Loading from:', API_URL)
        const response = await fetch(`${API_URL}/assignments`)
        console.log('Response status:', response.status)
        const assignments = await response.json()
        console.log('Data loaded:', assignments)
        setData(assignments)
        setLoading(false)
      } catch (err: any) {
        console.error('Error:', err)
        setError(err.message)
        setLoading(false)
      }
    }

    loadData()
  }, [API_URL])

  if (loading) {
    return <div className="p-8">Loading...</div>
  }

  if (error) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-red-600">Error Loading Dashboard</h1>
        <p className="mt-4">Error: {error}</p>
        <p className="mt-2">API URL: {API_URL}</p>
        <button 
          onClick={() => window.location.reload()} 
          className="mt-4 px-4 py-2 bg-blue-500 text-white rounded"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold">No Data Loaded</h1>
        <p>API URL: {API_URL}</p>
        <p>Data: {JSON.stringify(data)}</p>
      </div>
    )
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">CTO Dashboard - Working!</h1>
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold">{data[0].name}</h2>
        <p className="text-gray-600 mt-2">{data[0].description}</p>
        <div className="mt-4">
          <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-sm">
            {data[0].status}
          </span>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-4">
          <div>
            <div className="text-sm text-gray-500">Monthly Burn Rate</div>
            <div className="font-semibold">${data[0].monthly_burn_rate.toLocaleString()}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Team Size</div>
            <div className="font-semibold">{data[0].team_size} people</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SimpleApp