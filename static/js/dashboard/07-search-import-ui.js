/* CTO Lens dashboard module: 07-search-import-ui.js */
function showSearchOverlay() {
    document.getElementById('search-overlay').classList.remove('hidden');
    document.getElementById('search-input').focus();
    
    // Show current assignments count
    const totalCount = assignments ? assignments.length : 0;
    document.getElementById('total-count').textContent = totalCount;
    document.getElementById('search-status').classList.remove('hidden');
    
    // Initialize with current assignments
    if (assignments) {
        displaySearchResults(assignments);
    }
}

function hideSearchOverlay() {
    document.getElementById('search-overlay').classList.add('hidden');
    // Clear search form
    document.getElementById('search-input').value = '';
    document.getElementById('filter-status').value = '';
    document.getElementById('filter-team-size').value = '';
    document.getElementById('filter-connectors').value = '';
    document.getElementById('search-status').classList.add('hidden');
}

function performSearch() {
    if (!assignments) return;
    
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    const statusFilter = document.getElementById('filter-status').value;
    const teamSizeFilter = document.getElementById('filter-team-size').value;
    const connectorFilter = document.getElementById('filter-connectors').value;
    
    const filtered = assignments.filter(assignment => {
        // Text search
        const searchableText = [
            assignment.name,
            assignment.description,
            assignment.id,
            ...(assignment.team?.tech_stack || [])
        ].join(' ').toLowerCase();
        
        const matchesSearch = !searchTerm || searchableText.includes(searchTerm);
        
        // Status filter
        const matchesStatus = !statusFilter || assignment.status === statusFilter;
        
        // Team size filter
        let matchesTeamSize = !teamSizeFilter;
        if (teamSizeFilter && assignment.team_size) {
            const teamSize = assignment.team_size;
            switch(teamSizeFilter) {
                case '1': matchesTeamSize = teamSize === 1; break;
                case '2-5': matchesTeamSize = teamSize >= 2 && teamSize <= 5; break;
                case '6-10': matchesTeamSize = teamSize >= 6 && teamSize <= 10; break;
                case '10+': matchesTeamSize = teamSize > 10; break;
            }
        }
        
        // Connector filter
        let matchesConnector = !connectorFilter;
        if (connectorFilter && assignment.metrics_config) {
            matchesConnector = assignment.metrics_config[connectorFilter]?.enabled === true;
        }
        
        return matchesSearch && matchesStatus && matchesTeamSize && matchesConnector;
    });
    
    displaySearchResults(filtered);
    document.getElementById('visible-count').textContent = filtered.length;
}

function displaySearchResults(filteredAssignments) {
    const resultsContainer = document.getElementById('search-results');
    
    if (filteredAssignments.length === 0) {
        resultsContainer.innerHTML = '<div class="text-center text-gray-500 py-8" role="status" aria-live="polite">No assignments found matching your criteria.</div>';
        return;
    }
    
    let html = '';
    filteredAssignments.forEach((assignment, index) => {
        const enabledConnectors = [];
        if (assignment.metrics_config) {
            Object.keys(assignment.metrics_config).forEach(connector => {
                if (assignment.metrics_config[connector]?.enabled) {
                    enabledConnectors.push(connector);
                }
            });
        }
        
        html += `
            <div class="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 cursor-pointer focus:ring-2 focus:ring-blue-500 focus:outline-none"
                 onclick="hideSearchOverlay(); showTab('assignment-${assignment.id}')"
                 role="listitem"
                 tabindex="0"
                 aria-label="Assignment: ${assignment.name || assignment.id}. Click to view details."
                 onkeydown="if(event.key==='Enter'||event.key===' '){hideSearchOverlay(); showTab('assignment-${assignment.id}');event.preventDefault();}">
                <div class="flex justify-between items-start">
                    <div class="flex-1">
                        <h4 class="font-medium text-gray-900">${assignment.name || assignment.id}</h4>
                        <p class="text-sm text-gray-600 mt-1">${assignment.description || 'No description'}</p>
                        
                        <div class="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                            <span>Status: <span class="font-medium">${assignment.status || 'active'}</span></span>
                            <span>Team: ${assignment.team_size || 'N/A'}</span>
                            <span>Budget: $${(assignment.monthly_burn_rate || 0).toLocaleString()}/mo</span>
                        </div>
                        
                        ${enabledConnectors.length > 0 ? `
                            <div class="flex flex-wrap gap-1 mt-2">
                                ${enabledConnectors.map(conn => 
                                    `<span class="px-2 py-1 text-xs bg-blue-100 text-blue-600 rounded">${conn}</span>`
                                ).join('')}
                            </div>
                        ` : ''}
                    </div>
                    <div class="text-xs text-gray-400">
                        Click to view
                    </div>
                </div>
            </div>
        `;
    });
    
    resultsContainer.innerHTML = html;
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl+K or Cmd+K to open search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        if (document.getElementById('search-overlay').classList.contains('hidden')) {
            showSearchOverlay();
        } else {
            hideSearchOverlay();
        }
    }
    
    // Escape to close search and import dialog
    if (e.key === 'Escape') {
        hideSearchOverlay();
        hideImportDialog();
    }
});

