/* CTO Lens dashboard module: 03-workspace-core.js */
async function retryWithExponentialBackoff(operation, options = {}) {
    const {
        maxRetries = 3,
        initialDelayMs = 1000,
        maxDelayMs = 10000,
        backoffMultiplier = 2,
        onRetry = null
    } = options;
    
    let lastError;
    let delay = initialDelayMs;
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            const result = await operation();
            
            // For fetch operations, check if the response is ok
            if (result && typeof result.ok === 'boolean') {
                if (result.ok) {
                    return result;
                }
                // If it's a 404/401 during user initialization, retry
                if (attempt < maxRetries && (result.status === 404 || result.status === 401)) {
                    throw new Error(`HTTP ${result.status} - retrying...`);
                }
                return result; // Return non-ok responses on last attempt
            }
            
            return result;
            
        } catch (error) {
            lastError = error;
            
            if (attempt === maxRetries) {
                console.error(`Operation failed after ${maxRetries + 1} attempts:`, error);
                throw error;
            }
            
            console.log(`Attempt ${attempt + 1} failed, retrying in ${delay}ms:`, error.message);
            
            if (onRetry) {
                onRetry(attempt + 1, delay, error);
            }
            
            // Wait before retrying
            await new Promise(resolve => setTimeout(resolve, delay));
            
            // Increase delay for next attempt (exponential backoff)
            delay = Math.min(delay * backoffMultiplier, maxDelayMs);
        }
    }
    
    throw lastError;
}

// Workspace Management
let currentWorkspace = null;

async function loadWorkspaces() {
    try {
        const response = await authFetch('/api/workspaces');
        
        if (response.ok) {
            const workspaces = await response.json();
            
            if (workspaces.length === 0) {
                // No workspace - show loading and create user's workspace automatically
                showWorkspaceLoading('Creating your first workspace...');
                await createUserWorkspace();
            } else if (workspaces.length === 1) {
                // One workspace - auto-select and show simplified UI
                currentWorkspace = workspaces[0].id;
                localStorage.setItem('selectedWorkspace', currentWorkspace);
                showSingleWorkspaceUI(workspaces[0]);
            } else {
                // Multiple workspaces - show dropdown selector
                populateWorkspaceSelector(workspaces);
                document.getElementById('workspace-selector').classList.remove('hidden');
                
                // Get user profile to find default workspace
                const profileResponse = await authFetch('/api/auth/profile');
                
                let defaultWorkspace = null;
                if (profileResponse.ok) {
                    const profile = await profileResponse.json();
                    defaultWorkspace = profile.preferences?.default_workspace;
                }
                
                // Auto-select default workspace or first available
                const targetWorkspace = workspaces.find(w => w.id === defaultWorkspace) ? defaultWorkspace : workspaces[0].id;
                currentWorkspace = targetWorkspace;
                localStorage.setItem('selectedWorkspace', currentWorkspace);
                document.getElementById('workspace-select').value = currentWorkspace;
                
                // Show and load dashboard content
                showDashboardContent();
                loadDashboard();
            }
        } else {
            console.error('Failed to load workspaces:', response.status);
            // Hide workspace selector if no access
            document.getElementById('workspace-selector').classList.add('hidden');
        }
    } catch (error) {
        console.error('Error loading workspaces:', error);
        document.getElementById('workspace-selector').classList.add('hidden');
    }
}

async function createUserWorkspace() {
    // Auto-create workspace for user (called when user has no workspace)
    console.log('🏗️ Creating user workspace (handling potential race condition)...');
    
    try {
        // Get user info to create workspace name - with retry logic for race conditions
        const profileResponse = await retryWithExponentialBackoff(
            () => authFetch('/api/auth/profile'),
            {
                maxRetries: 5,
                initialDelayMs: 500,
                maxDelayMs: 5000,
                backoffMultiplier: 2,
                onRetry: (attempt, delay, error) => {
                    console.log(`🔄 Profile fetch retry ${attempt}/5 in ${delay}ms (${error.message})`);
                    showWorkspaceLoading(`Initializing account... (attempt ${attempt}/5)`);
                }
            }
        );
        
        if (!profileResponse.ok) {
            throw new Error('Failed to get user profile');
        }
        
        const profile = await profileResponse.json();
        const email = profile.email;
        const displayName = profile.display_name;
        
        // Generate workspace details
        const username = email.split('@')[0];
        const workspaceId = username + '_workspace';
        const workspaceName = displayName + "'s Workspace";
        const workspaceDescription = `Personal workspace for ${email}`;
        
        // Create the user's personal workspace via API - with retry for consistency
        console.log(`📝 Creating workspace: ${workspaceName}`);
        const createResponse = await retryWithExponentialBackoff(
            () => authFetch('/api/workspaces', {
                method: 'POST',
                body: JSON.stringify({
                    id: workspaceId,
                    name: workspaceName,
                    description: workspaceDescription
                })
            }),
            {
                maxRetries: 3,
                initialDelayMs: 1000,
                maxDelayMs: 5000,
                onRetry: (attempt, delay, error) => {
                    console.log(`🔄 Workspace creation retry ${attempt}/3 in ${delay}ms`);
                }
            }
        );

        if (!createResponse.ok) {
            const errData = await createResponse.json().catch(() => ({}));
            throw new Error(errData.error || 'Failed to create workspace');
        }
        
        console.log('✅ Workspace created successfully');

        // Reload to pick up the newly created workspace
        await loadWorkspaces();
        
    } catch (error) {
        console.error('Error creating user workspace:', error);
        // Show error state
        showWorkspaceError('Unable to initialize workspace. Please refresh the page.');
    }
}

function showSingleWorkspaceUI(workspace) {
    // Single workspace: hide selector (no redundant label overlapping header)
    document.getElementById('workspace-selector').classList.add('hidden');
    showDashboardContent();
    loadDashboard();
}

