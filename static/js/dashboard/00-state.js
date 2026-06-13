/* CTO Lens dashboard module: 00-state.js */
// Authentication State Management
let currentUser = null;
let authToken = null;
let isAuthenticated = false;
let assignments = []; // Store assignments globally for management functions
let trialState = null;

// Act 4 deployment connectors (Railway, Vercel, Azure) — gated by server feature flags
let act4ConnectorFlags = {
    railway_connector: false,
    vercel_connector: false,
    azure_connector: false,
};

const ALL_CONNECTOR_TYPES = ['github', 'jira', 'aws', 'openai', 'railway', 'vercel', 'azure'];

const CONNECTOR_CATALOG = [
    { id: 'github', label: 'GitHub', desc: 'Repository metrics', bg: 'bg-gray-800', icon: 'GH' },
    { id: 'jira', label: 'Jira', desc: 'Issue tracking', bg: 'bg-blue-600', icon: 'JI' },
    { id: 'aws', label: 'AWS', desc: 'Cloud costs', bg: 'bg-orange-500', icon: 'AWS' },
    { id: 'openai', label: 'OpenAI', desc: 'AI insights', bg: 'bg-green-600', icon: 'AI' },
    { id: 'railway', label: 'Railway', desc: 'Deployments', bg: 'bg-purple-700', icon: 'RW', act4: 'railway_connector' },
    { id: 'vercel', label: 'Vercel', desc: 'Deployments', bg: 'bg-black', icon: 'VC', act4: 'vercel_connector' },
    { id: 'azure', label: 'Azure', desc: 'Cloud resources', bg: 'bg-sky-600', icon: 'AZ', act4: 'azure_connector' },
];

function isAct4ConnectorCatalogEntry(entry) {
    return !!entry.act4;
}

function isAct4ConnectorFlagEnabled(flagKey) {
    return !!act4ConnectorFlags[flagKey];
}

function getConnectorsForPicker() {
    return CONNECTOR_CATALOG.filter(function(entry) {
        if (!entry.act4) return true;
        return isAct4ConnectorFlagEnabled(entry.act4);
    });
}

function getConnectorsForAssignmentDisplay(metricsConfig) {
    return ALL_CONNECTOR_TYPES.filter(function(type) {
        const config = metricsConfig && metricsConfig[type];
        return config && config.enabled;
    });
}

async function loadAct4ConnectorFlags() {
    try {
        const response = await fetch('/api/feature-flags', { credentials: 'same-origin' });
        if (response.ok) {
            const flags = await response.json();
            act4ConnectorFlags = {
                railway_connector: !!flags.railway_connector,
                vercel_connector: !!flags.vercel_connector,
                azure_connector: !!flags.azure_connector,
            };
        }
    } catch (error) {
        console.warn('Act 4 connector flags unavailable:', error);
    }
    applyAct4ConnectorUiVisibility();
    return act4ConnectorFlags;
}

function applyAct4ConnectorUiVisibility() {
    const toggles = [
        ['railway-card', 'railway_connector'],
        ['vercel-card', 'vercel_connector'],
        ['azure-card', 'azure_connector'],
        ['enable_railway_row', 'railway_connector'],
        ['enable_vercel_row', 'vercel_connector'],
        ['enable_azure_row', 'azure_connector'],
        ['dashboard_enable_railway_row', 'railway_connector'],
        ['dashboard_enable_vercel_row', 'vercel_connector'],
        ['dashboard_enable_azure_row', 'azure_connector'],
    ];
    toggles.forEach(function(pair) {
        const el = document.getElementById(pair[0]);
        if (el) el.classList.toggle('hidden', !act4ConnectorFlags[pair[1]]);
    });
}
