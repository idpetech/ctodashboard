import { useState, useEffect } from 'react';

interface CTOInsightsSectionProps {
  assignmentId: string;
  apiUrl: string;
}

interface CTOInsights {
  timestamp: string;
  cost_analysis?: {
    total_cost_30_days: number;
    daily_average: number;
    weekly_trend: string;
    recent_7_days_cost: number;
    previous_7_days_cost: number;
    service_breakdown: { [key: string]: number };
    daily_costs: { date: string; cost: number }[];
    period: string;
  };
  ec2_resources?: {
    total_instances: number;
    running_instances: number;
    stopped_instances: number;
    instances: {
      id: string;
      type: string;
      state: string;
      monthly_cost: number;
    }[];
    suggestions: string[];
  };
  route53_resources?: {
    total_hosted_zones: number;
    hosted_zones: {
      zone_id: string;
      name: string;
      record_count: number;
      private_zone: boolean;
      comment: string;
    }[];
    suggestions: string[];
  };
  s3_resources?: {
    total_buckets: number;
    total_size_readable: string;
    buckets: {
      name: string;
      creation_date: string;
      size_bytes: number;
      size_readable: string;
    }[];
    suggestions: string[];
  };
  rds_resources?: {
    total_databases: number;
    databases: {
      id: string;
      engine: string;
      size: string;
      monthly_cost: number;
    }[];
    suggestions: string[];
  };
  lightsail_resources?: {
    total_instances: number;
    running_instances: number;
    stopped_instances: number;
    estimated_monthly_cost: number;
    instances: {
      name: string;
      bundle_id: string;
      monthly_cost: number;
    }[];
    cost_optimization_suggestions: string[];
  };
  recommendations?: string[];
  assignment_info?: {
    id: string;
    name: string;
    monthly_burn_rate: number;
    team_size: number;
  };
}

