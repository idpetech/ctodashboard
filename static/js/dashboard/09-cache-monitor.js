/* CTO Lens dashboard module: 09-cache-monitor.js */
function BackgroundMonitor() {
    this.isRunning = false;
    this.interval = null;
    this.checkInterval = 60000; // 1 minute
    this.healthStatus = {
        api: 'unknown',
        assignments: 'unknown',
        lastCheck: null,
        errors: []
    };
}
    
BackgroundMonitor.prototype.start = function() {
    if (this.isRunning) return;
    
    this.isRunning = true;
    console.log('🔍 Starting background monitoring...');
    
    // Initial check
    this.performHealthCheck();
    
    // Set up interval
    var self = this;
    this.interval = setInterval(function() {
        self.performHealthCheck();
    }, this.checkInterval);
};
    
BackgroundMonitor.prototype.stop = function() {
    if (!this.isRunning) return;
    
    this.isRunning = false;
    console.log('⏹️ Stopping background monitoring...');
    
    if (this.interval) {
        clearInterval(this.interval);
        this.interval = null;
    }
};
    
BackgroundMonitor.prototype.performHealthCheck = function() {
    var self = this;
    var startTime = Date.now();
    
    // Create a simple timeout mechanism for older browsers
    var timeoutId = setTimeout(function() {
        self.healthStatus.api = 'unhealthy';
        self.healthStatus.assignments = 'unhealthy';
        self.addError('Request timeout');
        self.updateStatusIndicator(null, new Error('Timeout'));
        self.healthStatus.lastCheck = new Date().toISOString();
    }, 5000);
    
    fetch('/api/assignments?workspace_id=' + encodeURIComponent(currentWorkspace || ''), {
        headers: getAuthHeaders(),
        credentials: 'include'
    }).then(function(apiResponse) {
        clearTimeout(timeoutId);
        var responseTime = Date.now() - startTime;
        
        if (apiResponse.ok) {
            self.healthStatus.api = 'healthy';
            
            return apiResponse.json().then(function(data) {
                if (Array.isArray(data) || (data.assignments && Array.isArray(data.assignments))) {
                    self.healthStatus.assignments = 'healthy';
                } else {
                    self.healthStatus.assignments = 'degraded';
                }
                
                // Update UI status indicator
                self.updateStatusIndicator(responseTime);
                self.healthStatus.lastCheck = new Date().toISOString();
            });
        } else {
            self.healthStatus.api = 'unhealthy';
            self.healthStatus.assignments = 'unhealthy';
            self.addError('API returned ' + apiResponse.status);
            self.updateStatusIndicator(null, new Error('API Error'));
            self.healthStatus.lastCheck = new Date().toISOString();
        }
    }).catch(function(error) {
        clearTimeout(timeoutId);
        console.warn('Health check failed:', error);
        self.healthStatus.api = 'unhealthy';
        self.healthStatus.assignments = 'unhealthy';
        self.addError(error.message);
        self.updateStatusIndicator(null, error);
        self.healthStatus.lastCheck = new Date().toISOString();
    });
};
    
BackgroundMonitor.prototype.addError = function(errorMessage) {
    this.healthStatus.errors.unshift({
        timestamp: new Date().toISOString(),
        message: errorMessage
    });
    
    // Keep only last 10 errors
    if (this.healthStatus.errors.length > 10) {
        this.healthStatus.errors = this.healthStatus.errors.slice(0, 10);
    }
};
    
BackgroundMonitor.prototype.updateStatusIndicator = function(responseTime, error) {
    responseTime = responseTime || null;
    error = error || null;
    
    // Create or update status indicator
    var indicator = document.getElementById('health-indicator');
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'health-indicator';
        indicator.className = 'fixed bottom-4 left-4 z-50 px-3 py-2 rounded-lg text-xs transition-all duration-300 cursor-pointer';
        var self = this;
        indicator.onclick = function() {
            self.showHealthDetails();
        };
        document.body.appendChild(indicator);
    }
    
    // Update status
    if (this.healthStatus.api === 'healthy') {
        indicator.className = 'fixed bottom-4 left-4 z-50 px-3 py-2 rounded-lg text-xs transition-all duration-300 cursor-pointer bg-green-500 text-white';
        indicator.innerHTML = '🟢 System Healthy' + (responseTime ? ' (' + responseTime + 'ms)' : '');
    } else if (this.healthStatus.api === 'degraded') {
        indicator.className = 'fixed bottom-4 left-4 z-50 px-3 py-2 rounded-lg text-xs transition-all duration-300 cursor-pointer bg-yellow-500 text-white';
        indicator.innerHTML = '🟡 System Degraded';
    } else {
        indicator.className = 'fixed bottom-4 left-4 z-50 px-3 py-2 rounded-lg text-xs transition-all duration-300 cursor-pointer bg-red-500 text-white';
        indicator.innerHTML = '🔴 System Issues';
    }
    
    indicator.title = 'Click for details. Last check: ' + new Date().toLocaleTimeString();
};
    