// Phase 5C: Import/Export Functions
async function exportAssignments() {
    try {
        const workspaceId = currentWorkspace || 'default_workspace';
        const response = await fetch(`/api/assignments/export?workspace_id=${workspaceId}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const exportData = await response.json();
        
        // Create downloadable file
        const timestamp = new Date().toISOString().split('T')[0];
        const filename = `cto-dashboard-assignments-${timestamp}.json`;
        const blob = new Blob([JSON.stringify(exportData, null, 2)], {
            type: 'application/json'
        });
        
        // Download file
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        // Show success notification
        const totalRecords = exportData.records_exported || exportData.export_metadata?.records_exported || 0;
        showNotification(`Exported ${totalRecords} assignments to ${filename}`, 'success');
        
    } catch (error) {
        console.error('Export failed:', error);
        showNotification('Export failed. Please try again.', 'error');
    }
}

function showImportDialog() {
    if (!assertTrialWrite('imports')) return;
    document.getElementById('import-dialog').classList.remove('hidden');
    document.getElementById('import-file').focus();
}

function hideImportDialog() {
    document.getElementById('import-dialog').classList.add('hidden');
    document.getElementById('import-file').value = '';
    document.getElementById('import-mode').value = 'create_new';
    document.getElementById('import-message').classList.add('hidden');
}

function handleImportDrop(event) {
    event.preventDefault();
    const zone = document.getElementById('import-drop-zone');
    zone.classList.remove('border-blue-400', 'bg-blue-50');
    const fileInput = document.getElementById('import-file');
    if (event.dataTransfer.files.length) {
        fileInput.files = event.dataTransfer.files;
        updateImportDropLabel();
    }
}

function updateImportDropLabel() {
    const fileInput = document.getElementById('import-file');
    const label = document.getElementById('import-drop-label');
    if (fileInput.files.length) {
        label.textContent = 'Selected: ' + fileInput.files[0].name;
    } else {
        label.textContent = 'Drop file here or click to browse';
    }
}

async function performImport() {
    const fileInput = document.getElementById('import-file');
    const modeSelect = document.getElementById('import-mode');
    
    if (!fileInput.files.length) {
        showImportMessage('Please select a file to import.', 'error');
        return;
    }
    
    const file = fileInput.files[0];
    const importMode = modeSelect.value;
    const ext = (file.name.split('.').pop() || '').toLowerCase();
    const workspaceId = currentWorkspace;
    if (!workspaceId) {
        showImportMessage('Select your workspace before importing.', 'error');
        return;
    }
    
    try {
        showImportMessage('Importing...', 'info');
        let response, result;

        if (ext === 'json') {
            const fileContent = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = (e) => resolve(e.target.result);
                reader.onerror = reject;
                reader.readAsText(file);
            });
            const importData = JSON.parse(fileContent);
            if (!importData.assignments || !Array.isArray(importData.assignments)) {
                throw new Error('Invalid JSON — missing assignments array');
            }
            response = await authFetch(`/api/workspaces/${workspaceId}/import?mode=${importMode}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(importData)
            });
        } else if (ext === 'csv' || ext === 'xlsx' || ext === 'xlsm') {
            const formData = new FormData();
            formData.append('file', file);
            response = await authFetch(
                `/api/workspaces/${workspaceId}/import/file?mode=${importMode}`,
                { method: 'POST', body: formData }
            );
        } else {
            throw new Error('Unsupported file type. Use .json, .csv, or .xlsx');
        }

        result = await response.json();

        if (result.duplicate_file) {
            showImportMessage(result.warnings?.[0] || 'This file was already imported.', 'info');
            return;
        }

        if (result.success || response.status === 207) {
            let message = `Import complete: ${result.imported_assignments || 0} created`;
            if (result.updated_assignments) message += `, ${result.updated_assignments} updated`;
            if (result.rows_parsed) message += ` (${result.rows_parsed} rows parsed)`;
            if (result.skipped_assignments) message += `, ${result.skipped_assignments} skipped`;
            if (result.errors && result.errors.length) {
                message += `. ${result.errors.length} error(s) — see console.`;
                console.warn('Import errors:', result.errors);
            }
            if (result.warnings && result.warnings.length) {
                console.warn('Import warnings:', result.warnings);
            }
            showImportMessage(message, 'success');

            hideImportDialog();
            await loadDashboard(true);
            loadOverviewPanels();
        } else {
            const errText = (result.errors && result.errors.join('; ')) || result.error || 'Import failed';
            showImportMessage(errText, 'error');
        }
    } catch (error) {
        console.error('Import error:', error);
        showImportMessage('Import failed: ' + error.message, 'error');
    }
}

