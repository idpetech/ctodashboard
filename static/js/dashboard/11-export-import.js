/* CTO Lens dashboard module: 11-export-import.js */
// Export functionality - Simple and focused
function showExportMenu() {
document.getElementById('export-modal').classList.remove('hidden');
}

function hideExportModal() {
document.getElementById('export-modal').classList.add('hidden');
clearExportMessages();
}

function showExportMessage(message, type) {
const messageDiv = document.getElementById('export-message');
messageDiv.className = `mb-4 p-3 rounded ${type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`;
messageDiv.textContent = message;
messageDiv.classList.remove('hidden');
}

function clearExportMessages() {
document.getElementById('export-message').classList.add('hidden');
}

async function executeExport() {
const exportType = document.getElementById('export-type').value;
const format = document.getElementById('export-format').value;
const exportBtn = document.getElementById('export-btn');

// Get current workspace
const workspaceSelect = document.getElementById('workspace-select');
const workspaceId = workspaceSelect.value;

if (!workspaceId) {
showExportMessage('Please select a workspace first', 'error');
return;
}

try {
// Show loading state
exportBtn.disabled = true;
exportBtn.innerHTML = '⏳ Exporting...';
clearExportMessages();

let url;
if (exportType === 'workspace') {
    url = `/api/export/workspace/${workspaceId}?format=${format}`;
} else {
    // For assignment export, we need the current assignment
    if (!selectedAssignmentId) {
        showExportMessage('Please select an assignment first', 'error');
        return;
    }
    url = `/api/export/assignment/${workspaceId}/${selectedAssignmentId}?format=${format}`;
}

const response = await fetch(url);
const result = await response.json();

if (result.success) {
    // Success! Show download link
    showExportMessage(`Export successful! File: ${result.filename} (${result.size_bytes} bytes)`, 'success');
    
    // Auto-download the file
    window.open(`/api/export/download/${result.filename}`, '_blank');
    
    // Close modal after a delay
    setTimeout(() => {
        hideExportModal();
    }, 2000);
} else {
    showExportMessage(`Export failed: ${result.error}`, 'error');
}

} catch (error) {
console.error('Export error:', error);
showExportMessage(`Export failed: ${error.message}`, 'error');
} finally {
// Restore button state
exportBtn.disabled = false;
exportBtn.innerHTML = '📤 Export';
}
}

// ============================================================================
// Import JavaScript Functions - Phase 2 KISS Implementation
// ============================================================================

function showImportMenu() {
document.getElementById('import-modal').classList.remove('hidden');
loadImportTemplates();
setupImportSourceToggle();
}

function hideImportModal() {
document.getElementById('import-modal').classList.add('hidden');
clearImportMessages();
resetImportForm();
}

function showImportMessage(message, type) {
const messageDiv = document.getElementById('import-message');
messageDiv.className = `mb-4 p-3 rounded ${type === 'success' ? 'bg-green-100 text-green-700' : type === 'warning' ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`;
messageDiv.textContent = message;
messageDiv.classList.remove('hidden');
}

function clearImportMessages() {
document.getElementById('import-message').classList.add('hidden');
}

function resetImportForm() {
document.getElementById('import-file').value = '';
document.querySelector('input[name="import-source"][value="file"]').checked = true;
document.getElementById('import-mode').value = 'create_new';
document.getElementById('import-btn').disabled = true;
setupImportSourceToggle();
}

function setupImportSourceToggle() {
const fileSection = document.getElementById('file-import-section');
const templateSection = document.getElementById('template-import-section');
const radios = document.querySelectorAll('input[name="import-source"]');

radios.forEach(radio => {
radio.addEventListener('change', function() {
    if (this.value === 'file') {
        fileSection.classList.remove('hidden');
        templateSection.classList.add('hidden');
    } else {
        fileSection.classList.add('hidden');
        templateSection.classList.remove('hidden');
        checkImportReadiness();
    }
});
});
}

async function loadImportTemplates() {
try {
const response = await fetch('/api/import/templates');
const result = await response.json();

const select = document.getElementById('import-template');
select.innerHTML = '<option value="">Select a template...</option>';

if (result.templates) {
    result.templates.forEach(template => {
        const option = document.createElement('option');
        option.value = template.id;
        option.textContent = `${template.name} - ${template.description}`;
        select.appendChild(option);
    });
    
    select.addEventListener('change', checkImportReadiness);
}

} catch (error) {
console.error('Failed to load templates:', error);
}
}

