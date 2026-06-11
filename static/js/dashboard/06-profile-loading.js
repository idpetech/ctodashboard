/* CTO Lens dashboard module: 06-profile-loading.js */
async function editAssignment(assignmentId) {
    try {
        // Fetch assignment data directly rather than relying on global state
        const workspaceId = currentWorkspace || 'default_workspace';
        const response = await fetch(`/api/workspaces/${workspaceId}/assignments`);
        
        if (!response.ok) {
            throw new Error('Failed to load assignment data');
        }
        
        const data = await response.json();
        const assignment = data.assignments.find(a => a.id === assignmentId);
        
        if (!assignment) {
            showAssignmentEditMessage('Assignment not found', 'error');
            return;
        }
        
        console.log('Loading assignment for edit:', assignment);
        
        // Populate modal form with current assignment data
        document.getElementById('assignment-id').value = assignment.id;
        document.getElementById('assignment-name').value = assignment.name || assignment.id;
        document.getElementById('assignment-description').value = assignment.description || '';
        document.getElementById('assignment-status').value = assignment.status || 'active';
        document.getElementById('assignment-team-size').value = assignment.team_size || '';
        document.getElementById('assignment-burn-rate').value = assignment.monthly_burn_rate || '';
        document.getElementById('assignment-target-burn').value = assignment.target_monthly_burn || '';
        document.getElementById('assignment-start-date').value = assignment.start_date || '';
        
        // Load connectors for the assignment
        console.log('Loading connectors for assignment:', assignmentId);
        displayAssignmentModalConnectors(assignment);
        
        // Show the modal
        document.getElementById('assignment-edit-modal').classList.remove('hidden');
        
    } catch (error) {
        console.error('Error loading assignment:', error);
        showAssignmentEditMessage('Failed to load assignment: ' + error.message, 'error');
    }
}

function hideAssignmentEditModal() {
    document.getElementById('assignment-edit-modal').classList.add('hidden');
    // Clear any messages
    document.getElementById('assignment-edit-message').classList.add('hidden');
    // Reset form
    document.getElementById('assignment-edit-form').reset();
}

async function saveAssignmentChanges(event) {
    event.preventDefault();
    
    // Phase 5C: Enhanced loading states
    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.textContent;
    const formModal = document.getElementById('assignment-edit-modal');
    
    // Show loading states
    submitBtn.disabled = true;
    submitBtn.textContent = 'Saving...';
    submitBtn.classList.add('button-loading');
    
    // Add loading overlay to form
    if (!formModal.querySelector('.loading-overlay')) {
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = '<div class="flex items-center"><div class="loading-spinner"></div><span class="text-gray-600">Updating assignment...</span></div>';
        formModal.querySelector('.bg-white').style.position = 'relative';
        formModal.querySelector('.bg-white').appendChild(overlay);
    }
    
    const assignmentId = document.getElementById('assignment-id').value;
    const formData = {
        name: document.getElementById('assignment-name').value,
        description: document.getElementById('assignment-description').value,
        status: document.getElementById('assignment-status').value,
        team_size: parseInt(document.getElementById('assignment-team-size').value) || null,
        monthly_burn_rate: parseInt(document.getElementById('assignment-burn-rate').value) || null,
        target_monthly_burn: parseInt(document.getElementById('assignment-target-burn').value) || null,
        start_date: document.getElementById('assignment-start-date').value || null
    };
    
    try {
        const url = workspaceAssignmentUrl(assignmentId);
        if (!url) return;
        const response = await authFetch(url, {
            method: 'PUT',
            body: JSON.stringify(formData)
        });

        let data = {};
        try { data = await response.json(); } catch (e) { data = {}; }

        if (response.ok) {
            showAssignmentEditMessage('Assignment updated successfully!', 'success');
            cache.invalidateAssignments(currentWorkspace);
            setTimeout(async () => {
                hideAssignmentEditModal();
                await loadDashboard(true);
            }, 800);
        } else if (response.status === 401) {
            showAssignmentEditMessage('Your session has expired. Please sign in - your changes are kept and will be saved automatically after you log in.', 'error');
            window._pendingAuthRetry = function() { saveAssignmentChanges(event); };
            showAuthOverlay();
            showLoginForm();
        } else {
            showAssignmentEditMessage(data.error || ('Failed to update assignment (HTTP ' + response.status + ')'), 'error');
        }
    } catch (error) {
        console.error('Error updating assignment:', error);
        showAssignmentEditMessage('Connection error - your changes are still here. Please try again.', 'error');
    } finally {
        // Phase 5C: Clean up loading states
        setTimeout(() => {
            submitBtn.disabled = false;
            submitBtn.textContent = originalBtnText;
            submitBtn.classList.remove('button-loading');
            
            // Remove loading overlay
            const overlay = formModal.querySelector('.loading-overlay');
            if (overlay) {
                overlay.remove();
            }
        }, 800); // Small delay for better UX
    }
}

