/* CTO Lens dashboard module: 02-analytics.js */
// ===== Product analytics (client beacon) =====
let _analyticsEnabled = null;

async function isProductAnalyticsEnabled() {
    if (_analyticsEnabled !== null) {
        return _analyticsEnabled;
    }
    try {
        const resp = await fetch('/api/feature-flags');
        const flags = await resp.json();
        _analyticsEnabled = !!(flags && flags.product_analytics);
    } catch (e) {
        _analyticsEnabled = false;
    }
    return _analyticsEnabled;
}

function trackAnalytics(eventName, metadata) {
    if (!eventName) return;
    isProductAnalyticsEnabled().then(function(enabled) {
        if (!enabled || !isAuthenticated) return;
        authFetch('/api/analytics/events', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                event_name: eventName,
                metadata: metadata || {},
            }),
        }).catch(function() {});
    });
}

function trackFeatureUsed(feature, extra) {
    const meta = Object.assign({ feature: feature }, extra || {});
    trackAnalytics('feature_used', meta);
}

function trackPageViewOnce(key, path) {
    const storageKey = 'analytics_pv_' + key;
    if (sessionStorage.getItem(storageKey)) return;
    sessionStorage.setItem(storageKey, '1');
    trackAnalytics('page_view', { path: path || window.location.pathname });
}

function trackInsightViewed(panel) {
    const storageKey = 'analytics_insight_' + (panel || 'briefing');
    if (sessionStorage.getItem(storageKey)) return;
    sessionStorage.setItem(storageKey, '1');
    trackAnalytics('insight_viewed', { panel: panel || 'briefing' });
}

// Retry utility with exponential backoff for handling eventual consistency