function showWorkspaceLoading(message = 'Setting up your workspace...') {
    const selector = document.getElementById('workspace-selector');
    selector.innerHTML = `
        <div class="workspace-selector bg-blue-50 border border-blue-200 p-4 rounded-lg">
            <div class="text-sm font-medium text-blue-700 mb-2">
                🏗️ Initializing Workspace
            </div>
            <div class="text-xs text-blue-600 mb-3">
                ${message}
            </div>
            <div class="w-full bg-blue-200 rounded-full h-2">
                <div class="bg-blue-600 h-2 rounded-full animate-pulse" style="width: 70%"></div>
            </div>
            <div class="text-xs text-blue-500 mt-2">
                This may take a few seconds for new accounts...
            </div>
        </div>
    `;
    selector.classList.remove('hidden');
}

function showWorkspaceError(message) {
    const selector = document.getElementById('workspace-selector');
    selector.innerHTML = `
        <div class="workspace-selector bg-red-50 border border-red-200 p-4 rounded-lg">
            <div class="text-sm font-medium text-red-700 mb-2">
                ⚠️ Workspace Error
            </div>
            <div class="text-xs text-red-600 mb-3">
                ${message}
            </div>
            <button onclick="location.reload()" class="w-full bg-red-600 hover:bg-red-700 text-white text-sm font-medium py-2 px-3 rounded">
                Refresh Page
            </button>
        </div>
    `;
    selector.classList.remove('hidden');
    hideDashboardContent();
}

function hideDashboardContent() {
    // Hide main dashboard sections when no workspace is available
    const sections = [
        'metrics-overview',
        'assignments-section', 
        'assignments-table',
        'chatbot-section'
    ];
    
    sections.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.style.display = 'none';
        }
    });
    
    // Show a placeholder message
    const mainContent = document.querySelector('.min-h-screen > div');
    if (mainContent) {
        const placeholder = document.createElement('div');
        placeholder.id = 'workspace-placeholder';
        placeholder.className = 'text-center py-16';
        placeholder.innerHTML = `
            <div class="max-w-md mx-auto">
                <h2 class="text-xl font-semibold text-gray-600 mb-4">Welcome to CTO Lens</h2>
                <p class="text-gray-500 mb-6">Create your workspace to get started with managing assignments and configuring connectors.</p>
                <div class="text-6xl mb-4">🚀</div>
            </div>
        `;
        
        // Remove existing placeholder if any
        const existing = document.getElementById('workspace-placeholder');
        if (existing) existing.remove();
        
        mainContent.appendChild(placeholder);
    }
}

function showDashboardContent() {
    // Show main dashboard sections when workspace is selected
    const sections = [
        'metrics-overview',
        'assignments-section', 
        'assignments-table',
        'chatbot-section'
    ];
    
    sections.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.style.display = '';
        }
    });
    
    // Remove placeholder
    const placeholder = document.getElementById('workspace-placeholder');
    if (placeholder) placeholder.remove();

    trackPageViewOnce('dashboard', '/dashboard');
}

function populateWorkspaceSelector(workspaces) {
    const select = document.getElementById('workspace-select');
    
    // Clear existing options except the first one
    select.innerHTML = '<option value="">Select Workspace...</option>';
    
    // Handle different response formats
    let workspaceArray = [];
    if (Array.isArray(workspaces)) {
        workspaceArray = workspaces;
    } else if (workspaces && workspaces.workspaces && Array.isArray(workspaces.workspaces)) {
        workspaceArray = workspaces.workspaces;
    } else if (workspaces && typeof workspaces === 'object') {
        // If it's an object, treat it as a single workspace
        workspaceArray = [workspaces];
    } else {
        console.warn('No valid workspaces data received:', workspaces);
        return;
    }
    
    // Add workspace options
    workspaceArray.forEach(workspace => {
        const option = document.createElement('option');
        option.value = workspace.id || workspace.name;
        option.textContent = workspace.name || workspace.id || 'Unnamed Workspace';
        select.appendChild(option);
    });
}

function handleWorkspaceChange() {
    const select = document.getElementById('workspace-select');
    currentWorkspace = select.value;
    if (currentWorkspace) {
        localStorage.setItem('selectedWorkspace', currentWorkspace);
        console.log('Workspace selected:', currentWorkspace);
        cache.invalidateAssignments(currentWorkspace);
        loadDashboard(true);
    }
}

function getCurrentWorkspace() {
    return currentWorkspace;
}

/** Build workspace-scoped assignment API URL; returns null if no workspace selected. */
function workspaceAssignmentUrl(assignmentId) {
    const ws = currentWorkspace;
    if (!ws) {
        alert('Select your workspace before managing assignments.');
        return null;
    }
    return `/api/workspaces/${encodeURIComponent(ws)}/assignments/${encodeURIComponent(assignmentId)}`;
}

function openWorkspaceSettings() {
    const ws = currentWorkspace || localStorage.getItem('selectedWorkspace') || 'default_workspace';
    window.location.href = `/workspace/${ws}/settings`;
}