async function loadAttentionBriefing() {
    return loadOverviewPanels();
}

function showShareLinkDialog(url, expiresAt) {
    const dialog = document.getElementById('share-link-dialog');
    const input = document.getElementById('share-link-input');
    const expiryEl = document.getElementById('share-link-expiry');
    const statusEl = document.getElementById('share-link-copy-status');
    const copyBtn = document.getElementById('share-link-copy-btn');
    if (!dialog || !input) return;
    input.value = url;
    if (expiryEl) {
        expiryEl.textContent = expiresAt
            ? 'Expires ' + new Date(expiresAt).toLocaleDateString(undefined, { dateStyle: 'medium' })
            : 'No expiration date';
    }
    if (statusEl) {
        statusEl.textContent = '';
        statusEl.classList.add('hidden');
    }
    if (copyBtn) {
        copyBtn.textContent = 'Copy link';
        copyBtn.classList.remove('bg-gray-500');
        copyBtn.classList.add('bg-emerald-600', 'hover:bg-emerald-700');
    }
    dialog.classList.remove('hidden');
    input.focus();
    input.select();
}

function hideShareLinkDialog() {
    const dialog = document.getElementById('share-link-dialog');
    if (dialog) dialog.classList.add('hidden');
}

async function copyShareLink() {
    const input = document.getElementById('share-link-input');
    const statusEl = document.getElementById('share-link-copy-status');
    const copyBtn = document.getElementById('share-link-copy-btn');
    if (!input || !input.value) return;
    const url = input.value;
    let copied = false;
    if (navigator.clipboard && navigator.clipboard.writeText) {
        try {
            await navigator.clipboard.writeText(url);
            copied = true;
        } catch (e) { /* fallback below */ }
    }
    if (!copied) {
        input.focus();
        input.select();
        try {
            copied = document.execCommand('copy');
        } catch (e) { /* ignore */ }
    }
    if (statusEl) {
        statusEl.textContent = copied ? 'Link copied to clipboard.' : 'Select the link and copy manually (Cmd+C).';
        statusEl.classList.remove('hidden');
    }
    if (copyBtn && copied) {
        copyBtn.textContent = 'Copied!';
        copyBtn.classList.remove('bg-emerald-600', 'hover:bg-emerald-700');
        copyBtn.classList.add('bg-gray-500');
        setTimeout(function() {
            copyBtn.textContent = 'Copy link';
            copyBtn.classList.remove('bg-gray-500');
            copyBtn.classList.add('bg-emerald-600', 'hover:bg-emerald-700');
        }, 2000);
    }
}