BackgroundMonitor.prototype.showHealthDetails = function() {
    var errorSummary = '';
    var recentErrors = this.healthStatus.errors.slice(0, 3);
    for (var i = 0; i < recentErrors.length; i++) {
        var err = recentErrors[i];
        errorSummary += '\n• ' + new Date(err.timestamp).toLocaleTimeString() + ': ' + err.message;
    }
    
    var details = 'System Health Status:' +
        '\n• API: ' + this.healthStatus.api +
        '\n• Assignments: ' + this.healthStatus.assignments +
        '\n• Last Check: ' + (this.healthStatus.lastCheck ? new Date(this.healthStatus.lastCheck).toLocaleString() : 'Never') +
        '\n• Monitoring: ' + (this.isRunning ? 'Active' : 'Stopped') +
        '\n\nRecent Errors (' + this.healthStatus.errors.length + '):' + errorSummary;
    
    alert(details);
};
    
BackgroundMonitor.prototype.getStatus = function() {
    return {
        api: this.healthStatus.api,
        assignments: this.healthStatus.assignments,
        lastCheck: this.healthStatus.lastCheck,
        errors: this.healthStatus.errors.slice() // Create a copy
    };
};

const monitor = new BackgroundMonitor();

// Phase 5C: Real-time Updates with Polling Layer
function RealTimeUpdater() {
    this.isActive = false;
    this.interval = null;
    this.pollInterval = 30000; // 30 seconds
    this.lastUpdateCheck = null;
    this.assignmentCount = 0;
}
    
RealTimeUpdater.prototype.start = function() {
    if (this.isActive) return;
    
    this.isActive = true;
    console.log('🔄 Starting real-time updates...');
    
    // Initial state capture
    this.captureCurrentState();
    
    // Set up polling
    var self = this;
    this.interval = setInterval(function() {
        self.checkForUpdates();
    }, this.pollInterval);
};
    
RealTimeUpdater.prototype.stop = function() {
    if (!this.isActive) return;
    
    this.isActive = false;
    console.log('⏹️ Stopping real-time updates...');
    
    if (this.interval) {
        clearInterval(this.interval);
        this.interval = null;
    }
};
    
RealTimeUpdater.prototype.captureCurrentState = function() {
    if (typeof assignments !== 'undefined' && assignments) {
        this.assignmentCount = assignments.length;
    }
    this.lastUpdateCheck = new Date().toISOString();
};
    
RealTimeUpdater.prototype.checkForUpdates = function() {
    var self = this;
    
    // Check for assignment count changes (simple change detection)
    var apiUrl = '/api/assignments';
    if (typeof currentWorkspace !== 'undefined' && currentWorkspace) {
        apiUrl = '/api/workspaces/' + currentWorkspace + '/assignments';
    }
    
    fetch(apiUrl, {
        headers: getAuthHeaders()
    }).then(function(response) {
        if (!response.ok) return;
        
        return response.json().then(function(data) {
            var currentAssignments = Array.isArray(data) ? data : data.assignments || [];
            
            // Check if assignment count changed
            if (currentAssignments.length !== self.assignmentCount) {
                console.log('🔄 Detected assignment changes, refreshing...');
                self.showUpdateNotification('Assignments updated - refreshing dashboard');
                
                // Clear cache to force fresh data
                cache.invalidateAssignments(currentWorkspace);
                
                // Refresh dashboard (bypass stale cache)
                if (typeof loadDashboard === 'function') {
                    loadDashboard(true).then(function() {
                        self.captureCurrentState();
                    });
                } else {
                    self.captureCurrentState();
                }
            }
            
            // Update status indicator
            self.updateRealTimeIndicator('active');
        });
    }).catch(function(error) {
        console.warn('Real-time update check failed:', error);
        self.updateRealTimeIndicator('error');
    });
};
    
