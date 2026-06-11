/* CTO Lens dashboard module: 10-bootstrap.js */

function closeToolbarMore() {
    const menu = document.getElementById('toolbar-more-menu');
    const toggle = document.getElementById('toolbar-more-toggle');
    if (menu) menu.classList.add('hidden');
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
}

function toggleToolbarMore(event) {
    if (event) event.stopPropagation();
    const menu = document.getElementById('toolbar-more-menu');
    const toggle = document.getElementById('toolbar-more-toggle');
    if (!menu) return;
    const willOpen = menu.classList.contains('hidden');
    menu.classList.toggle('hidden');
    if (toggle) toggle.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
}

document.addEventListener('click', function() {
    closeToolbarMore();
});

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