function showAssignmentEditMessage(message, type) {
    const messageDiv = document.getElementById('assignment-edit-message');
    messageDiv.textContent = message;
    messageDiv.className = `mb-4 p-3 rounded ${type === 'error' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`;
    messageDiv.classList.remove('hidden');
}

// Phase 5B: Assignment Edit Modal Tab Functions
function switchAssignmentTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.assignment-tab-content').forEach(tab => {
        tab.classList.add('hidden');
    });
    
    // Remove active styles from all tab buttons
    document.querySelectorAll('.assignment-tab-btn').forEach(btn => {
        btn.classList.remove('border-blue-500', 'text-blue-600');
        btn.classList.add('border-transparent', 'text-gray-500');
    });
    
    // Show selected tab content
    document.getElementById(tabName + '-tab-content').classList.remove('hidden');
    
    // Add active styles to selected tab button
    const activeBtn = document.getElementById(tabName + '-tab');
    activeBtn.classList.remove('border-transparent', 'text-gray-500');
    activeBtn.classList.add('border-blue-500', 'text-blue-600');
    
    // Load connector config if switching to connectors tab
    if (tabName === 'connectors') {
        loadAssignmentModalConnectors();
    }
}


function loadAssignmentModalConnectors() {
    const assignmentId = document.getElementById('assignment-id').value;
    if (!assignmentId) {
        console.warn('No assignment ID found for loading connectors');
        return;
    }
    
    const assignment = assignments?.find(a => a.id === assignmentId);
    if (!assignment) {
        console.warn('Assignment not found in assignments array:', assignmentId);
        console.log('Available assignments:', assignments?.map(a => a.id));
        return;
    }
    
    console.log('Loading connectors for assignment:', assignmentId);
    displayAssignmentModalConnectors(assignment);
}

function displayAssignmentModalConnectors(assignment) {
    console.log('displayAssignmentModalConnectors called with:', assignment);
    
    const container = document.getElementById('assignmentModalConnectorsList');
    const noConnectorsMsg = document.getElementById('assignmentModalNoConnectors');
    
    if (!container) {
        console.error('assignmentModalConnectorsList element not found');
        return;
    }
    
    if (!noConnectorsMsg) {
        console.error('assignmentModalNoConnectors element not found');
        return;
    }
    
    const metrics_config = assignment.metrics_config || {};
    console.log('Assignment metrics_config:', metrics_config);
    
    // Get all configured connectors
    const configuredConnectors = [];
    const connectorTypes = ['github', 'jira', 'aws', 'openai'];
    
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
            
            const credentialSummary = connector.configured
                ? `<div class="text-xs text-gray-600 mt-1">Last updated: ${new Date(connector.config.auth_instance?.last_updated || '').toLocaleDateString()}</div>`
                : '<div class="text-xs text-red-600 mt-1">Credentials not configured</div>';
            
            return `
                <div class="border rounded-lg p-4 hover:bg-gray-50">
                    <div class="flex justify-between items-start">
                        <div class="flex-1">
                            <div class="flex items-center gap-2 mb-2">
                                <h4 class="font-medium text-gray-800">${connector.name}</h4>
                                ${statusBadge}
                            </div>
                            ${credentialSummary}
                        </div>
                        <div class="flex gap-2">
                            <button onclick="configureAssignmentConnector('${connector.type}')" 
                                    class="text-blue-600 hover:text-blue-800 text-sm">
                                ${connector.configured ? 'Reconfigure' : 'Configure'}
                            </button>
                            <button onclick="removeAssignmentConnector('${connector.type}')" 
                                    class="text-red-600 hover:text-red-800 text-sm">
                                Remove
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }
}

function configureAssignmentConnector(connectorType) {
    const assignmentId = document.getElementById('assignment-id').value;
    if (!assignmentId) {
        alert('Please save the assignment first');
        return;
    }
    
    // Set up the connector configuration in context of this assignment
    selectedAssignmentId = assignmentId;
    selectedConnectorAssignmentId = assignmentId;
    configureConnector(connectorType);
}

function addConnectorToAssignment() {
    const assignmentId = document.getElementById('assignment-id').value;
    if (!assignmentId) {
        alert('Please save the assignment first');
        return;
    }
    
    selectedAssignmentId = assignmentId;
    showCreateConnectorModal();
}

async function removeAssignmentConnector(connectorType) {
    const assignmentId = document.getElementById('assignment-id').value;
    if (!assignmentId) return;
    
    if (!confirm(`Remove ${connectorType} connector from this assignment?`)) return;
    
    try {
        const workspaceId = currentWorkspace || 'default_workspace';
        
        // Remove the connector by disabling it
        const assignment = assignments?.find(a => a.id === assignmentId);
        if (assignment && assignment.metrics_config && assignment.metrics_config[connectorType]) {
            assignment.metrics_config[connectorType].enabled = false;
            
            const response = await fetch(`/api/workspaces/${workspaceId}/assignments/${assignmentId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders()
                },
                body: JSON.stringify(assignment)
            });
            
            if (response.ok) {
                // Refresh the connector list
                loadAssignmentModalConnectors();
                showAssignmentEditMessage('Connector removed successfully', 'success');
            } else {
                throw new Error('Failed to remove connector');
            }
        }
    } catch (error) {
        console.error('Error removing connector:', error);
        showAssignmentEditMessage('Failed to remove connector: ' + error.message, 'error');
    }
}