RealTimeUpdater.prototype.showUpdateNotification = function(message) {
    // Create update notification
    var notification = document.createElement('div');
    notification.className = 'fixed top-16 right-4 z-50 bg-blue-500 text-white px-4 py-2 rounded-lg shadow-lg text-sm flex items-center space-x-2';
    notification.innerHTML = '<span>🔄</span><span>' + message + '</span>';
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(function() {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 3000);
};
    
RealTimeUpdater.prototype.updateRealTimeIndicator = function(status) {
    // Add small indicator to show real-time status
    var indicator = document.getElementById('realtime-indicator');
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'realtime-indicator';
        indicator.className = 'fixed bottom-16 left-4 z-50 px-2 py-1 rounded text-xs cursor-pointer';
        indicator.title = 'Real-time updates status';
        document.body.appendChild(indicator);
    }
    
    if (status === 'active') {
        indicator.className = 'fixed bottom-16 left-4 z-50 px-2 py-1 rounded text-xs cursor-pointer bg-green-100 text-green-800';
        indicator.textContent = '🔄 Live';
    } else if (status === 'error') {
        indicator.className = 'fixed bottom-16 left-4 z-50 px-2 py-1 rounded text-xs cursor-pointer bg-red-100 text-red-800';
        indicator.textContent = '⚠️ Sync Issue';
    } else {
        indicator.className = 'fixed bottom-16 left-4 z-50 px-2 py-1 rounded text-xs cursor-pointer bg-gray-100 text-gray-800';
        indicator.textContent = '⏸️ Paused';
    }
};

const updater = new RealTimeUpdater();

// Enhanced fetch with caching
function cachedFetch(url, options, cacheKey, cacheTTL) {
    options = options || {};
    cacheKey = cacheKey || null;
    cacheTTL = cacheTTL || null;
    
    // Only cache GET requests
    if (!options.method || options.method === 'GET') {
        var key = cacheKey || url;
        var cached = cache.get(key);
        if (cached) {
            console.log('📂 Cache hit:', key);
            return Promise.resolve({
                json: function() { return Promise.resolve(cached); },
                ok: true,
                status: 200,
            });
        }
    }
    
    // Make actual request (always include cookies for session auth)
    var fetchOptions = Object.assign({ credentials: 'include' }, options);
    return fetch(url, fetchOptions).then(function(response) {
        // Cache successful GET responses
        if (response.ok && (!options.method || options.method === 'GET')) {
            var responseClone = response.clone();
            responseClone.json().then(function(data) {
                var key = cacheKey || url;
                cache.set(key, data, cacheTTL);
                console.log('💾 Cached response:', key);
            }).catch(function(e) {
                console.warn('Failed to cache response:', e);
            });
        }
        
        return response;
    });
}

// Modal Functions for Setup Panel
function configureConnector(connectorType) {
    document.getElementById('modalTitle').textContent = `Configure ${connectorType.toUpperCase()}`;
    
    // Hide all forms
    document.querySelectorAll('.credential-form').forEach(form => {
        form.classList.remove('active');
    });
    
    // Show specific form
    document.getElementById(`${connectorType}-form`).classList.add('active');
    
    // Clear any previous messages
    clearMessages();
    
    // Populate assignment dropdown and then show modal
    populateAssignmentDropdown(connectorType).then(() => {
        // Load existing credentials if we have a pre-selected assignment
        loadExistingCredentials(connectorType);
        
        // Show modal after dropdown and credentials are populated
        document.getElementById('credentialModal').classList.remove('hidden');
    });
}

async function loadExistingCredentials(connectorType) {
    try {
        // Get the currently selected assignment (either pre-selected or from dropdown)
        const assignmentId = selectedConnectorAssignmentId || selectedAssignmentId || document.getElementById(`${connectorType}_assignment`)?.value;
        
        if (!assignmentId) {
            console.log('No assignment selected, skipping credential loading');
            return;
        }
        
        console.log(`Loading existing ${connectorType} credentials for assignment:`, assignmentId);
        
        const workspaceId = currentWorkspace || 'default_workspace';
        const response = await authFetch(
            `/api/workspaces/${workspaceId}/assignments/${assignmentId}/auth/${connectorType}`
        );
        
        if (response.ok) {
            const data = await response.json();
            const credentials = data.credentials || {};
            
            if (credentials && Object.keys(credentials).length > 0) {
                console.log(`Found existing ${connectorType} credentials:`, credentials);
                
                // Pre-populate form fields based on connector type
                if (connectorType === 'github') {
                    populateGitHubForm(credentials);
                } else if (connectorType === 'aws') {
                    populateAWSForm(credentials);
                } else if (connectorType === 'openai') {
                    populateOpenAIForm(credentials);
                } else if (connectorType === 'jira') {
                    populateJiraForm(credentials);
                }
            } else {
                console.log(`No stored ${connectorType} credentials for assignment:`, assignmentId);
            }
        }
    } catch (error) {
        console.error('Error loading existing credentials:', error);
    }
}