const CTOInsightsSection = ({ assignmentId, apiUrl }: CTOInsightsSectionProps) => {
  const [insights, setInsights] = useState<CTOInsights | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCTOInsights = async () => {
      try {
        setLoading(true);
        const url = `${apiUrl}/api/assignments/${assignmentId}/cto-insights`;
        console.log('Fetching CTO insights from:', url);
        
        const response = await fetch(url);
        
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        
        const data = await response.json();
        console.log('CTO insights data received:', data);
        setInsights(data);
        setLoading(false);
      } catch (err: any) {
        console.error('Error fetching CTO insights:', err);
        if (err.name === 'TypeError' && err.message.includes('fetch')) {
          setError('Network error - cannot connect to backend server');
        } else {
          setError(`Load failed: ${err.message}`);
        }
        setLoading(false);
      }
    };

    fetchCTOInsights();
  }, [assignmentId, apiUrl]);

  if (loading) {
    return <div className="ml-4 p-3 bg-gray-50 rounded">Loading detailed CTO insights...</div>;
  }

  if (error) {
    return <div className="ml-4 p-3 bg-gray-50 rounded text-red-600">Error: {error}</div>;
  }

  if (!insights) {
    return <div className="ml-4 p-3 bg-gray-50 rounded text-gray-600">No detailed CTO insights available</div>;
  }

  return (
    <div className="ml-4 mt-4 bg-gray-50 rounded p-4 text-sm border border-gray-200">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">CTO-Level AWS Insights</h3>
      
      {/* Cost Analysis Section */}
      {insights.cost_analysis && (
        <div className="mb-6">
          <h4 className="text-md font-medium text-gray-700 mb-2">💰 Cost Analysis</h4>
          <div className="bg-white p-3 rounded border border-gray-200">
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <span className="text-gray-500 text-xs">Weekly Trend</span>
                <div className="text-sm font-medium">
                  {insights.cost_analysis.weekly_trend === 'decreasing' 
                    ? '📉 Decreasing' 
                    : insights.cost_analysis.weekly_trend === 'increasing' 
                      ? '📈 Increasing' 
                      : '➡️ Stable'}
                </div>
              </div>
              <div>
                <span className="text-gray-500 text-xs">Daily Average</span>
                <div className="text-sm font-medium">${insights.cost_analysis.daily_average}</div>
              </div>
              <div>
                <span className="text-gray-500 text-xs">30-Day Total</span>
                <div className="text-sm font-medium">${insights.cost_analysis.total_cost_30_days}</div>
              </div>
              <div>
                <span className="text-gray-500 text-xs">Period</span>
                <div className="text-sm font-medium">{insights.cost_analysis.period}</div>
              </div>
            </div>
            
            {/* Service Breakdown Chart */}
            <div className="mt-4">
              <div className="text-xs text-gray-500 mb-2">Top Services by Cost</div>
              <div className="space-y-1">
                {Object.entries(insights.cost_analysis.service_breakdown)
                  .sort(([,a], [,b]) => b - a)
                  .slice(0, 5)
                  .map(([service, cost]) => (
                  <div key={service} className="flex justify-between items-center">
                    <span className="text-xs text-gray-600 truncate flex-1 mr-2">{service}</span>
                    <span className="text-xs font-medium">${cost}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Daily Cost Trend */}
            {insights.cost_analysis.daily_costs && insights.cost_analysis.daily_costs.length > 0 && (
              <div className="mt-4">
                <div className="text-xs text-gray-500 mb-1">Last 7 Days Cost Trend</div>
                <div className="flex h-20 items-end space-x-1">
                  {insights.cost_analysis.daily_costs.slice(-7).map((day, index) => {
                    const maxCost = Math.max(...(insights.cost_analysis?.daily_costs?.map(d => d.cost) || [1]));
                    const height = Math.max(5, (day.cost / maxCost) * 100);
                    return (
                      <div key={index} className="flex flex-col items-center flex-1">
                        <div 
                          className="bg-blue-500 w-full rounded-t" 
                          style={{ height: `${height}%` }}
                        ></div>
                        <div className="text-xs mt-1">${day.cost.toFixed(2)}</div>
                        <div className="text-xs text-gray-500">{new Date(day.date).getMonth() + 1}/{new Date(day.date).getDate()}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Resource Inventory Section */}
      <div className="mb-6">
        <h4 className="text-md font-medium text-gray-700 mb-2">🗃️ Resource Inventory</h4>
        
        {/* EC2 Instances */}
        {insights.ec2_resources && (
          <div className="bg-white p-3 rounded border border-gray-200 mb-3">
            <h5 className="font-medium mb-2">🖥️ EC2 Instances ({insights.ec2_resources.total_instances})</h5>
            {insights.ec2_resources.instances && insights.ec2_resources.instances.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-2 py-1 text-left">ID</th>
                      <th className="px-2 py-1 text-left">Type</th>
                      <th className="px-2 py-1 text-left">State</th>
                      <th className="px-2 py-1 text-right">Monthly Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {insights.ec2_resources.instances.map((instance) => (
                      <tr key={instance.id} className="border-t border-gray-100">
                        <td className="px-2 py-1">{instance.id}</td>
                        <td className="px-2 py-1">{instance.type}</td>
                        <td className="px-2 py-1">
                          <span className={`inline-block w-2 h-2 rounded-full mr-1 ${
                            instance.state === 'running' ? 'bg-green-500' : 'bg-gray-400'
                          }`}></span>
                          {instance.state}
                        </td>
                        <td className="px-2 py-1 text-right">${instance.monthly_cost}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-500 text-xs italic">No EC2 instances found - all resources terminated or insufficient permissions.</p>
            )}
            {insights.ec2_resources.suggestions && insights.ec2_resources.suggestions.length > 0 && (
              <div className="mt-2 pt-2 border-t border-gray-100">
                <div className="text-xs text-amber-600">
                  {insights.ec2_resources.suggestions.map((suggestion, idx) => (
                    <div key={idx}>• {suggestion}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Route53 */}
        {insights.route53_resources && (
          <div className="bg-white p-3 rounded border border-gray-200 mb-3">
            <h5 className="font-medium mb-2">🔗 Route 53 DNS Zones ({insights.route53_resources.total_hosted_zones})</h5>
            {insights.route53_resources.hosted_zones && insights.route53_resources.hosted_zones.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-2 py-1 text-left">Domain</th>
                      <th className="px-2 py-1 text-center">Records</th>
                      <th className="px-2 py-1 text-center">Type</th>
                      <th className="px-2 py-1 text-right">Monthly Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {insights.route53_resources.hosted_zones.map((zone) => (
                      <tr key={zone.zone_id} className="border-t border-gray-100">
                        <td className="px-2 py-1">{zone.name}</td>
                        <td className="px-2 py-1 text-center">{zone.record_count}</td>
                        <td className="px-2 py-1 text-center">{zone.private_zone ? 'Private' : 'Public'}</td>
                        <td className="px-2 py-1 text-right">$0.50</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-500 text-xs italic">No hosted zones found or insufficient permissions.</p>
            )}
            {insights.route53_resources.suggestions && insights.route53_resources.suggestions.length > 0 && (
              <div className="mt-2 pt-2 border-t border-gray-100">
                <div className="text-xs text-amber-600">
                  {insights.route53_resources.suggestions.map((suggestion, idx) => (
                    <div key={idx}>• {suggestion}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* S3 Buckets */}
        {insights.s3_resources && (
          <div className="bg-white p-3 rounded border border-gray-200 mb-3">
            <h5 className="font-medium mb-2">🪣 S3 Storage ({insights.s3_resources.total_buckets} buckets, {insights.s3_resources.total_size_readable})</h5>
            {insights.s3_resources.buckets && insights.s3_resources.buckets.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-2 py-1 text-left">Bucket Name</th>
                      <th className="px-2 py-1 text-right">Size</th>
                      <th className="px-2 py-1 text-right">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {insights.s3_resources.buckets.slice(0, 10).map((bucket) => (
                      <tr key={bucket.name} className="border-t border-gray-100">
                        <td className="px-2 py-1">{bucket.name}</td>
                        <td className="px-2 py-1 text-right">{bucket.size_readable}</td>
                        <td className="px-2 py-1 text-right">{new Date(bucket.creation_date).toLocaleDateString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {insights.s3_resources.buckets.length > 10 && (
                  <div className="text-xs text-gray-500 italic mt-2 text-center">
                    ...and {insights.s3_resources.buckets.length - 10} more buckets
                  </div>
                )}
              </div>
            ) : (
              <p className="text-gray-500 text-xs italic">No S3 buckets found or insufficient permissions.</p>
            )}
            {insights.s3_resources.suggestions && insights.s3_resources.suggestions.length > 0 && (
              <div className="mt-2 pt-2 border-t border-gray-100">
                <div className="text-xs text-amber-600">
                  {insights.s3_resources.suggestions.map((suggestion, idx) => (
                    <div key={idx}>• {suggestion}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* RDS Instances */}
        {insights.rds_resources && (
          <div className="bg-white p-3 rounded border border-gray-200 mb-3">
            <h5 className="font-medium mb-2">🗄️ RDS Databases ({insights.rds_resources.total_databases})</h5>
            {insights.rds_resources.databases && insights.rds_resources.databases.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-2 py-1 text-left">ID</th>
                      <th className="px-2 py-1 text-left">Engine</th>
                      <th className="px-2 py-1 text-left">Size</th>
                      <th className="px-2 py-1 text-right">Monthly Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {insights.rds_resources.databases.map((instance) => (
                      <tr key={instance.id} className="border-t border-gray-100">
                        <td className="px-2 py-1">{instance.id}</td>
                        <td className="px-2 py-1">{instance.engine}</td>
                        <td className="px-2 py-1">{instance.size}</td>
                        <td className="px-2 py-1 text-right">${instance.monthly_cost}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-500 text-xs italic">No RDS databases found or insufficient permissions.</p>
            )}
            {insights.rds_resources.suggestions && insights.rds_resources.suggestions.length > 0 && (
              <div className="mt-2 pt-2 border-t border-gray-100">
                <div className="text-xs text-amber-600">
                  {insights.rds_resources.suggestions.map((suggestion, idx) => (
                    <div key={idx}>• {suggestion}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Lightsail Instances */}
        {insights.lightsail_resources && (
          <div className="bg-white p-3 rounded border border-gray-200">
            <h5 className="font-medium mb-2">🚀 Lightsail Instances ({insights.lightsail_resources.total_instances})</h5>
            {insights.lightsail_resources.instances && insights.lightsail_resources.instances.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-2 py-1 text-left">Name</th>
                      <th className="px-2 py-1 text-left">Bundle</th>
                      <th className="px-2 py-1 text-right">Monthly Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {insights.lightsail_resources.instances.map((instance) => (
                      <tr key={instance.name} className="border-t border-gray-100">
                        <td className="px-2 py-1">{instance.name}</td>
                        <td className="px-2 py-1">{instance.bundle_id}</td>
                        <td className="px-2 py-1 text-right">${instance.monthly_cost}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-500 text-xs italic">No Lightsail instances found - all resources terminated or insufficient permissions.</p>
            )}
            {insights.lightsail_resources.cost_optimization_suggestions && insights.lightsail_resources.cost_optimization_suggestions.length > 0 && (
              <div className="mt-2 pt-2 border-t border-gray-100">
                <div className="text-xs text-amber-600">
                  {insights.lightsail_resources.cost_optimization_suggestions.map((suggestion, idx) => (
                    <div key={idx}>• {suggestion}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* CTO Recommendations */}
      {insights.recommendations && insights.recommendations.length > 0 && (
        <div className="mb-3">
          <h4 className="text-md font-medium text-gray-700 mb-2">💡 CTO Strategic Recommendations</h4>
          <div className="bg-white p-3 rounded border border-gray-200">
            <div className="space-y-2 text-xs text-gray-700">
              {insights.recommendations.map((recommendation, idx) => {
                // Handle section headers (lines starting with emoji and ending with colon)
                if (recommendation.match(/^[🎯💰📊🔄🚨].*:$/)) {
                  return (
                    <div key={idx} className="font-semibold text-gray-800 mt-3 first:mt-0">
                      {recommendation}
                    </div>
                  );
                }
                // Handle empty lines for spacing
                if (recommendation.trim() === '') {
                  return <div key={idx} className="h-1"></div>;
                }
                // Handle bullet points
                if (recommendation.startsWith('•')) {
                  return (
                    <div key={idx} className="ml-2 text-gray-600">
                      {recommendation}
                    </div>
                  );
                }
                // Regular text
                return (
                  <div key={idx} className="text-gray-600">
                    {recommendation}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
      
      {/* Assignment Info Footer */}
      {insights.assignment_info && (
        <div className="mt-4 pt-3 border-t border-gray-200">
          <div className="text-xs text-gray-500 space-y-1">
            <div>Assignment: <span className="font-medium">{insights.assignment_info.name}</span></div>
            <div>Team Size: <span className="font-medium">{insights.assignment_info.team_size} people</span></div>
            <div>Monthly Burn Rate: <span className="font-medium">${insights.assignment_info.monthly_burn_rate.toLocaleString()}</span></div>
            <div>Data last updated: <span className="font-medium">{new Date(insights.timestamp).toLocaleString()}</span></div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CTOInsightsSection;
