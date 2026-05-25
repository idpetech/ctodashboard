// Import React hooks we need
import { useState, useEffect } from 'react'
import LoadingSpinner from './components/LoadingSpinner'
import ChatbotButton from './components/ChatbotButton'

// Define what an Assignment looks like (now with rich configuration)
interface Assignment {
  id: string
  name: string
  status: string
  start_date: string
  end_date: string | null
  monthly_burn_rate: number
  team_size: number
  description: string
  metrics_config: {
    github: { enabled: boolean; org: string; repos: string[] }
    jira: { enabled: boolean; project_key: string }
    aws: { enabled: boolean; account_id?: string; services?: string[] }
    railway: { enabled: boolean; project_id?: string }
    openai: { enabled: boolean; api_dashboard_url?: string; track_usage?: boolean; track_costs?: boolean }
  }
  team: {
    roles: string[]
    tech_stack: string[]
  }
}

// Define metrics response structure
interface AssignmentMetrics {
  timestamp: string
  assignment_id: string
  github?: any[]
  jira?: any
  aws?: any
  railway?: any
  openai?: any
}

function TabbedApp() {
  // Get API URL from environment variable - use relative paths for single app deployment
  const API_URL = import.meta.env.VITE_API_URL || ''
  
  // Store list of assignments from API
  const [assignments, setAssignments] = useState<Assignment[]>([])
  // Store metrics for each assignment
  const [metrics, setMetrics] = useState<{ [key: string]: AssignmentMetrics }>({})
  // Track if we're still loading data
  const [loading, setLoading] = useState(true)
  // Track loading state for individual metrics
  const [metricsLoading, setMetricsLoading] = useState<{ [key: string]: boolean }>({})
  // Store any error messages
  const [error, setError] = useState<string | null>(null)
  // Track expanded sections for each assignment and service
  const [expandedSections, setExpandedSections] = useState<{ [key: string]: boolean }>({})
  // Track active tab
  const [activeTab, setActiveTab] = useState<string>('overview')

  // Run this code when component first loads
  useEffect(() => {
    const loadAssignmentsAndMetrics = async () => {
      try {
        console.log('Loading assignments from:', `${API_URL}/api/assignments`)
        const assignmentsResponse = await fetch(`${API_URL}/api/assignments`)
        const assignmentsData = await assignmentsResponse.json()
        console.log('Assignments loaded:', assignmentsData)
        setAssignments(assignmentsData)

        // Set loading state for all assignments
        const loadingState: { [key: string]: boolean } = {}
        assignmentsData.forEach((assignment: Assignment) => {
          loadingState[assignment.id] = true
        })
        setMetricsLoading(loadingState)

        // Load metrics for each assignment
        const metricsPromises = assignmentsData.map(async (assignment: Assignment) => {
          try {
            console.log('Loading metrics for:', assignment.id)
            const metricsResponse = await fetch(`${API_URL}/api/assignments/${assignment.id}/metrics`)
            const metricsData = await metricsResponse.json()
            console.log('Metrics loaded for', assignment.id, ':', metricsData)
            
            // Update loading state
            setMetricsLoading(prev => ({ ...prev, [assignment.id]: false }))
            
            return { [assignment.id]: metricsData }
          } catch (error) {
            console.warn(`Failed to load metrics for ${assignment.id}:`, error)
            setMetricsLoading(prev => ({ ...prev, [assignment.id]: false }))
            return { [assignment.id]: { timestamp: new Date().toISOString(), assignment_id: assignment.id } }
          }
        })

        const metricsResults = await Promise.all(metricsPromises)
        const combinedMetrics = Object.assign({}, ...metricsResults)
        setMetrics(combinedMetrics)
        setLoading(false)
      } catch (error) {
        console.error('Error loading dashboard:', error)
        setError(error instanceof Error ? error.message : 'Unknown error')
        setLoading(false)
      }
    }

    loadAssignmentsAndMetrics()
  }, [API_URL])

  // Helper function to toggle section expansion
  const toggleSection = (assignmentId: string, section: string) => {
    const key = `${assignmentId}_${section}`
    setExpandedSections(prev => ({
      ...prev,
      [key]: !prev[key]
    }))
  }

  // Helper function to generate overview content
  const generateOverviewContent = () => {
    const activeCount = assignments.filter(a => a.status === 'active').length
    const totalBurnRate = assignments.reduce((sum, a) => sum + a.monthly_burn_rate, 0)
    const totalTeamSize = assignments.reduce((sum, a) => sum + a.team_size, 0)

    return (
      <div className="space-y-6">
        {/* Overview Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-2xl font-bold text-blue-600">{assignments.length}</div>
            <div className="text-sm text-gray-600">Total Projects</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-2xl font-bold text-green-600">{activeCount}</div>
            <div className="text-sm text-gray-600">Active Projects</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-2xl font-bold text-purple-600">${totalBurnRate.toLocaleString()}</div>
            <div className="text-sm text-gray-600">Total Monthly Burn</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-2xl font-bold text-orange-600">{totalTeamSize}</div>
            <div className="text-sm text-gray-600">Total Team Size</div>
          </div>
        </div>

        {/* Project Summary Cards */}
        <div className="grid gap-4">
          {assignments.map(assignment => (
            <div key={assignment.id} className="bg-white p-4 rounded-lg shadow">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold text-gray-900">{assignment.name}</h3>
                  <p className="text-sm text-gray-600">{assignment.description}</p>
                  <div className="flex items-center mt-2 space-x-2">
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      assignment.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {assignment.status}
                    </span>
                    <span className="text-xs text-gray-500">
                      {assignment.team_size} people
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-semibold">${assignment.monthly_burn_rate.toLocaleString()}</div>
                  <div className="text-xs text-gray-500">monthly</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // Show loading spinner while data is being fetched
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <LoadingSpinner message="Loading CTO Dashboard..." size="lg" variant="hourglass" />
      </div>
    )
  }

  // Show error message if something went wrong
  if (error) {
    return (
      <div className="p-4 text-red-500">
        Error: {error}
      </div>
    )
  }

  // Show message if no assignments found
  if (assignments.length === 0) {
    return (
      <div className="p-4">
        <h1 className="text-2xl font-bold mb-4">CTO Dashboard - Debug Mode</h1>
        <div className="bg-gray-100 p-4 rounded">
          <p>No assignments loaded. Debug info:</p>
          <p>API URL: {API_URL}</p>
          <p>Loading state: {loading ? 'true' : 'false'}</p>
          <p>Error: {error || 'none'}</p>
          <p>Check browser console for more details.</p>
          <button 
            onClick={() => window.location.reload()} 
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  // Main dashboard display with tabs
  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-6xl mx-auto">
        {/* Page title */}
        <h1 className="text-3xl font-bold text-gray-900 mb-8">
          CTO Dashboard
        </h1>
        
        {/* Tab Navigation */}
        <div className="bg-white rounded-lg shadow-lg mb-6">
          <div className="flex border-b border-gray-200">
            {/* Overview Tab */}
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'overview'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-700 hover:text-blue-600 hover:border-blue-300'
              }`}
            >
              📊 Overview ({assignments.length})
            </button>
            
            {/* Individual Assignment Tabs */}
            {assignments.map(assignment => {
              const statusEmoji = assignment.status === 'active' ? '🟢' : 
                                 assignment.status === 'completed' ? '🔵' : '🟡'
              return (
                <button
                  key={assignment.id}
                  onClick={() => setActiveTab(`assignment-${assignment.id}`)}
                  className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === `assignment-${assignment.id}`
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-700 hover:text-blue-600 hover:border-blue-300'
                  }`}
                >
                  {statusEmoji} {assignment.name}
                </button>
              )
            })}
          </div>
        </div>

        {/* Tab Content */}
        <div className="tab-content">
          {activeTab === 'overview' && generateOverviewContent()}
          {assignments.map(assignment => {
            if (activeTab === `assignment-${assignment.id}`) {
              const assignmentMetrics = metrics[assignment.id]
              return (
                <div key={assignment.id} className="space-y-6">
                  {/* Assignment Header */}
                  <div className="bg-white rounded-lg shadow-lg p-6">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h2 className="text-xl font-semibold text-gray-900">{assignment.name}</h2>
                        <p className="text-sm text-gray-600 mt-1">{assignment.description}</p>
                        <span className={`inline-block px-2 py-1 text-xs rounded-full mt-2 ${
                          assignment.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {assignment.status}
                        </span>
                      </div>
                      <div className="text-right">
                        <div className="text-sm text-gray-500">Monthly Burn Rate</div>
                        <div className="text-lg font-semibold">${assignment.monthly_burn_rate.toLocaleString()}</div>
                      </div>
                    </div>

                    {/* Team and tech info */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                      <div>
                        <div className="text-sm text-gray-500">Team Size</div>
                        <div className="font-medium">{assignment.team_size} people</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500">Start Date</div>
                        <div className="font-medium">{new Date(assignment.start_date).toLocaleDateString()}</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500">Tech Stack</div>
                        <div className="font-medium">{assignment.team.tech_stack.slice(0, 3).join(', ')}</div>
                      </div>
                    </div>

                    {/* Service status badges */}
                    <div className="flex flex-wrap gap-2 mb-4">
                      {assignment.metrics_config.github.enabled && (
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                          📊 GitHub ({assignment.metrics_config.github.repos.length} repos)
                        </span>
                      )}
                      {assignment.metrics_config.jira.enabled && (
                        <span className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded">
                          🎯 Jira ({assignment.metrics_config.jira.project_key})
                        </span>
                      )}
                      {assignment.metrics_config.aws.enabled && (
                        <span className="px-2 py-1 bg-orange-100 text-orange-800 text-xs rounded">
                          ☁️ AWS {assignment.metrics_config.aws.services ? `(${assignment.metrics_config.aws.services.length} services)` : ''}
                        </span>
                      )}
                      {assignment.metrics_config.railway.enabled && (
                        <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                          🚂 Railway
                        </span>
                      )}
                      {assignment.metrics_config.openai.enabled && (
                        <span className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded">
                          🤖 OpenAI
                        </span>
                      )}
                    </div>

                    {/* Metrics section */}
                    {(assignmentMetrics || metricsLoading[assignment.id]) && (
                      <div className="border-t border-gray-200 pt-4">
                        {metricsLoading[assignment.id] ? (
                          <div className="flex items-center justify-center py-8">
                            <LoadingSpinner message="Loading metrics..." size="md" variant="spinner" />
                          </div>
                        ) : (
                          <div>
                            <div className="text-sm text-gray-500 mb-4">
                              Latest Metrics (Updated: {new Date(assignmentMetrics.timestamp).toLocaleString()})
                            </div>

                            {/* GitHub Metrics */}
                            {assignment.metrics_config.github.enabled ? (
                              assignmentMetrics.github ? (
                                // Check if all repos have errors
                                assignmentMetrics.github.every((repo: any) => repo.error) ? (
                                  <div className="mb-3 p-2 text-sm text-orange-600">
                                    📊 GitHub: Failing - {assignmentMetrics.github[0]?.error || 'Check API configuration'}
                                  </div>
                                ) : (
                                  <div className="mb-3">
                                    <button
                                      onClick={() => toggleSection(assignment.id, 'github')}
                                      className="flex items-center justify-between w-full text-left text-sm text-gray-700 hover:text-gray-900 p-2 rounded hover:bg-gray-50"
                                    >
                                      <span>📊 GitHub: {assignmentMetrics.github.filter((repo: any) => !repo.error).length} repositories tracked</span>
                                      <span className="text-xs text-gray-400">
                                        {expandedSections[`${assignment.id}_github`] ? '▼' : '▶'}
                                      </span>
                                    </button>
                                    {expandedSections[`${assignment.id}_github`] && (
                                      <div className="ml-4 mt-2 space-y-2">
                                        {assignmentMetrics.github.map((repo: any, index: number) => (
                                          <div key={index} className="bg-gray-50 p-3 rounded text-xs">
                                            {repo.error ? (
                                              <div className="text-red-600">❌ {repo.error}</div>
                                            ) : (
                                              <>
                                                <div className="font-medium text-gray-900">{repo.repo_name}</div>
                                                <div className="grid grid-cols-2 gap-2 mt-1 text-gray-600">
                                                  <div>Commits (30d): {repo.commits_last_30_days}</div>
                                                  <div>Language: {repo.language}</div>
                                                  <div>Stars: {repo.stars}</div>
                                                  <div>Open Issues: {repo.open_issues}</div>
                                                  <div>Pull Requests: {repo.total_prs}</div>
                                                  <div>Last Updated: {new Date(repo.last_updated).toLocaleDateString()}</div>
                                                </div>
                                              </>
                                            )}
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                )
                              ) : (
                                <div className="mb-3 p-2 text-sm text-orange-600">
                                  📊 GitHub: Failing - Check API configuration
                                </div>
                              )
                            ) : (
                              <div className="mb-3 p-2 text-sm text-gray-500">
                                📊 GitHub: Not Configured
                              </div>
                            )}

                            {/* AWS Metrics */}
                            {assignment.metrics_config.aws.enabled ? (
                              assignmentMetrics.aws ? (
                                assignmentMetrics.aws.error ? (
                                  <div className="mb-3 p-2 text-sm text-orange-600">
                                    ☁️ AWS: Failing - {assignmentMetrics.aws.error}
                                  </div>
                                ) : (
                                  <div className="mb-3">
                                    <button
                                      onClick={() => toggleSection(assignment.id, 'aws')}
                                      className="flex items-center justify-between w-full text-left text-sm text-gray-700 hover:text-gray-900 p-2 rounded hover:bg-gray-50"
                                    >
                                      <span>☁️ AWS: Cost tracking active - ${assignmentMetrics.aws.total_cost_last_30_days} (30d)</span>
                                      <span className="text-xs text-gray-400">
                                        {expandedSections[`${assignment.id}_aws`] ? '▼' : '▶'}
                                      </span>
                                    </button>
                                    {expandedSections[`${assignment.id}_aws`] && (
                                      <div className="ml-4 mt-2">
                                        <div className="bg-gray-50 p-3 rounded text-xs">
                                          <div className="space-y-3">
                                            <div className="border-b border-gray-200 pb-2">
                                              <div className="font-semibold text-gray-800 mb-1">💰 Cost Summary</div>
                                              <div className="grid grid-cols-2 gap-2 text-gray-600">
                                                <div>Total Cost (30d): ${assignmentMetrics.aws.total_cost_last_30_days}</div>
                                                <div>Period: {assignmentMetrics.aws.period}</div>
                                              </div>
                                            </div>
                                            <div className="border-b border-gray-200 pb-2">
                                              <div className="font-semibold text-gray-800 mb-1">🔝 Top Services</div>
                                              <div className="space-y-1">
                                                {Object.entries(assignmentMetrics.aws.top_services || {}).map(([service, cost]: [string, any]) => (
                                                  <div key={service} className="flex justify-between text-gray-600">
                                                    <span className="truncate flex-1 mr-2">{service}</span>
                                                    <span className="font-medium">${cost}</span>
                                                  </div>
                                                ))}
                                              </div>
                                            </div>
                                          </div>
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                )
                              ) : (
                                <div className="mb-3 p-2 text-sm text-orange-600">
                                  ☁️ AWS: Failing - Check API configuration
                                </div>
                              )
                            ) : (
                              <div className="mb-3 p-2 text-sm text-gray-500">
                                ☁️ AWS: Not Configured
                              </div>
                            )}

                            {/* Jira Metrics */}
                            {assignment.metrics_config.jira.enabled ? (
                              assignmentMetrics.jira ? (
                                assignmentMetrics.jira.error ? (
                                  <div className="mb-3 p-2 text-sm text-orange-600">
                                    🎯 Jira: Failing - {assignmentMetrics.jira.error}
                                  </div>
                                ) : (
                                  <div className="mb-3 p-2 text-sm text-green-600">
                                    🎯 Jira: Connected - Project {assignmentMetrics.jira.project_name}
                                  </div>
                                )
                              ) : (
                                <div className="mb-3 p-2 text-sm text-orange-600">
                                  🎯 Jira: Failing - Check API configuration
                                </div>
                              )
                            ) : (
                              <div className="mb-3 p-2 text-sm text-gray-500">
                                🎯 Jira: Not Configured
                              </div>
                            )}

                            {/* Railway Metrics */}
                            {assignment.metrics_config.railway.enabled ? (
                              assignmentMetrics.railway ? (
                                assignmentMetrics.railway.error ? (
                                  <div className="mb-3 p-2 text-sm text-orange-600">
                                    🚂 Railway: Failing - {assignmentMetrics.railway.error}
                                  </div>
                                ) : (
                                  <div className="mb-3 p-2 text-sm text-green-600">
                                    🚂 Railway: Connected - Project {assignmentMetrics.railway.project_name}
                                  </div>
                                )
                              ) : (
                                <div className="mb-3 p-2 text-sm text-orange-600">
                                  🚂 Railway: Failing - Check API configuration
                                </div>
                              )
                            ) : (
                              <div className="mb-3 p-2 text-sm text-gray-500">
                                🚂 Railway: Not Configured
                              </div>
                            )}

                            {/* OpenAI Metrics */}
                            {assignment.metrics_config.openai.enabled ? (
                              assignmentMetrics.openai ? (
                                assignmentMetrics.openai.error ? (
                                  <div className="mb-3 p-2 text-sm text-orange-600">
                                    🤖 OpenAI: Failing - {assignmentMetrics.openai.error}
                                  </div>
                                ) : (
                                  <div className="mb-3">
                                    <button
                                      onClick={() => toggleSection(assignment.id, 'openai')}
                                      className="flex items-center justify-between w-full text-left text-sm text-gray-700 hover:text-gray-900 p-2 rounded hover:bg-gray-50"
                                    >
                                      <span>🤖 OpenAI: Active - ${assignmentMetrics.openai.usage_this_month?.estimated_cost || 0} this month</span>
                                      <span className="text-xs text-gray-400">
                                        {expandedSections[`${assignment.id}_openai`] ? '▼' : '▶'}
                                      </span>
                                    </button>
                                    {expandedSections[`${assignment.id}_openai`] && (
                                      <div className="ml-4 mt-2">
                                        <div className="bg-gray-50 p-3 rounded text-xs">
                                          <div className="space-y-3">
                                            <div className="border-b border-gray-200 pb-2">
                                              <div className="font-semibold text-gray-800 mb-1">📊 Usage Summary</div>
                                              <div className="grid grid-cols-2 gap-2 text-gray-600">
                                                <div>Tokens Used: {assignmentMetrics.openai.usage_this_month?.tokens_used?.toLocaleString()}</div>
                                                <div>Requests: {assignmentMetrics.openai.usage_this_month?.requests_made}</div>
                                                <div>Estimated Cost: ${assignmentMetrics.openai.usage_this_month?.estimated_cost}</div>
                                                <div>Status: {assignmentMetrics.openai.status}</div>
                                              </div>
                                            </div>
                                            <div className="border-b border-gray-200 pb-2">
                                              <div className="font-semibold text-gray-800 mb-1">🔧 Models Used</div>
                                              <div className="text-gray-600">
                                                {assignmentMetrics.openai.models_used?.join(', ')}
                                              </div>
                                            </div>
                                            <div>
                                              <div className="font-semibold text-gray-800 mb-1">🔗 Dashboard</div>
                                              <a 
                                                href={assignmentMetrics.openai.dashboard_url} 
                                                target="_blank" 
                                                rel="noopener noreferrer"
                                                className="text-blue-600 hover:underline text-xs"
                                              >
                                                View OpenAI Dashboard →
                                              </a>
                                            </div>
                                            <div>
                                              <div className="font-semibold text-gray-800 mb-1">💰 Billing</div>
                                              <a 
                                                href={assignmentMetrics.openai.billing_url} 
                                                target="_blank" 
                                                rel="noopener noreferrer"
                                                className="text-blue-600 hover:underline text-xs"
                                              >
                                                Check Account Balance →
                                              </a>
                                            </div>
                                            {assignmentMetrics.openai.period && (
                                              <div className="text-xs text-gray-500 mt-2">
                                                Period: {assignmentMetrics.openai.period}
                                              </div>
                                            )}
                                            {assignmentMetrics.openai.note && (
                                              <div className="text-xs text-orange-600 mt-2 p-2 bg-orange-50 rounded">
                                                ℹ️ {assignmentMetrics.openai.note}
                                              </div>
                                            )}
                                          </div>
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                )
                              ) : (
                                <div className="mb-3 p-2 text-sm text-orange-600">
                                  🤖 OpenAI: Failing - Check API configuration
                                </div>
                              )
                            ) : (
                              <div className="mb-3 p-2 text-sm text-gray-500">
                                🤖 OpenAI: Not Configured
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )
            }
            return null
          })}
        </div>

        {/* Chatbot Button */}
        <ChatbotButton apiUrl={API_URL} />
      </div>
    </div>
  )
}

export default TabbedApp