function populateGitHubForm(credentials) {
    // Pre-populate GitHub form fields
    if (credentials.github_token) {
        document.getElementById('github_token').value = credentials.github_token;
    }
    if (credentials.github_org) {
        document.getElementById('github_org').value = credentials.github_org;
    }
    if (credentials.github_repos) {
        document.getElementById('github_repos').value = credentials.github_repos;
    }
    console.log('GitHub form pre-populated with existing credentials');
}

function populateAWSForm(credentials) {
    // Pre-populate AWS form fields
    if (credentials.aws_access_key) {
        document.getElementById('aws_access_key').value = credentials.aws_access_key;
    }
    if (credentials.aws_secret_key) {
        document.getElementById('aws_secret_key').value = credentials.aws_secret_key;
    }
    if (credentials.aws_region) {
        document.getElementById('aws_region').value = credentials.aws_region;
    }
    console.log('AWS form pre-populated with existing credentials');
}

function populateOpenAIForm(credentials) {
    // Pre-populate OpenAI form fields
    if (credentials.openai_api_key) {
        document.getElementById('openai_api_key').value = credentials.openai_api_key;
    }
    if (credentials.openai_org_id) {
        document.getElementById('openai_org_id').value = credentials.openai_org_id;
    }
    if (credentials.openai_admin_api_key) {
        document.getElementById('openai_admin_api_key').value = credentials.openai_admin_api_key;
    }
    if (credentials.openai_model) {
        document.getElementById('openai_model').value = credentials.openai_model;
    }
    console.log('OpenAI form pre-populated with existing credentials');
}

function populateJiraForm(credentials) {
    if (credentials.jira_url) {
        document.getElementById('jira_url').value = credentials.jira_url;
    }
    if (credentials.jira_email) {
        document.getElementById('jira_email').value = credentials.jira_email;
    }
    if (credentials.jira_token) {
        document.getElementById('jira_token').value = credentials.jira_token;
    }
    if (credentials.jira_projects) {
        document.getElementById('jira_projects').value = credentials.jira_projects;
    }
    console.log('Jira form pre-populated with existing credentials');
}

function closeCredentialModal() {
    document.getElementById('credentialModal').classList.add('hidden');
    clearMessages();
    // Reset pre-selected assignment
    selectedConnectorAssignmentId = null;
}

async function testCredentials(connectorType) {
    const credentials = getCredentialsFromForm(connectorType);
    if (!credentials) return;

    showMessage('Testing connection...', 'info');

    try {
        const workspaceId = currentWorkspace || 'default_workspace';
        const response = await authFetch(`/api/workspaces/${workspaceId}/credentials/${connectorType}/test`, {
            method: 'POST',
            body: JSON.stringify({ credentials })
        });

        const result = await response.json();

        if (result.valid) {
            showMessage(`✅ Connection successful! Connected as: ${result.user || result.account}`, 'success');
        } else {
            showMessage(`❌ Connection failed: ${result.error}`, 'error');
        }
    } catch (error) {
        showMessage(`❌ Test failed: ${error.message}`, 'error');
    }
}