function loadAssignmentMetricsConfig() {
    const assignmentId = document.getElementById('assignment-id').value;
    if (!assignmentId) return;
    
    const assignment = assignments?.find(a => a.id === assignmentId);
    if (!assignment || !assignment.metrics_config) {
        document.getElementById('metrics-config-summary').innerHTML = 
            '<div class="text-gray-500">No metrics configured for this assignment yet.</div>';
        return;
    }
    
    const config = assignment.metrics_config;
    let summary = '<div class="space-y-2">';
    
    // Check each connector
    if (config.github?.enabled) {
        summary += `<div class="flex items-center space-x-2">
            <span class="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded">🐙 GitHub</span>
            <span class="text-xs text-gray-600">Org: ${config.github.org || 'N/A'} | Repos: ${config.github.repos?.length || 0}</span>
        </div>`;
    }
    
    if (config.jira?.enabled) {
        summary += `<div class="flex items-center space-x-2">
            <span class="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">🎫 Jira</span>
            <span class="text-xs text-gray-600">Project: ${config.jira.project_key || 'N/A'}</span>
        </div>`;
    }
    
    if (config.aws?.enabled) {
        summary += `<div class="flex items-center space-x-2">
            <span class="px-2 py-1 bg-orange-100 text-orange-800 text-xs rounded">☁️ AWS</span>
            <span class="text-xs text-gray-600">Account: ${config.aws.account_id || 'N/A'}</span>
        </div>`;
    }
    
    if (config.railway?.enabled) {
        summary += `<div class="flex items-center space-x-2">
            <span class="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">🚄 Railway</span>
            <span class="text-xs text-gray-600">Project: ${config.railway.project_id || 'N/A'}</span>
        </div>`;
    }
    
    if (config.openai?.enabled) {
        summary += `<div class="flex items-center space-x-2">
            <span class="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded">🤖 OpenAI</span>
            <span class="text-xs text-gray-600">Usage tracking enabled</span>
        </div>`;
    }
    
    summary += '</div>';
    
    if (!config.github?.enabled && !config.jira?.enabled && !config.aws?.enabled && !config.railway?.enabled && !config.openai?.enabled) {
        summary = '<div class="text-gray-500">No service connectors enabled for this assignment.</div>';
    }
    
    document.getElementById('metrics-config-summary').innerHTML = summary;
}

function toggleAssignmentStatus(assignmentId) {
    // Find current status
    const assignment = assignments?.find(a => a.id === assignmentId);
    if (!assignment) {
        alert('Assignment not found');
        return;
    }
    
    // Cycle through statuses: active -> paused -> completed -> active
    const statusCycle = { 'active': 'paused', 'paused': 'completed', 'completed': 'active' };
    const currentStatus = assignment.status || 'active';
    const newStatus = statusCycle[currentStatus] || 'active';
    
    // Confirm the change
    if (!confirm(`Change status from "${currentStatus}" to "${newStatus}"?`)) {
        return;
    }
    
    // Call API to update status
    updateAssignmentStatus(assignmentId, newStatus);
}

