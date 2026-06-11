/* CTO Lens dashboard module: 10-bootstrap.js */
// Initialize authentication when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeAuth();
    
    // Phase 5C: Start background monitoring and real-time updates after successful auth
    setTimeout(function() {
        if (isAuthenticated) {
            monitor.start();
            updater.start(); // Start real-time updates
        }
    }, 2000); // Give auth time to complete
});