function handleFileSelect() {
const fileInput = document.getElementById('import-file');
const file = fileInput.files[0];

if (file) {
// Basic file validation
const validTypes = ['application/json', 'text/csv'];
if (!validTypes.includes(file.type) && !file.name.endsWith('.json') && !file.name.endsWith('.csv')) {
    showImportMessage('Please select a JSON or CSV file', 'error');
    fileInput.value = '';
    document.getElementById('import-btn').disabled = true;
    return;
}

// Size check (max 10MB)
if (file.size > 10 * 1024 * 1024) {
    showImportMessage('File too large. Maximum size is 10MB', 'error');
    fileInput.value = '';
    document.getElementById('import-btn').disabled = true;
    return;
}

clearImportMessages();
showImportMessage(`File selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`, 'success');
document.getElementById('import-btn').disabled = false;
} else {
document.getElementById('import-btn').disabled = true;
}
}

function checkImportReadiness() {
const importSource = document.querySelector('input[name="import-source"]:checked').value;
const importBtn = document.getElementById('import-btn');

if (importSource === 'file') {
const fileInput = document.getElementById('import-file');
importBtn.disabled = !fileInput.files[0];
} else {
const templateSelect = document.getElementById('import-template');
importBtn.disabled = !templateSelect.value;
}
}

async function executeImport() {
const importSource = document.querySelector('input[name="import-source"]:checked').value;
const importMode = document.getElementById('import-mode').value;
const importBtn = document.getElementById('import-btn');
const workspaceSelect = document.getElementById('workspace-select');
const workspaceId = workspaceSelect.value;

if (!workspaceId) {
showImportMessage('Please select a workspace first', 'error');
return;
}

try {
importBtn.disabled = true;
importBtn.innerHTML = '⏳ Importing...';
clearImportMessages();

let importData;

if (importSource === 'file') {
    // Handle file import
    const fileInput = document.getElementById('import-file');
    const file = fileInput.files[0];
    
    if (!file) {
        showImportMessage('Please select a file', 'error');
        return;
    }
    
    importData = await readFileAsText(file);
    
    // Parse JSON if needed
    if (file.type === 'application/json' || file.name.endsWith('.json')) {
        try {
            importData = JSON.parse(importData);
        } catch (e) {
            showImportMessage('Invalid JSON file format', 'error');
            return;
        }
    } else {
        showImportMessage('CSV import not yet supported. Please use JSON format.', 'error');
        return;
    }
    
} else {
    // Handle template import
    const templateId = document.getElementById('import-template').value;
    if (!templateId) {
        showImportMessage('Please select a template', 'error');
        return;
    }
    
    // Get template data
    const templatesResponse = await fetch('/api/import/templates');
    const templatesResult = await templatesResponse.json();
    const template = templatesResult.templates.find(t => t.id === templateId);
    
    if (!template) {
        showImportMessage('Template not found', 'error');
        return;
    }
    
    // Create import data from template
    importData = {
        export_metadata: {
            export_version: '1.0',
            workspace_id: workspaceId,
            export_timestamp: new Date().toISOString(),
            source: 'template'
        },
        workspace_info: {},
        assignments: [{
            assignment_id: `template_${templateId}_${Date.now()}`,
            ...template.template
        }]
    };
}

// Send import request
const response = await fetch(`/api/workspaces/${workspaceId}/import?mode=${importMode}`, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(importData)
});

const result = await response.json();

if (response.ok || response.status === 207) { // 207 = partial success
    let message = `Import completed! `;
    if (result.imported_assignments > 0) message += `Created: ${result.imported_assignments} `;
    if (result.updated_assignments > 0) message += `Updated: ${result.updated_assignments} `;
    if (result.skipped_assignments > 0) message += `Skipped: ${result.skipped_assignments}`;
    
    showImportMessage(message, result.success ? 'success' : 'warning');
    
    // Show details if any
    if (result.details && result.details.length > 0) {
        console.log('Import details:', result.details);
    }
    
    // Show errors if any
    if (result.errors && result.errors.length > 0) {
        console.log('Import errors:', result.errors);
    }
    
    // Refresh the page after success to show new assignments
    if (result.success) {
        setTimeout(() => {
            hideImportModal();
            window.location.reload();
        }, 2000);
    }
    
} else {
    showImportMessage(`Import failed: ${result.error || 'Unknown error'}`, 'error');
    if (result.errors) {
        console.error('Import errors:', result.errors);
    }
}

} catch (error) {
console.error('Import error:', error);
showImportMessage(`Import failed: ${error.message}`, 'error');
} finally {
importBtn.disabled = false;
importBtn.innerHTML = '📥 Import';
}
}

function readFileAsText(file) {
return new Promise((resolve, reject) => {
const reader = new FileReader();
reader.onload = (e) => resolve(e.target.result);
reader.onerror = (e) => reject(new Error('Failed to read file'));
reader.readAsText(file);
});
}