async function saveCredentials(event, connectorType) {
    event.preventDefault();
    
    const credentials = getCredentialsFromForm(connectorType);
    const assignmentId = document.getElementById(`${connectorType}_assignment`).value;
    
    if (!credentials || !assignmentId) {
        showMessage('Please fill in all required fields and select an assignment', 'error');
        return;
    }

    showMessage('Saving credentials...', 'info');

    try {
        const workspaceId = currentWorkspace || 'default_workspace';
        const response = await authFetch(`/api/workspaces/${workspaceId}/credentials/${connectorType}`, {
            method: 'PUT',
            body: JSON.stringify({
                credentials,
                assignment_id: assignmentId
            })
        });

        const result = await response.json();

        if (result.success) {
            showMessage('✅ Credentials saved successfully!', 'success');
            setTimeout(() => {
                closeCredentialModal();
                // Refresh the assignment connectors view if we're in setup mode
                if (selectedAssignmentId) {
                    loadAssignmentConnectors(selectedAssignmentId);
                }
                refreshAssignmentsUI();
            }, 2000);
        } else {
            showMessage(`❌ Save failed: ${result.error || result.details}`, 'error');
        }
    } catch (error) {
        showMessage(`❌ Save failed: ${error.message}`, 'error');
    }
}

function getCredentialsFromForm(connectorType) {
    switch (connectorType) {
        case 'github':
            return {
                github_token: document.getElementById('github_token').value,
                github_org: document.getElementById('github_org').value,
                github_repos: document.getElementById('github_repos').value
            };
        case 'jira':
            return {
                jira_url: document.getElementById('jira_url').value,
                jira_email: document.getElementById('jira_email').value,
                jira_token: document.getElementById('jira_token').value,
                jira_projects: document.getElementById('jira_projects').value
            };
        case 'aws':
            return {
                aws_access_key: document.getElementById('aws_access_key').value,
                aws_secret_key: document.getElementById('aws_secret_key').value,
                aws_region: document.getElementById('aws_region').value
            };
        case 'openai':
            return {
                openai_api_key: document.getElementById('openai_api_key').value,
                openai_org_id: document.getElementById('openai_org_id').value,
                openai_admin_api_key: document.getElementById('openai_admin_api_key').value,
                openai_model: document.getElementById('openai_model').value
            };
        case 'railway':
            return {
                railway_token: document.getElementById('railway_token').value,
                railway_project_id: document.getElementById('railway_project_id').value,
                railway_project_name: document.getElementById('railway_project_name').value
            };
        case 'vercel':
            return {
                vercel_token: document.getElementById('vercel_token').value,
                vercel_project_id: document.getElementById('vercel_project_id').value,
                vercel_team_id: document.getElementById('vercel_team_id').value
            };
        case 'azure':
            return {
                azure_tenant_id: document.getElementById('azure_tenant_id').value,
                azure_client_id: document.getElementById('azure_client_id').value,
                azure_client_secret: document.getElementById('azure_client_secret').value,
                azure_subscription_id: document.getElementById('azure_subscription_id').value,
                azure_resource_group: document.getElementById('azure_resource_group').value
            };
        default:
            return null;
    }
}

function showMessage(message, type) {
    clearMessages();
    
    const messageElement = document.getElementById(type === 'error' ? 'credentialError' : 'credentialSuccess');
    messageElement.textContent = message;
    messageElement.classList.remove('hidden');
}

function clearMessages() {
    document.getElementById('credentialError').classList.add('hidden');
    document.getElementById('credentialSuccess').classList.add('hidden');
}

// Global variable to track pre-selected assignment for connector config
let selectedConnectorAssignmentId = null;