async function shareBriefingReport() {
    if (!currentWorkspace) {
        alert('Select a workspace first.');
        return;
    }
    const btn = document.getElementById('briefing-share-btn');
    const originalText = btn ? btn.textContent : '';
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Creating...';
    }
    try {
        const resp = await authFetch(
            '/api/workspaces/' + encodeURIComponent(currentWorkspace) + '/attention/briefing/share',
            { method: 'POST', body: JSON.stringify({ expires_in_days: 30 }) }
        );
        const data = await resp.json();
        if (!resp.ok) {
            alert(data.message || data.error || 'Could not create share link.');
            return;
        }
        const url = data.share_url || (window.location.origin + (data.path || ''));
        showShareLinkDialog(url, data.expires_at);
    } catch (e) {
        console.error('Share link failed:', e);
        alert('Share link failed: ' + e.message);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = originalText || 'Share';
        }
    }
}

async function exportBriefingPdf() {
    if (!currentWorkspace) {
        alert('Select a workspace first.');
        return;
    }
    const btn = document.getElementById('briefing-export-pdf-btn');
    const originalText = btn ? btn.textContent : '';
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Exporting...';
    }
    try {
        const resp = await authFetch(
            '/api/workspaces/' + encodeURIComponent(currentWorkspace) + '/attention/briefing/export'
        );
        if (!resp.ok) {
            let message = 'PDF export failed.';
            try {
                const err = await resp.json();
                message = err.message || err.error || message;
            } catch (e) { /* ignore */ }
            alert(message);
            return;
        }
        const blob = await resp.blob();
        const disposition = resp.headers.get('Content-Disposition') || '';
        const match = disposition.match(/filename="?([^";]+)"?/i);
        const filename = match ? match[1] : ('CTO-Briefing-' + currentWorkspace + '.pdf');
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setTimeout(function() { URL.revokeObjectURL(url); }, 1000);
    } catch (e) {
        console.error('Briefing PDF export failed:', e);
        alert('PDF export failed: ' + e.message);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = originalText || 'Export PDF';
        }
    }
}

async function reloadBriefingPanelOnly() {
    if (!currentWorkspace) return;
    try {
        await loadOverviewPanels();
    } catch (e) {
        console.warn('Briefing panel reload failed:', e);
    }
}

async function refreshAttentionBriefing(fetchMetrics) {
    const root = document.getElementById('overview-panels-root');
    if (!currentWorkspace) return;
    try {
        const flagsResp = await fetch('/api/feature-flags');
        const flags = await flagsResp.json();
        const ctolensOn = flags && flags.ctolens_briefing;
        const attentionOn = flags && flags.attention_engine;
        if (!ctolensOn && !attentionOn) return;

        if (root) {
            root.innerHTML = '<div class="text-sm text-gray-500 p-4 bg-white rounded-lg shadow mb-4">' +
                (fetchMetrics ? 'Refreshing live metrics (this may take 90+ seconds)...' : 'Updating briefing (fast)...') +
                '</div>';
        }

        let resp;
        if (ctolensOn) {
            resp = await authFetch('/api/workspaces/' + encodeURIComponent(currentWorkspace) + '/ctolens/briefing/generate', {
                method: 'POST',
                headers: Object.assign({ 'Content-Type': 'application/json' }, getAuthHeaders()),
                body: JSON.stringify({ fetch_metrics: !!fetchMetrics })
            });
        } else {
            resp = await authFetch('/api/workspaces/' + encodeURIComponent(currentWorkspace) + '/attention/refresh', { method: 'POST' });
        }
        if (!resp.ok) {
            await reloadBriefingPanelOnly();
            return;
        }
        await loadOverviewPanels();
    } catch (e) {
        console.warn('Attention refresh failed:', e);
        await reloadBriefingPanelOnly();
    }
}

function showImportMessage(message, type) {
    const messageDiv = document.getElementById('import-message');
    messageDiv.textContent = message;
    messageDiv.className = `p-3 rounded ${type === 'error' ? 'bg-red-100 text-red-700' : 
        type === 'success' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'}`;
    messageDiv.classList.remove('hidden');
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transition-opacity duration-300 ${
        type === 'error' ? 'bg-red-500 text-white' : 
        type === 'success' ? 'bg-green-500 text-white' : 'bg-blue-500 text-white'
    }`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// Phase 5C: Assignment History Functions