async function updateAssignmentStatus(assignmentId, newStatus) {
    try {
        const url = workspaceAssignmentUrl(assignmentId);
        if (!url) return;
        const response = await authFetch(url, {
            method: 'PUT',
            body: JSON.stringify({ status: newStatus })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Update local assignment data
            const assignmentIndex = assignments.findIndex(a => a.id === assignmentId);
            if (assignmentIndex !== -1) {
                assignments[assignmentIndex].status = newStatus;
            }
            cache.invalidateAssignments(currentWorkspace);
            loadDashboard(true);
        } else {
            alert(data.error || 'Failed to update status');
        }
    } catch (error) {
        console.error('Error updating status:', error);
        alert('Connection error. Please try again.');
    }
}

function deleteAssignment(assignmentId) {
    // Find assignment for confirmation
    const assignment = assignments?.find(a => a.id === assignmentId);
    if (!assignment) {
        alert('Assignment not found');
        return;
    }
    
    const assignmentName = assignment.name || assignmentId;
    
    // Double confirmation for deletion
    if (!confirm(`Are you sure you want to delete "${assignmentName}"? This cannot be undone.`)) {
        return;
    }
    
    if (!confirm('This will permanently delete the assignment and all its data. Proceed?')) {
        return;
    }
    
    // Call API to delete assignment
    performAssignmentDeletion(assignmentId);
}

async function performAssignmentDeletion(assignmentId) {
    try {
        const url = workspaceAssignmentUrl(assignmentId);
        if (!url) return;
        const response = await authFetch(url, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Remove from local assignments array
            const assignmentIndex = assignments.findIndex(a => a.id === assignmentId);
            if (assignmentIndex !== -1) {
                assignments.splice(assignmentIndex, 1);
            }
            cache.invalidateAssignments(currentWorkspace);
            loadDashboard(true);
            alert('Assignment deleted successfully');
        } else {
            alert(data.error || 'Failed to delete assignment');
        }
    } catch (error) {
        console.error('Error deleting assignment:', error);
        alert('Connection error. Please try again.');
    }
}

// Phase 5A: Profile Management Functions
async function showProfileModal() {
    await refreshCurrentUserFromServer();
    if (currentUser) {
        document.getElementById('profile-name').value = currentUser.name || currentUser.display_name || '';
        document.getElementById('profile-email').value = currentUser.email || '';
    }
    if (trialState) {
        applyTrialUI(trialState);
    }
    await loadAdminTrialList();
    document.getElementById('profile-modal').classList.remove('hidden');
}

function hideProfileModal() {
    document.getElementById('profile-modal').classList.add('hidden');
    // Clear password fields
    document.getElementById('new-password').value = '';
    document.getElementById('confirm-password').value = '';
    // Hide any messages
    document.getElementById('profile-message').classList.add('hidden');
}

async function saveProfile() {
    // Phase 5C: Enhanced loading states for profile
    const saveBtn = document.querySelector('.profile-save-btn');
    const originalBtnText = saveBtn?.textContent || 'Save Changes';
    const profileModal = document.getElementById('profile-modal');
    
    const newName = document.getElementById('profile-name').value;
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    
    // Validate password if provided
    if (newPassword && newPassword !== confirmPassword) {
        showProfileMessage('Passwords do not match', 'error');
        return;
    }
    
    if (newPassword && newPassword.length < 6) {
        showProfileMessage('Password must be at least 6 characters', 'error');
        return;
    }
    
    // Prepare update data
    const updateData = {};
    if (newName && newName !== currentUser?.name) {
        updateData.display_name = newName;
    }
    if (newPassword) {
        updateData.password = newPassword; // Fixed API field name
    }
    
    // Only make API call if there are changes
    if (Object.keys(updateData).length === 0) {
        showProfileMessage('No changes to save', 'info');
        return;
    }
    
    // Show loading states
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.textContent = 'Updating...';
        saveBtn.classList.add('button-loading');
    }
    
    // Add loading overlay
    if (profileModal && !profileModal.querySelector('.loading-overlay')) {
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = '<div class="flex items-center"><div class="loading-spinner"></div><span class="text-gray-600">Updating profile...</span></div>';
        profileModal.querySelector('.bg-white').style.position = 'relative';
        profileModal.querySelector('.bg-white').appendChild(overlay);
    }
    
    try {
        const response = await fetch('/api/auth/profile', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(updateData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showProfileMessage('Profile updated successfully!', 'success');
            
            // Update local user data
            if (updateData.display_name && currentUser) {
                currentUser.name = updateData.display_name;
                document.getElementById('user-display-name').textContent = updateData.display_name;
                localStorage.setItem('current_user', JSON.stringify(currentUser));
            }
            
            // Clear password fields
            document.getElementById('new-password').value = '';
            document.getElementById('confirm-password').value = '';
            
            setTimeout(() => hideProfileModal(), 2000);
        } else {
            showProfileMessage(data.error || 'Failed to update profile', 'error');
        }
    } catch (error) {
        console.error('Error updating profile:', error);
        showProfileMessage('Connection error. Please try again.', 'error');
    } finally {
        // Phase 5C: Clean up loading states
        setTimeout(() => {
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = originalBtnText;
                saveBtn.classList.remove('button-loading');
            }
            
            // Remove loading overlay
            if (profileModal) {
                const overlay = profileModal.querySelector('.loading-overlay');
                if (overlay) {
                    overlay.remove();
                }
            }
        }, 800);
    }
}

function showProfileMessage(message, type) {
    const messageDiv = document.getElementById('profile-message');
    messageDiv.textContent = message;
    messageDiv.className = `mb-4 p-3 rounded ${type === 'error' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`;
    messageDiv.classList.remove('hidden');
}

// Phase 5C: Search/Filtering Functions