async function populateAssignmentDropdown(connectorType) {
    try {
        const workspaceId = currentWorkspace || 'default_workspace';
        const response = await fetch(`/api/workspaces/${workspaceId}/assignments`, {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const data = await response.json();
            const assignments = data.assignments || [];
            
            const dropdown = document.getElementById(`${connectorType}_assignment`);
            dropdown.innerHTML = '<option value="">Select assignment...</option>' +
                assignments.map(assignment => 
                    `<option value="${assignment.id}" ${selectedConnectorAssignmentId === assignment.id ? 'selected' : ''}>${assignment.name || assignment.id}</option>`
                ).join('');
            
            // If we have a pre-selected assignment, ensure it's selected
            if (selectedConnectorAssignmentId) {
                dropdown.value = selectedConnectorAssignmentId;
                console.log('🎯 Pre-selected assignment:', selectedConnectorAssignmentId, 'in', connectorType, 'dropdown');
            }
        }
    } catch (error) {
        console.error('Error loading assignments:', error);
    }
}

// Assignment Modal Functions
function showCreateAssignmentModal() {
    // Clear form
    document.getElementById('assignment_id').value = '';
    document.getElementById('assignment_name').value = '';
    document.getElementById('assignment_description').value = '';
    document.getElementById('team_size').value = '';
    document.getElementById('monthly_burn_rate').value = '';
    document.getElementById('target_monthly_burn').value = '';
    document.getElementById('assignment_status').value = 'active';
    document.getElementById('enable_github').checked = false;
    document.getElementById('enable_jira').checked = false;
    document.getElementById('enable_aws').checked = false;
    document.getElementById('enable_openai').checked = false;
    const er = document.getElementById('dashboard_enable_railway');
    const ev = document.getElementById('dashboard_enable_vercel');
    const ea = document.getElementById('dashboard_enable_azure');
    if (er) er.checked = false;
    if (ev) ev.checked = false;
    if (ea) ea.checked = false;
    loadAct4ConnectorFlags();
    
    clearAssignmentMessages();
    document.getElementById('createAssignmentModal').classList.remove('hidden');
}

function closeCreateAssignmentModal() {
    document.getElementById('createAssignmentModal').classList.add('hidden');
    clearAssignmentMessages();
}

async function createAssignment(event) {
    event.preventDefault();
    clearAssignmentMessages();

    // Get form data
    const assignmentData = {
        id: document.getElementById('assignment_id').value.trim(),
        name: document.getElementById('assignment_name').value.trim(),
        description: document.getElementById('assignment_description').value.trim(),
        team_size: parseInt(document.getElementById('team_size').value) || null,
        monthly_burn_rate: parseInt(document.getElementById('monthly_burn_rate').value) || null,
        target_monthly_burn: parseInt(document.getElementById('target_monthly_burn').value) || null,
        status: document.getElementById('assignment_status').value,
        workspace_id: currentWorkspace || 'default_workspace',
        created_at: new Date().toISOString()
    };

    // Get enabled connectors
    const connectors = {};
    if (document.getElementById('enable_github').checked) {
        connectors.github = {
            enabled: true,
            track_deployments: true,
            track_issues: true,
            track_pull_requests: true,
            default_branch: "main"
        };
    }
    if (document.getElementById('enable_jira').checked) {
        connectors.jira = {
            enabled: true,
            track_sprints: true,
            track_bugs: true,
            track_story_points: true,
            default_board: "scrum"
        };
    }
    if (document.getElementById('enable_aws').checked) {
        connectors.aws = {
            enabled: true,
            track_costs: true,
            track_resources: true,
            cost_alert_threshold: 100
        };
    }
    if (document.getElementById('enable_openai').checked) {
        connectors.openai = {
            enabled: true,
            track_usage: true,
            track_costs: true,
            cost_alert_threshold: 50
        };
    }
    if (document.getElementById('dashboard_enable_railway')?.checked) {
        connectors.railway = { enabled: true };
    }
    if (document.getElementById('dashboard_enable_vercel')?.checked) {
        connectors.vercel = { enabled: true };
    }
    if (document.getElementById('dashboard_enable_azure')?.checked) {
        connectors.azure = { enabled: true };
    }

    if (Object.keys(connectors).length > 0) {
        assignmentData.metrics_config = connectors;
    }

    showAssignmentMessage('Creating assignment...', 'info');

    try {
        const workspaceId = currentWorkspace || 'default_workspace';
        const response = await authFetch(`/api/workspaces/${workspaceId}/assignments`, {
            method: 'POST',
            body: JSON.stringify(assignmentData)
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showAssignmentMessage('✅ Assignment created successfully!', 'success');
            setTimeout(() => {
                closeCreateAssignmentModal();
                refreshAssignmentsUI();
            }, 2000);
        } else if (response.status === 401) {
            showAssignmentMessage('Your session has expired. Please sign in - your entries are kept and will be submitted automatically after you log in.', 'error');
            window._pendingAuthRetry = function() { createAssignment(event); };
            showAuthOverlay();
            showLoginForm();
        } else {
            showAssignmentMessage(`❌ Failed to create assignment: ${result.error || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        showAssignmentMessage(`❌ Error creating assignment - your entries are still here: ${error.message}`, 'error');
    }
}

function showAssignmentMessage(message, type) {
    clearAssignmentMessages();
    
    const messageElement = document.getElementById(type === 'error' ? 'assignmentError' : 'assignmentSuccess');
    messageElement.textContent = message;
    messageElement.classList.remove('hidden');
}

function clearAssignmentMessages() {
    document.getElementById('assignmentError').classList.add('hidden');
    document.getElementById('assignmentSuccess').classList.add('hidden');
}