function showSetupPanel() {
    // Show setup panel inline in the dashboard
    document.getElementById('dashboard-content').innerHTML = `
        <div class="max-w-4xl mx-auto">
            <div class="bg-white rounded-lg shadow-lg">
                <!-- Header -->
                <div class="bg-blue-600 text-white p-6 rounded-t-lg">
                    <div class="flex justify-between items-center">
                        <div>
                            <h2 class="text-2xl font-bold">⚙️ Setup Assignments & Connectors</h2>
                            <p class="text-blue-100 mt-1">Manage your projects and configure integrations</p>
                        </div>
                        <button onclick="loadDashboard(true)" class="bg-blue-500 hover:bg-blue-400 px-4 py-2 rounded text-sm">
                            ← Back to Dashboard
                        </button>
                    </div>
                </div>

                <!-- Setup Content: Master-Detail Layout -->
                <div class="p-6">
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        <!-- Master: Assignments List -->
                        <div>
                            <div class="flex justify-between items-center mb-4">
                                <div>
                                    <h3 class="text-xl font-semibold text-gray-800">📋 Assignments</h3>
                                    <p class="text-gray-600">Select an assignment to manage its connectors</p>
                                </div>
                                <button onclick="showCreateAssignmentModal()" class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 text-sm">
                                    + Create
                                </button>
                            </div>
                            
                            <!-- Assignment List -->
                            <div id="setupAssignmentsList" class="space-y-3 max-h-96 overflow-y-auto">
                                <div class="text-center py-8 text-gray-500">Loading assignments...</div>
                            </div>
                        </div>

                        <!-- Detail: Connector Configuration -->
                        <div>
                            <div id="connectorDetailSection">
                                <!-- No Assignment Selected State -->
                                <div id="noAssignmentSelected" class="text-center py-16">
                                    <div class="text-6xl mb-4">🔌</div>
                                    <h3 class="text-lg font-medium text-gray-800 mb-2">Select an Assignment</h3>
                                    <p class="text-gray-600">Choose an assignment from the left to view and configure its connectors</p>
                                </div>

                                <!-- Assignment Selected State (initially hidden) -->
                                <div id="assignmentConnectors" class="hidden">
                                    <div class="flex justify-between items-center mb-6">
                                        <div>
                                            <h3 class="text-xl font-semibold text-gray-800">🔌 Connectors</h3>
                                            <p class="text-gray-600">for <span id="selectedAssignmentName" class="font-medium text-blue-600"></span></p>
                                        </div>
                                        <button onclick="showCreateConnectorModal()" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm">
                                            + Add Connector
                                        </button>
                                    </div>
                                    
                                    <!-- Configured Connectors List -->
                                    <div id="configuredConnectorsList" class="space-y-3 mb-6">
                                        <!-- Will be populated dynamically -->
                                    </div>
                                    
                                    <!-- Available Connectors (if none configured) -->
                                    <div id="noConnectorsMessage" class="text-center py-8 text-gray-500 hidden">
                                        <div class="text-4xl mb-4">⚡</div>
                                        <p class="mb-4">No connectors configured yet</p>
                                        <button onclick="showCreateConnectorModal()" class="text-blue-600 hover:underline">
                                            Add your first connector
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- CTOLens live metrics schedule -->
                    <div class="mt-8 border-t border-gray-200 pt-8">
                        <div class="flex justify-between items-center mb-4">
                            <div>
                                <h3 class="text-xl font-semibold text-gray-800">📅 CTOLens Live Metrics Schedule</h3>
                                <p class="text-gray-600 text-sm mt-1">Optional periodic GitHub/Jira refresh. Fast briefing updates stay manual.</p>
                            </div>
                            <button id="setupSaveCtolenScheduleBtn" onclick="saveSetupCtolenSchedule()" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm">
                                Save Schedule
                            </button>
                        </div>
                        <div id="setupCtolenScheduleDisabled" class="hidden bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded mb-4 text-sm">
                            Scheduled enrichment is disabled on this deployment. Set ENABLE_CTOLENS_SCHEDULED_ENRICHMENT=true to save schedules.
                        </div>
                        <div id="setupCtolenScheduleMessage" class="hidden mb-4 text-sm rounded px-4 py-3"></div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <label class="flex items-center space-x-2">
                                <input type="checkbox" id="setupCtolenScheduleEnabled" class="rounded border-gray-300">
                                <span class="text-sm text-gray-700">Enable scheduled live metrics runs</span>
                            </label>
                            <label class="flex items-center space-x-2">
                                <input type="checkbox" id="setupCtolenScheduleOnImport" class="rounded border-gray-300">
                                <span class="text-sm text-gray-700">Run enriched briefing after CSV import</span>
                            </label>
                            <div>
                                <label class="block text-sm text-gray-600 mb-1">Frequency</label>
                                <select id="setupCtolenScheduleFrequency" class="w-full border rounded px-3 py-2 text-sm">
                                    <option value="manual_only">Manual only</option>
                                    <option value="daily">Daily</option>
                                    <option value="weekly">Weekly</option>
                                </select>
                            </div>
                            <div>
                                <label class="block text-sm text-gray-600 mb-1">Time (UTC)</label>
                                <input type="time" id="setupCtolenScheduleTimeUtc" value="06:00" class="w-full border rounded px-3 py-2 text-sm">
                            </div>
                            <div>
                                <label class="block text-sm text-gray-600 mb-1">Day of week (weekly)</label>
                                <select id="setupCtolenScheduleDay" class="w-full border rounded px-3 py-2 text-sm">
                                    <option value="monday">Monday</option>
                                    <option value="tuesday">Tuesday</option>
                                    <option value="wednesday">Wednesday</option>
                                    <option value="thursday">Thursday</option>
                                    <option value="friday">Friday</option>
                                    <option value="saturday">Saturday</option>
                                    <option value="sunday">Sunday</option>
                                </select>
                            </div>
                        </div>
                        <div id="setupCtolenRunStatus" class="bg-gray-50 rounded p-4 mt-4 text-sm text-gray-700 hidden"></div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Wait for DOM to be ready, then load setup data
    setTimeout(() => {
        loadSetupData();
    }, 100);
}

function configureSetupConnector(connectorType) {
    // Use inline modal for connector configuration
    configureConnector(connectorType);
}

function getSelectedAssignmentDisplayName() {
    const nameEl = document.getElementById('selectedAssignmentName');
    if (nameEl && nameEl.textContent.trim()) {
        return nameEl.textContent.trim();
    }
    const editNameEl = document.getElementById('assignment-name');
    if (editNameEl && editNameEl.value.trim()) {
        return editNameEl.value.trim();
    }
    if (selectedAssignmentId && Array.isArray(assignments)) {
        const match = assignments.find(function(a) { return a.id === selectedAssignmentId; });
        if (match) {
            return match.name || match.id;
        }
    }
    return selectedAssignmentId || 'this assignment';
}

async function showCreateConnectorModal() {
    if (!selectedAssignmentId) {
        alert('Please select an assignment first');
        return;
    }

    await loadAct4ConnectorFlags();
    const assignmentName = getSelectedAssignmentDisplayName();
    const pickerEntries = getConnectorsForPicker();
    if (pickerEntries.length === 0) {
        alert('No connectors are available on this deployment.');
        return;
    }

    const pickerButtons = pickerEntries.map(function(entry) {
        return `
                        <button onclick="createNewConnector('${entry.id}')" class="border-2 border-gray-200 hover:border-blue-500 rounded-lg p-4 text-left transition-colors">
                            <div class="flex items-center space-x-3">
                                <div class="w-12 h-12 ${entry.bg} rounded text-white flex items-center justify-center font-bold">
                                    ${entry.icon}
                                </div>
                                <div>
                                    <h4 class="font-medium">${entry.label}</h4>
                                    <p class="text-sm text-gray-600">${entry.desc}</p>
                                </div>
                            </div>
                        </button>`;
    }).join('');

    const modalHtml = `
        <div id="connectorTypeModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4">
                <div class="bg-gray-50 px-6 py-4 border-b">
                    <div class="flex justify-between items-center">
                        <h3 class="text-lg font-medium text-gray-800">Add Connector</h3>
                        <button onclick="closeConnectorTypeModal()" class="text-gray-400 hover:text-gray-600">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                            </svg>
                        </button>
                    </div>
                </div>
                <div class="p-6">
                    <p class="text-gray-600 mb-6">Choose a connector type for <strong>${assignmentName}</strong></p>
                    <div class="grid grid-cols-2 gap-4">
                        ${pickerButtons}
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

function closeConnectorTypeModal() {
    const modal = document.getElementById('connectorTypeModal');
    if (modal) {
        modal.remove();
    }
}

function createNewConnector(connectorType) {
    closeConnectorTypeModal();
    
    // Enable the connector for the assignment first, then configure
    enableConnectorForAssignment(selectedAssignmentId, connectorType).then(() => {
        // Pre-populate assignment in modal
        selectedConnectorAssignmentId = selectedAssignmentId;
        console.log('🔧 Creating', connectorType, 'connector for assignment:', selectedConnectorAssignmentId);
        configureConnector(connectorType);
    });
}

async function enableConnectorForAssignment(assignmentId, connectorType) {
    try {
        const workspaceId = currentWorkspace || 'default_workspace';
        
        // Get current assignment data
        const response = await fetch(`/api/workspaces/${workspaceId}/assignments`);
        const data = await response.json();
        const assignment = data.assignments.find(a => a.id === assignmentId);
        
        if (!assignment) {
            throw new Error('Assignment not found');
        }
        
        // Add connector to metrics_config if not already present
        if (!assignment.metrics_config) {
            assignment.metrics_config = {};
        }
        
        if (!assignment.metrics_config[connectorType]) {
            if (['railway', 'vercel', 'azure'].includes(connectorType)) {
                assignment.metrics_config[connectorType] = { enabled: true };
            } else {
                assignment.metrics_config[connectorType] = {
                    enabled: true,
                    track_deployments: connectorType === 'github',
                    track_issues: connectorType === 'github' || connectorType === 'jira',
                    track_pull_requests: connectorType === 'github',
                    track_sprints: connectorType === 'jira',
                    track_bugs: connectorType === 'jira',
                    track_story_points: connectorType === 'jira',
                    track_costs: connectorType === 'aws' || connectorType === 'openai',
                    track_resources: connectorType === 'aws',
                    track_usage: connectorType === 'openai',
                    cost_alert_threshold: connectorType === 'aws' ? 100 : 50,
                    default_branch: 'main'
                };
            }
        }
        
        // Update assignment
        const updateResponse = await fetch(`/api/workspaces/${workspaceId}/assignments/${assignmentId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(assignment)
        });
        
        if (!updateResponse.ok) {
            throw new Error('Failed to enable connector');
        }
        
    } catch (error) {
        console.error('Error enabling connector:', error);
        alert('Failed to enable connector: ' + error.message);
    }
}

function editConnector(assignmentId, connectorType) {
    selectedConnectorAssignmentId = assignmentId;
    configureConnector(connectorType);
}

async function deleteConnector(assignmentId, connectorType) {
    if (!confirm(`Remove ${connectorType.toUpperCase()} connector from this assignment?\n\nThis will delete all credentials and configuration.`)) {
        return;
    }
    
    try {
        const workspaceId = currentWorkspace || 'default_workspace';
        
        // Get current assignment data
        const response = await fetch(`/api/workspaces/${workspaceId}/assignments`);
        const data = await response.json();
        const assignment = data.assignments.find(a => a.id === assignmentId);
        
        if (!assignment || !assignment.metrics_config) {
            throw new Error('Assignment or connector not found');
        }
        
        // Remove connector from metrics_config
        delete assignment.metrics_config[connectorType];
        
        // Update assignment
        const updateResponse = await fetch(`/api/workspaces/${workspaceId}/assignments/${assignmentId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(assignment)
        });
        
        if (updateResponse.ok) {
            // Refresh the connector list
            loadAssignmentConnectors(assignmentId);
        } else {
            throw new Error('Failed to remove connector');
        }
        
    } catch (error) {
        console.error('Error removing connector:', error);
        alert('Failed to remove connector: ' + error.message);
    }
}

function configureConnectorForAssignment(connectorType) {
    if (!selectedAssignmentId) {
        alert('Please select an assignment first');
        return;
    }
    
    // Pre-populate assignment in modal
    selectedConnectorAssignmentId = selectedAssignmentId;
    console.log('🔧 Configuring', connectorType, 'for assignment:', selectedConnectorAssignmentId);
    configureConnector(connectorType);
}

function refreshAssignmentsUI() {
    if (document.getElementById('setupAssignmentsList')) {
        loadSetupData();
    } else {
        if (typeof cache !== 'undefined' && cache.invalidateAssignments) {
            cache.invalidateAssignments(currentWorkspace);
        }
        loadDashboard(true);
    }
}

async function loadSetupData() {
    await loadAct4ConnectorFlags();
    const container = document.getElementById('setupAssignmentsList');
    if (!container) {
        return;
    }
    try {
        const workspaceId = currentWorkspace || 'default_workspace';

        const assignmentsResponse = await authFetch(
            `/api/workspaces/${workspaceId}/assignments`
        );
        if (assignmentsResponse.ok) {
            const assignmentsData = await assignmentsResponse.json();
            displaySetupAssignments(assignmentsData.assignments || []);
        }

        const credentialsResponse = await authFetch(
            `/api/workspaces/${workspaceId}/credentials`
        );
        if (credentialsResponse.ok) {
            const credentialsData = await credentialsResponse.json();
            updateSetupConnectorStatus(credentialsData);
        }

        await loadSetupCtolenSchedule();
    } catch (error) {
        console.error('Error loading setup data:', error);
        container.innerHTML =
            '<div class="text-center py-8 text-red-500">Error loading data</div>';
    }
}

async function loadSetupCtolenSchedule() {
    const workspaceId = currentWorkspace || 'default_workspace';
    try {
        const response = await authFetch(`/api/workspaces/${workspaceId}/ctolens/schedule`);
        if (!response.ok) return;
        const data = await response.json();
        const schedule = data.schedule || {};
        const flagEnabled = !!data.scheduled_enrichment_enabled;
        const disabledEl = document.getElementById('setupCtolenScheduleDisabled');
        const saveBtn = document.getElementById('setupSaveCtolenScheduleBtn');
        if (disabledEl) disabledEl.classList.toggle('hidden', flagEnabled);
        if (saveBtn) saveBtn.disabled = !flagEnabled;

        const setVal = (id, fn) => { const el = document.getElementById(id); if (el) fn(el); };
        setVal('setupCtolenScheduleEnabled', el => { el.checked = !!schedule.enabled; });
        setVal('setupCtolenScheduleOnImport', el => { el.checked = !!schedule.on_import; });
        setVal('setupCtolenScheduleFrequency', el => { el.value = schedule.frequency || 'manual_only'; });
        setVal('setupCtolenScheduleTimeUtc', el => { el.value = schedule.time_utc || '06:00'; });
        setVal('setupCtolenScheduleDay', el => { el.value = schedule.day_of_week || 'monday'; });

        const runStatus = data.run_status || {};
        const statusEl = document.getElementById('setupCtolenRunStatus');
        if (statusEl && runStatus.last_run_at) {
            statusEl.classList.remove('hidden');
            const conn = (runStatus.connectors_attempted || []).join(', ') || 'none';
            statusEl.innerHTML = '<div class="font-medium text-gray-800 mb-1">Last run</div>'
                + '<div>' + runStatus.last_run_at + ' · ' + (runStatus.last_run_type || 'unknown') + ' · ' + (runStatus.status || 'unknown') + '</div>'
                + '<div class="mt-1">Metrics fetched: ' + (runStatus.metrics_fetched ? 'yes' : 'no') + ' · Connectors: ' + conn + '</div>';
        }
    } catch (error) {
        console.error('Error loading CTOLens schedule:', error);
    }
}

async function saveSetupCtolenSchedule() {
    const workspaceId = currentWorkspace || 'default_workspace';
    const msgEl = document.getElementById('setupCtolenScheduleMessage');
    const payload = {
        enabled: document.getElementById('setupCtolenScheduleEnabled')?.checked || false,
        on_import: document.getElementById('setupCtolenScheduleOnImport')?.checked || false,
        frequency: document.getElementById('setupCtolenScheduleFrequency')?.value || 'manual_only',
        time_utc: document.getElementById('setupCtolenScheduleTimeUtc')?.value || '06:00',
        day_of_week: document.getElementById('setupCtolenScheduleDay')?.value || 'monday',
    };
    try {
        const response = await authFetch(`/api/workspaces/${workspaceId}/ctolens/schedule`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!msgEl) return;
        msgEl.classList.remove('hidden');
        if (!response.ok) {
            msgEl.className = 'mb-4 text-sm rounded px-4 py-3 bg-red-100 text-red-700 border border-red-200';
            msgEl.textContent = data.error || 'Failed to save schedule';
            return;
        }
        msgEl.className = 'mb-4 text-sm rounded px-4 py-3 bg-green-100 text-green-700 border border-green-200';
        msgEl.textContent = 'Schedule saved.';
        loadSetupCtolenSchedule();
    } catch (error) {
        if (msgEl) {
            msgEl.classList.remove('hidden');
            msgEl.className = 'mb-4 text-sm rounded px-4 py-3 bg-red-100 text-red-700 border border-red-200';
            msgEl.textContent = 'Failed to save schedule: ' + error.message;
        }
    }
}

// Global variable to track selected assignment
let selectedAssignmentId = null;

function displaySetupAssignments(assignments) {
    const container = document.getElementById('setupAssignmentsList');
    if (!container) {
        return;
    }
    
    if (assignments.length === 0) {
        container.innerHTML = `
            <div class="text-center py-8 text-gray-500">
                <div class="text-4xl mb-4">📋</div>
                <p class="mb-4">No assignments yet</p>
                <button onclick="showCreateAssignmentModal()" class="text-blue-600 hover:underline">
                    Create your first assignment
                </button>
            </div>
        `;
        return;
    }

    container.innerHTML = assignments.map(assignment => `
        <div id="assignment-${assignment.id}" class="border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer assignment-card ${selectedAssignmentId === assignment.id ? 'ring-2 ring-blue-500 bg-blue-50' : ''}" 
             onclick="selectAssignment('${assignment.id}', '${assignment.name || assignment.id}')">
            <div class="flex justify-between items-start">
                <div class="flex-1">
                    <div class="flex items-center space-x-2">
                        <h4 class="font-medium text-gray-800">${assignment.name || assignment.id}</h4>
                        ${selectedAssignmentId === assignment.id ? '<span class="text-blue-600 text-sm">✓ Selected</span>' : ''}
                    </div>
                    <p class="text-sm text-gray-600 mt-1">${assignment.description || 'No description'}</p>
                    <div class="flex items-center space-x-4 text-xs text-gray-500 mt-2">
                        <span>👥 ${assignment.team_size || 'N/A'} team</span>
                        <span>💰 $${(assignment.monthly_burn_rate || 0).toLocaleString()}/mo</span>
                        <span class="px-2 py-1 rounded bg-green-100 text-green-600">${assignment.status || 'active'}</span>
                    </div>
                </div>
                <div class="flex items-center space-x-2" onclick="event.stopPropagation()">
                    <button onclick="editAssignment('${assignment.id}')" class="text-blue-600 hover:text-blue-800 text-sm">
                        Edit
                    </button>
                    <button onclick="deleteSetupAssignment('${assignment.id}')" class="text-red-600 hover:text-red-800 text-sm">
                        Delete
                    </button>
                </div>
            </div>
            ${getSetupConnectorBadges(assignment)}
        </div>
    `).join('');
}

function selectAssignment(assignmentId, assignmentName) {
    console.log('🎯 Selecting assignment:', assignmentId, assignmentName);
    selectedAssignmentId = assignmentId;
    
    // Update visual selection in setup cards
    document.querySelectorAll('.assignment-card').forEach(card => {
        card.classList.remove('ring-2', 'ring-blue-500', 'bg-blue-50');
    });
    const assignmentCard = document.getElementById(`assignment-${assignmentId}`);
    if (assignmentCard) {
        assignmentCard.classList.add('ring-2', 'ring-blue-500', 'bg-blue-50');
    }
    
    // Refresh assignment display to show selection in table
    const currentTab = document.querySelector('.tab-button.active-tab');
    if (currentTab && currentTab.id.includes('assignment')) {
        // Refresh current assignment view
        const currentAssignmentId = currentTab.id.replace('tab-assignment-', '');
        showTab(`assignment-${currentAssignmentId}`);
    } else {
        // Refresh overview to update table selection
        showTab('overview');
    }
    
    // Show detail section and hide "no selection" message
    const noSelectionEl = document.getElementById('noAssignmentSelected');
    const connectorsEl = document.getElementById('assignmentConnectors');
    const selectedNameEl = document.getElementById('selectedAssignmentName');
    
    if (noSelectionEl) noSelectionEl.classList.add('hidden');
    if (connectorsEl) connectorsEl.classList.remove('hidden');
    if (selectedNameEl) selectedNameEl.textContent = assignmentName;
    
    // Load connectors for selected assignment
    loadAssignmentConnectors(assignmentId);
}

async function loadAssignmentConnectors(assignmentId) {
    try {
        const workspaceId = currentWorkspace || 'default_workspace';
        const response = await fetch(`/api/workspaces/${workspaceId}/assignments`);
        
        if (response.ok) {
            const data = await response.json();
            const assignment = data.assignments.find(a => a.id === assignmentId);
            
            if (assignment) {
                displayConnectorsForAssignment(assignment);
            }
        }
    } catch (error) {
        console.error('Error loading assignment connectors:', error);
    }
}

function displayConnectorsForAssignment(assignment) {
    const container = document.getElementById('configuredConnectorsList');
    const noConnectorsMsg = document.getElementById('noConnectorsMessage');
    const metrics_config = assignment.metrics_config || {};
    
    // Defensive check - if elements don't exist, skip display logic
    if (!container || !noConnectorsMsg) {
        console.warn('Required elements not found for connector display');
        return;
    }
    
    // Get all configured connectors
    const configuredConnectors = [];
    const connectorTypes = getConnectorsForAssignmentDisplay(metrics_config);
    
    connectorTypes.forEach(type => {
        const config = metrics_config[type];
        if (config && config.enabled) {
            const authInstance = config.auth_instance || {};
            const isConfigured = authInstance.auth_configured;
            
            configuredConnectors.push({
                type,
                name: type.charAt(0).toUpperCase() + type.slice(1),
                configured: isConfigured,
                credentials: authInstance.credentials || {},
                config: config
            });
        }
    });
    
    if (configuredConnectors.length === 0) {
        container.innerHTML = '';
        noConnectorsMsg.classList.remove('hidden');
    } else {
        noConnectorsMsg.classList.add('hidden');
        container.innerHTML = configuredConnectors.map(connector => {
            const statusBadge = connector.configured 
                ? '<span class="px-2 py-1 text-xs rounded bg-green-100 text-green-600">✅ Configured</span>'
                : '<span class="px-2 py-1 text-xs rounded bg-yellow-100 text-yellow-600">⚡ Enabled</span>';
                
            const credentialCount = Object.keys(connector.credentials).length;
            
            return `
                <div class="border rounded-lg p-4">
                    <div class="flex justify-between items-start">
                        <div class="flex items-center space-x-3">
                            <div class="w-10 h-10 ${getConnectorColor(connector.type)} rounded text-white flex items-center justify-center font-bold">
                                ${getConnectorIcon(connector.type)}
                            </div>
                            <div>
                                <h4 class="font-medium text-gray-800">${connector.name}</h4>
                                <div class="flex items-center space-x-2 text-sm text-gray-600">
                                    ${statusBadge}
                                    ${credentialCount > 0 ? `<span>${credentialCount} credential${credentialCount > 1 ? 's' : ''}</span>` : ''}
                                </div>
                            </div>
                        </div>
                        <div class="flex space-x-2">
                            <button onclick="editConnector('${assignment.id}', '${connector.type}')" class="text-blue-600 hover:text-blue-800 text-sm">
                                ${connector.configured ? 'Edit' : 'Configure'}
                            </button>
                            <button onclick="deleteConnector('${assignment.id}', '${connector.type}')" class="text-red-600 hover:text-red-800 text-sm">
                                Remove
                            </button>
                        </div>
                    </div>
                    ${getConnectorSummary(connector)}
                </div>
            `;
        }).join('');
    }
}

function getConnectorColor(type) {
    const colors = {
        github: 'bg-gray-800',
        jira: 'bg-blue-600',
        aws: 'bg-orange-500',
        openai: 'bg-green-600',
        railway: 'bg-purple-700',
        vercel: 'bg-black',
        azure: 'bg-sky-600',
    };
    return colors[type] || 'bg-gray-500';
}

function getConnectorIcon(type) {
    const icons = {
        github: 'GH',
        jira: 'JI',
        aws: 'AWS',
        openai: 'AI',
        railway: 'RW',
        vercel: 'VC',
        azure: 'AZ',
    };
    return icons[type] || '?';
}

function getConnectorSummary(connector) {
    const creds = connector.credentials;
    if (!connector.configured || !creds) return '';
    
    let summary = '';
    if (connector.type === 'github' && creds.github_repos) {
        summary = `<div class="mt-2 text-sm text-gray-600">📁 Repos: ${creds.github_repos}</div>`;
    } else if (connector.type === 'jira' && creds.jira_url) {
        summary = `<div class="mt-2 text-sm text-gray-600">🌐 ${creds.jira_url}</div>`;
    } else if (connector.type === 'aws' && creds.aws_region) {
        summary = `<div class="mt-2 text-sm text-gray-600">🌍 Region: ${creds.aws_region}</div>`;
    } else if (connector.type === 'railway' && creds.railway_project_id) {
        summary = `<div class="mt-2 text-sm text-gray-600">Project: ${creds.railway_project_id}</div>`;
    } else if (connector.type === 'vercel' && creds.vercel_project_id) {
        summary = `<div class="mt-2 text-sm text-gray-600">Project: ${creds.vercel_project_id}</div>`;
    } else if (connector.type === 'azure' && creds.azure_subscription_id) {
        summary = `<div class="mt-2 text-sm text-gray-600">Subscription: ${creds.azure_subscription_id}</div>`;
    }
    return summary;
}

async function updateConnectorStatusForAssignment(assignmentId) {
    try {
        const workspaceId = currentWorkspace || 'default_workspace';
        const response = await fetch(`/api/workspaces/${workspaceId}/assignments`);
        
        if (response.ok) {
            const data = await response.json();
            const assignment = data.assignments.find(a => a.id === assignmentId);
            
            if (assignment && assignment.metrics_config) {
                const connectors = ALL_CONNECTOR_TYPES;
                
                connectors.forEach(connectorType => {
                    const statusElement = document.getElementById(`${connectorType}-setup-status`);
                    const config = assignment.metrics_config[connectorType];
                    
                    if (statusElement) {
                        if (config && config.auth_instance && config.auth_instance.auth_configured) {
                            statusElement.textContent = '✅ Configured';
                            statusElement.className = 'text-sm text-green-600';
                        } else if (config && config.enabled) {
                            statusElement.textContent = '⚡ Enabled (needs credentials)';
                            statusElement.className = 'text-sm text-yellow-600';
                        } else {
                            statusElement.textContent = 'Not enabled';
                            statusElement.className = 'text-sm text-gray-600';
                        }
                    }
                });
            }
        }
    } catch (error) {
        console.error('Error updating connector status:', error);
    }
}

function getSetupConnectorBadges(assignment) {
    const authInstances = assignment.auth_instances || {};
    const connectors = ALL_CONNECTOR_TYPES;
    
    const configuredConnectors = connectors.filter(connector => {
        const instance = authInstances[connector];
        return instance && instance.credentials && Object.keys(instance.credentials).length > 0;
    });
    
    if (configuredConnectors.length === 0) {
        return '<div class="text-sm text-gray-400 mt-3">No connectors configured</div>';
    }
    
    return `<div class="flex items-center space-x-2 mt-3">
        <span class="text-sm text-gray-600">Connectors:</span>
        ${configuredConnectors.map(connector => `
            <span class="px-2 py-1 text-xs rounded bg-blue-100 text-blue-600">${connector.toUpperCase()}</span>
        `).join('')}
    </div>`;
}

function updateSetupConnectorStatus(credentialsData) {
    const connectors = credentialsData.connectors || {};
    
    Object.keys(connectors).forEach(connectorType => {
        const connector = connectors[connectorType];
        const statusElement = document.getElementById(`${connectorType}-setup-status`);
        
        // Check if element exists (setup panel might not be loaded yet)
        if (statusElement) {
            if (connector.configured) {
                statusElement.textContent = `✅ ${connector.assignments?.length || 0} assignments`;
                statusElement.className = 'text-sm text-green-600';
            } else {
                statusElement.textContent = 'Not configured';
                statusElement.className = 'text-sm text-gray-600';
            }
        }
    });
}

async function deleteSetupAssignment(assignmentId) {
    if (!confirm(`Delete assignment "${assignmentId}"?\n\nThis will remove all associated data.`)) {
        return;
    }

    try {
        const workspaceId = currentWorkspace || 'default_workspace';
        const response = await authFetch(
            `/api/workspaces/${workspaceId}/assignments/${assignmentId}`,
            { method: 'DELETE' }
        );

        if (response.ok) {
            refreshAssignmentsUI();
        } else {
            const result = await response.json();
            alert(`Failed to delete: ${result.error || 'Unknown error'}`);
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

function captureDashboardView() {
    if (document.getElementById('setupAssignmentsList')) {
        return { mode: 'setup' };
    }
    const activeTabEl = document.querySelector('#dashboard-content .tab-button.active-tab');
    if (activeTabEl && activeTabEl.id && activeTabEl.id.startsWith('tab-')) {
        return { mode: 'tab', tabId: activeTabEl.id.slice(4) };
    }
    return { mode: 'tab', tabId: 'overview' };
}

function restoreDashboardView(restoreView) {
    if (!restoreView) {
        showTab('overview');
        return;
    }
    if (restoreView.mode === 'setup') {
        showSetupPanel();
        return;
    }
    const tabId = restoreView.tabId || 'overview';
    if (document.getElementById('tab-' + tabId)) {
        showTab(tabId);
    } else {
        showTab('overview');
    }
}

async function loadDashboard(forceRefresh) {
    try {
        await loadTrialStatus();
        const workspaceId = currentWorkspace;
        if (!workspaceId) {
            document.getElementById('dashboard-content').innerHTML =
                '<div class="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded">Select a workspace before loading assignments.</div>';
            return;
        }

        console.log('🔍 Loading assignments for workspace:', workspaceId, forceRefresh ? '(fresh)' : '');
        const apiUrl = `/api/workspaces/${workspaceId}/assignments`;
        const cacheKey = `assignments_${workspaceId}`;

        let response;
        if (forceRefresh) {
            cache.invalidateAssignments(workspaceId);
            response = await authFetch(apiUrl);
        } else {
            response = await cachedFetch(apiUrl, {
                headers: getAuthHeaders()
            }, cacheKey, 3 * 60 * 1000);
        }
        console.log('📡 Response status:', response.status);
        
        const data = await response.json();
        console.log('📦 Data received:', data);
        console.log('📊 Data type:', typeof data);
        console.log('📋 Is array?:', Array.isArray(data));
        
        if (data.error) {
            document.getElementById('dashboard-content').innerHTML = 
                '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">Error: ' + data.error + '</div>';
            return;
        }
        
        // Handle both array and object wrapper formats
        const assignmentsData = Array.isArray(data) ? data : data.assignments;
        console.log('✅ Assignments to display:', assignmentsData);
        
        // Tag each row with workspace context; hide soft-archived rows from main UI
        const scoped = (assignmentsData || [])
            .filter(function(a) { return (a.status || 'active') !== 'archived'; })
            .map(function(a) {
                return Object.assign({}, a, { workspace_id: workspaceId });
            });
        
        // Store assignments globally for management functions
        assignments = scoped;
        
        const restoreView = captureDashboardView();
        displayAssignments(scoped, restoreView);
        
    } catch (error) {
        document.getElementById('dashboard-content').innerHTML = 
            '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">Failed to load dashboard: ' + error.message + '</div>';
    }
}

function displayAssignments(assignments, restoreView) {
    if (assignments.length === 0) {
        // Show welcome message with "+" tab for creating first assignment
        let html = '<div class="bg-white rounded-lg shadow-lg mb-6">';
        html += '<div class="dashboard-tab-scroll"><div class="dashboard-tab-row flex border-b border-gray-200" role="tablist">';
        html += '<button onclick="createNewAssignment()" id="tab-add-new" class="px-6 py-4 text-sm font-medium text-blue-600 hover:text-blue-800 hover:border-b-2 hover:border-blue-600 tab-button">';
        html += '➕ Create Your First Assignment';
        html += '</button>';
        html += '</div></div></div>';
        
        html += `
            <div class="bg-blue-50 border border-blue-200 rounded-lg p-8 text-center">
                <div class="text-6xl mb-4">🚀</div>
                <h2 class="text-2xl font-bold text-gray-800 mb-4">Welcome to CTO Lens!</h2>
                <p class="text-gray-600 mb-6 max-w-md mx-auto">
                    Get started by creating your first assignment. Click the "Create Your First Assignment" tab above to add projects and configure integrations.
                </p>
            </div>`;
        
        document.getElementById('dashboard-content').innerHTML = html;
        return;
    }
    
    // Store assignments globally for tab switching
    window.assignments = assignments;
    
    // Create tab navigation
    let html = '<div class="bg-white rounded-lg shadow-lg mb-6">';
    html += '<div class="dashboard-tab-scroll"><div class="dashboard-tab-row flex border-b border-gray-200" role="tablist">';
    
    // Main Overview Tab
    html += '<button onclick="showTab(' + "'overview'" + ')" id="tab-overview" class="px-6 py-4 text-sm font-medium text-gray-700 hover:text-blue-600 hover:border-b-2 hover:border-blue-600 tab-button active-tab">';
    html += '📊 Overview (' + assignments.length + ')';
    html += '</button>';
    
    // Individual Assignment Tabs
    assignments.forEach(assignment => {
        const statusEmoji = assignment.status === 'active' ? '🟢' : 
                           assignment.status === 'completed' ? '🔵' : '🟡';
        html += '<button onclick="showTab(' + "'assignment-" + assignment.id + "'" + ')" id="tab-assignment-' + assignment.id + '" class="px-6 py-4 text-sm font-medium text-gray-700 hover:text-blue-600 hover:border-b-2 hover:border-blue-600 tab-button">';
        html += statusEmoji + ' ' + (assignment.name || assignment.id);
        html += '</button>';
    });
    
    // Add "+" tab for creating new assignments
    html += '<button onclick="createNewAssignment()" id="tab-add-new" class="px-6 py-4 text-sm font-medium text-gray-500 hover:text-blue-600 hover:border-b-2 hover:border-blue-600 tab-button border-l border-gray-200">';
    html += '➕ New Assignment';
    html += '</button>';
    
    html += '</div></div>';
    html += '</div>';
    
    // Tab Content Areas
    html += '<div id="tab-content">';
    
    // Overview Tab Content
    html += '<div id="overview-content" class="tab-content">';
    html += generateOverviewContent(assignments);
    html += '</div>';
    
    // Individual Assignment Tab Contents
    assignments.forEach(assignment => {
        html += '<div id="assignment-' + assignment.id + '-content" class="tab-content hidden">';
        html += generateAssignmentContent(assignment);
        html += '</div>';
    });
    
    html += '</div>';
    
    document.getElementById('dashboard-content').innerHTML = html;
    
    // Initialize metrics after displaying assignments
    initializeAssignmentMetrics();

    loadOverviewPanels();
    updateChatbotPrompts();
    restoreDashboardView(restoreView);
}

// Modern UI: Handle "+" tab click for creating new assignments
function createNewAssignment() {
    if (!assertTrialWrite('new assignments')) return;
    showCreateAssignmentModal();
}
    
// Phase 5B: Auto-load basic metrics for each assignment after displaying assignments
function initializeAssignmentMetrics() {
    if (typeof assignments !== 'undefined' && assignments) {
        assignments.forEach(assignment => {
            if (assignment.metrics_config) {
                loadBasicMetrics(assignment.id);
            }
        });
    }
}
