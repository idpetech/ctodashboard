/* CTO Lens dashboard module: 08-history-backup.js */
async function showAssignmentHistory() {
    const assignmentId = document.getElementById('assignment-id').value;
    if (!assignmentId) {
        showNotification('No assignment selected', 'error');
        return;
    }
    
    try {
        const response = await fetch(`/api/assignments/${assignmentId}/history`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        displayAssignmentHistory(data.history, assignmentId);
        
    } catch (error) {
        console.error('Failed to load assignment history:', error);
        showNotification('Failed to load assignment history', 'error');
    }
}

function displayAssignmentHistory(history, assignmentId) {
    if (history.length === 0) {
        alert(`No change history found for assignment: ${assignmentId}`);
        return;
    }
    
    let historyText = `Assignment History: ${assignmentId}\n`;
    historyText += `Total Changes: ${history.length}\n\n`;
    
    history.slice(0, 10).forEach((entry, index) => {
        const date = new Date(entry.timestamp).toLocaleString();
        historyText += `${index + 1}. ${entry.action.toUpperCase()} - ${date}\n`;
        
        if (entry.changes && entry.changes.length > 0) {
            entry.changes.forEach(change => {
                historyText += `   • ${change.field}: ${change.old_value} → ${change.new_value}\n`;
            });
        }
        historyText += '\n';
    });
    
    if (history.length > 10) {
        historyText += `... and ${history.length - 10} more changes`;
    }
    
    // Show in alert for now (could be enhanced to use a proper modal)
    alert(historyText);
}

// Phase 5C: Backup/Restore Information
function showBackupInfo() {
    const backupInfo = `
CTO Lens Backup & Restore

📋 BACKUP OPTIONS:
The system includes a CLI tool for complete data backup and restore.

🔧 COMMAND LINE USAGE:

Create Backup:
• python backup_restore.py backup
• python backup_restore.py backup --name "my_backup"
• python backup_restore.py backup --include-services

List Backups:
• python backup_restore.py list

Restore Backup:
• python backup_restore.py restore backup_name.zip
• python backup_restore.py restore backup_name.zip --dry-run

Delete Backup:
• python backup_restore.py delete backup_name.zip

💾 WHAT'S INCLUDED:
• All assignment configurations
• Workspace settings  
• User profiles and credentials
• Assignment change history (audit logs)
• Service configurations (optional)

📁 BACKUP LOCATION:
Backups are stored in: ./backups/

⚠️ IMPORTANT:
• Stop the application before restoring
• Backups exclude sensitive credential data
• Test restores with --dry-run first

🚀 For automated backups, consider setting up a cron job to run the backup command regularly.
    `.trim();
    
    alert(backupInfo);
}

// Phase 5C: Performance Optimization with Caching
class CacheManager {
    constructor() {
        this.prefix = 'ctodash_cache_';
        this.defaultTTL = 5 * 60 * 1000; // 5 minutes
    }
    
    set(key, data, ttl = this.defaultTTL) {
        const item = {
            data: data,
            timestamp: Date.now(),
            ttl: ttl
        };
        try {
            localStorage.setItem(this.prefix + key, JSON.stringify(item));
        } catch (e) {
            console.warn('Cache storage failed:', e);
        }
    }
    
    get(key) {
        try {
            const itemStr = localStorage.getItem(this.prefix + key);
            if (!itemStr) return null;
            
            const item = JSON.parse(itemStr);
            if (Date.now() - item.timestamp > item.ttl) {
                this.delete(key);
                return null;
            }
            
            return item.data;
        } catch (e) {
            console.warn('Cache retrieval failed:', e);
            return null;
        }
    }
    
    delete(key) {
        localStorage.removeItem(this.prefix + key);
    }
    
    clear() {
        Object.keys(localStorage).forEach(key => {
            if (key.startsWith(this.prefix)) {
                localStorage.removeItem(key);
            }
        });
    }
    
    invalidateAssignments(workspaceId) {
        // Clear workspace-scoped keys (loadDashboard uses assignments_<workspaceId>)
        if (workspaceId) {
            this.delete('assignments_' + workspaceId);
        }
        // Clear any legacy or other workspace assignment caches
        try {
            Object.keys(localStorage).forEach(function(storageKey) {
                if (storageKey.startsWith('ctodash_cache_assignments')) {
                    localStorage.removeItem(storageKey);
                }
            });
        } catch (e) {
            console.warn('Cache sweep failed:', e);
        }
        this.delete('assignments');
        this.delete('assignments_overview');
    }
}

const cache = new CacheManager();

// Phase 5C: Background Monitoring Layer
