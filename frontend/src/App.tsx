// Import React hooks we need
import { useState, useEffect } from 'react'
import CTOInsightsSection from './components/CTOInsightsSection'

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
}

function App() {
  // Get API URL from environment variable (never hardcode!)
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  
  // Store list of assignments from API
  const [assignments, setAssignments] = useState<Assignment[]>([])
  // Store metrics for each assignment
  const [metrics, setMetrics] = useState<{ [key: string]: AssignmentMetrics }>({})
  // Track if we're still loading data
  const [loading, setLoading] = useState(true)
  // Store any error messages
  const [error, setError] = useState<string | null>(null)
  // Track expanded sections for each assignment and service
  const [expandedSections, setExpandedSections] = useState<{ [key: string]: boolean }>({})

  // Run this code when component first loads
  useEffect(() => {
    const loadAssignmentsAndMetrics = async () => {
      try {
        console.log('Loading assignments from:', `${API_URL}/assignments`)
        // Load assignments first
        const assignmentsResponse = await fetch(`${API_URL}/assignments`)
        const assignmentsData = await assignmentsResponse.json()
        console.log('Assignments loaded:', assignmentsData)
        setAssignments(assignmentsData)
        
        // Load metrics for each assignment
        const metricsPromises = assignmentsData.map(async (assignment: Assignment) => {
          try {
            console.log('Loading metrics for:', assignment.id)
            const metricsResponse = await fetch(`${API_URL}/assignments/${assignment.id}/metrics`)
            const metricsData = await metricsResponse.json()
            console.log('Metrics loaded for', assignment.id, ':', metricsData)
            return { [assignment.id]: metricsData }
          } catch (err) {
            console.warn(`Failed to load metrics for ${assignment.id}:`, err)
            return { [assignment.id]: { timestamp: new Date().toISOString(), assignment_id: assignment.id } }
          }
        })
        
        const metricsResults = await Promise.all(metricsPromises)
        const allMetrics = Object.assign({}, ...metricsResults)
        setMetrics(allMetrics)
        
        setLoading(false)
      } catch (err: any) {
        setError(err.message)
        setLoading(false)
      }
    }
    
    loadAssignmentsAndMetrics()
  }, [API_URL]) // Re-run if API_URL changes

  // Toggle expanded state for a specific section
  const toggleSection = (assignmentId: string, service: string) => {
    const key = `${assignmentId}_${service}`
    setExpandedSections(prev => ({
      ...prev,
      [key]: !prev[key]
    }))
  }

  // Show loading message while waiting
  if (loading) return <div className="p-4">Loading CTO Dashboard...</div>
  // Show error if something went wrong
  if (error) return <div className="p-4 text-red-500">Error: {error}</div>
  
  // Debug display
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

  // Main dashboard display
  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-4xl mx-auto">
        {/* Page title */}
        <h1 className="text-3xl font-bold text-gray-900 mb-8">
          CTO Dashboard
        </h1>
        
        {/* List of assignment cards */}
        <div className="grid gap-6">
          {/* Loop through each assignment and create a card */}
          {assignments.map(assignment => {
            const assignmentMetrics = metrics[assignment.id]
            
            return (
              <div key={assignment.id} className="bg-white rounded-lg shadow-lg p-6">
                {/* Assignment header */}
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900">
                      {assignment.name}
                    </h2>
                    <p className="text-sm text-gray-600 mt-1">
                      {assignment.description}
                    </p>
                    <span className={`inline-block px-2 py-1 text-xs rounded-full mt-2 ${
                      assignment.status === 'active' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {assignment.status}
                    </span>
                  </div>
                  
                  <div className="text-right">
                    <div className="text-sm text-gray-500">Monthly Burn Rate</div>
                    <div className="text-lg font-semibold">
                      ${assignment.monthly_burn_rate.toLocaleString()}
                    </div>
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

                {/* Metrics configuration badges */}
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
                </div>

                {/* Expandable Metrics Data */}
                {assignmentMetrics && (
                  <div className="border-t border-gray-200 pt-4">
                    <div className="text-sm text-gray-500 mb-4">
                      Latest Metrics (Updated: {new Date(assignmentMetrics.timestamp).toLocaleString()})
                    </div>
                    
                    {/* GitHub Metrics - Expandable */}
                    {assignmentMetrics.github && (
                      <div className="mb-3">
                        <button
                          onClick={() => toggleSection(assignment.id, 'github')}
                          className="flex items-center justify-between w-full text-left text-sm text-gray-700 hover:text-gray-900 p-2 rounded hover:bg-gray-50"
                        >
                          <span>📊 GitHub: {assignmentMetrics.github.length} repositories tracked</span>
                          <span className="text-xs text-gray-400">
                            {expandedSections[`${assignment.id}_github`] ? '▼' : '▶'}
                          </span>
                        </button>
                        {expandedSections[`${assignment.id}_github`] && (
                          <div className="ml-4 mt-2 space-y-2">
                            {assignmentMetrics.github.map((repo: any, idx: number) => (
                              <div key={idx} className="bg-gray-50 p-3 rounded text-xs">
                                <div className="font-medium text-gray-900">{repo.repo_name}</div>
                                <div className="grid grid-cols-2 gap-2 mt-1 text-gray-600">
                                  <div>Commits (30d): {repo.commits_last_30_days}</div>
                                  <div>Language: {repo.language}</div>
                                  <div>Stars: {repo.stars}</div>
                                  <div>Open Issues: {repo.open_issues}</div>
                                  <div>Pull Requests: {repo.total_prs}</div>
                                  <div>Last Updated: {new Date(repo.last_updated).toLocaleDateString()}</div>
                                </div>
                                {repo.error && (
                                  <div className="text-red-600 mt-1">Error: {repo.error}</div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* Jira Metrics - Expandable */}
                    {assignmentMetrics.jira && (
                      <div className="mb-3">
                        <button
                          onClick={() => toggleSection(assignment.id, 'jira')}
                          className="flex items-center justify-between w-full text-left text-sm text-gray-700 hover:text-gray-900 p-2 rounded hover:bg-gray-50"
                        >
                          <span>🎯 Jira: Project metrics available</span>
                          <span className="text-xs text-gray-400">
                            {expandedSections[`${assignment.id}_jira`] ? '▼' : '▶'}
                          </span>
                        </button>
                        {expandedSections[`${assignment.id}_jira`] && (
                          <div className="ml-4 mt-2">
                            <div className="bg-gray-50 p-3 rounded text-xs">
                              {assignmentMetrics.jira.error ? (
                                <div className="text-red-600">Error: {assignmentMetrics.jira.error}</div>
                              ) : (
                                <div className="space-y-1 text-gray-600">
                                  <div>Project: {assignmentMetrics.jira.project_name}</div>
                                  <div>Issues (30d): {assignmentMetrics.jira.total_issues_last_30_days}</div>
                                  <div>Resolved (30d): {assignmentMetrics.jira.resolved_issues_last_30_days}</div>
                                  <div>Resolution Rate: {assignmentMetrics.jira.resolution_rate}%</div>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* AWS Metrics - Expandable */}
                    {assignmentMetrics.aws && (
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
                              {assignmentMetrics.aws.error ? (
                                <div className="text-red-600">Error: {assignmentMetrics.aws.error}</div>
                              ) : (
                                <div className="space-y-3">
                                  {/* Basic Cost Info */}
                                  <div className="border-b border-gray-200 pb-2">
                                    <div className="font-semibold text-gray-800 mb-1">💰 Cost Summary</div>
                                    <div className="grid grid-cols-2 gap-2 text-gray-600">
                                      <div>Total Cost (30d): ${assignmentMetrics.aws.total_cost_last_30_days}</div>
                                      <div>Period: {assignmentMetrics.aws.period}</div>
                                      {assignmentMetrics.aws.cto_insights?.cost_trend && (
                                        <>
                                          <div>Trend: {assignmentMetrics.aws.cto_insights.cost_trend.weekly_trend === 'decreasing' ? '📉 Decreasing' : '📈 Increasing'}</div>
                                          <div>Daily Avg: ${assignmentMetrics.aws.cto_insights.cost_trend.daily_average}</div>
                                        </>
                                      )}
                                    </div>
                                  </div>

                                  {/* Top Services */}
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

                                  {/* Resource Details */}
                                  {assignmentMetrics.aws.cto_insights?.resource_inventory && (
                                    <div>
                                      <div className="font-semibold text-gray-800 mb-2">🗃️ Resource Inventory</div>
                                      
                                      {/* Route 53 */}
                                      {assignmentMetrics.aws.cto_insights.resource_inventory.route53?.hosted_zones && (
                                        <div className="mb-2 p-2 bg-blue-50 rounded">
                                          <div className="font-medium text-blue-800">🔗 Route 53 DNS</div>
                                          <div className="text-blue-700 text-xs mt-1">
                                            {assignmentMetrics.aws.cto_insights.resource_inventory.route53.total_hosted_zones} zones (${assignmentMetrics.aws.cto_insights.resource_inventory.route53.total_hosted_zones * 0.5}/month)
                                          </div>
                                          {assignmentMetrics.aws.cto_insights.resource_inventory.route53.hosted_zones.slice(0, 3).map((zone: any) => (
                                            <div key={zone.zone_id} className="text-blue-600 text-xs">
                                              • {zone.name} ({zone.record_count} records)
                                            </div>
                                          ))}
                                        </div>
                                      )}

                                      {/* S3 Storage */}
                                      {assignmentMetrics.aws.cto_insights.resource_inventory.s3?.total_buckets && (
                                        <div className="mb-2 p-2 bg-green-50 rounded">
                                          <div className="font-medium text-green-800">🪣 S3 Storage</div>
                                          <div className="text-green-700 text-xs mt-1">
                                            {assignmentMetrics.aws.cto_insights.resource_inventory.s3.total_buckets} buckets, {assignmentMetrics.aws.cto_insights.resource_inventory.s3.total_size_readable} total
                                          </div>
                                          {assignmentMetrics.aws.cto_insights.resource_inventory.s3.buckets?.slice(0, 3).map((bucket: any) => (
                                            <div key={bucket.name} className="text-green-600 text-xs">
                                              • {bucket.name}: {bucket.size_readable}
                                            </div>
                                          ))}
                                          {assignmentMetrics.aws.cto_insights.resource_inventory.s3.buckets?.length > 3 && (
                                            <div className="text-green-500 text-xs italic">...and {assignmentMetrics.aws.cto_insights.resource_inventory.s3.buckets.length - 3} more</div>
                                          )}
                                        </div>
                                      )}

                                      {/* Lightsail */}
                                      {assignmentMetrics.aws.cto_insights.resource_inventory.lightsail?.error && (
                                        <div className="mb-2 p-2 bg-yellow-50 rounded">
                                          <div className="font-medium text-yellow-800">🚀 Lightsail</div>
                                          <div className="text-yellow-700 text-xs mt-1">
                                            Need additional permissions to view instance details
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  )}

                                  {/* Quick Recommendations */}
                                  {assignmentMetrics.aws.cto_insights?.optimization_recommendations && (
                                    <div className="border-t border-gray-200 pt-2">
                                      <div className="font-semibold text-gray-800 mb-1">💡 Quick Actions</div>
                                      <div className="space-y-1 text-gray-600">
                                        <div className="text-xs">• Review {assignmentMetrics.aws.cto_insights.resource_inventory.route53?.total_hosted_zones || 0} Route53 zones</div>
                                        <div className="text-xs">• Cleanup S3 buckets (lifecycle policies)</div>
                                        <div className="text-xs">• Cost trend: {assignmentMetrics.aws.cto_insights.cost_trend?.weekly_trend || 'stable'}</div>
                                        <button 
                                             className="text-xs text-blue-600 cursor-pointer hover:underline bg-transparent border-none p-0"
                                             onClick={() => toggleSection(assignment.id, 'aws-detailed')}>
                                          → View detailed CTO insights ({expandedSections[`${assignment.id}_aws-detailed`] ? 'Hide' : 'Show'})
                                        </button>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* Railway Metrics - Expandable */}
                    {assignmentMetrics.railway && (
                      <div className="mb-3">
                        <button
                          onClick={() => toggleSection(assignment.id, 'railway')}
                          className="flex items-center justify-between w-full text-left text-sm text-gray-700 hover:text-gray-900 p-2 rounded hover:bg-gray-50"
                        >
                          <span>🚂 Railway: Deployment metrics available</span>
                          <span className="text-xs text-gray-400">
                            {expandedSections[`${assignment.id}_railway`] ? '▼' : '▶'}
                          </span>
                        </button>
                        {expandedSections[`${assignment.id}_railway`] && (
                          <div className="ml-4 mt-2">
                            <div className="bg-gray-50 p-3 rounded text-xs">
                              {assignmentMetrics.railway.error ? (
                                <div className="text-red-600">Error: {assignmentMetrics.railway.error}</div>
                              ) : (
                                <div className="space-y-1 text-gray-600">
                                  <div>Project: {assignmentMetrics.railway.project_name}</div>
                                  <div>Total Deployments: {assignmentMetrics.railway.total_deployments}</div>
                                  <div>Successful: {assignmentMetrics.railway.successful_deployments}</div>
                                  <div>Success Rate: {assignmentMetrics.railway.success_rate}%</div>
                                  {assignmentMetrics.railway.last_deployment && (
                                    <div>Last Deploy: {new Date(assignmentMetrics.railway.last_deployment).toLocaleString()}</div>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Detailed AWS CTO Insights - Expandable */}
                    {assignmentMetrics.aws && expandedSections[`${assignment.id}_aws-detailed`] && (
                      <CTOInsightsSection assignmentId={assignment.id} apiUrl={API_URL} />
                    )}
                    
                    {/* Show placeholder if no metrics configured */}
                    {!assignmentMetrics.github && !assignmentMetrics.jira && !assignmentMetrics.aws && !assignmentMetrics.railway && (
                      <div className="text-sm text-gray-500 italic">
                        Configure API tokens in backend/.env to see live metrics
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default App