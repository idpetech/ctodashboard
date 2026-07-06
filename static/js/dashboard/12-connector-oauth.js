/** Connector OAuth UI + per-assignment credential loading (GitHub App, Jira 3LO). */

let connectorOAuthFlags = {
    github_oauth_ui: false,
    jira_oauth_ui: false,
    github_oauth_available: false,
    jira_oauth_available: false,
    disable_manual_tokens: false,
};

const CONNECTOR_AUTH_TAB_ACTIVE =
    'rounded-md px-3 py-2.5 text-left bg-white shadow-sm ring-1 ring-blue-200';
const CONNECTOR_AUTH_TAB_INACTIVE =
    'rounded-md px-3 py-2.5 text-left text-gray-600 hover:text-gray-800 hover:bg-gray-100';

function connectorWorkspaceId() {
    return typeof currentWorkspace !== 'undefined' && currentWorkspace
        ? currentWorkspace
        : typeof window.currentWorkspace !== 'undefined'
          ? window.currentWorkspace
          : null;
}

function connectorAuthFetch(url, options) {
    if (typeof authFetch === 'function') {
        return authFetch(url, options);
    }
    const headers = {
        'Content-Type': 'application/json',
        ...(typeof wsAuthHeaders === 'function' ? wsAuthHeaders() : {}),
        ...(options && options.headers ? options.headers : {}),
    };
    return fetch(url, { credentials: 'same-origin', ...options, headers });
}

function connectorOAuthUiEnabled(connectorType) {
    return connectorType === 'github'
        ? connectorOAuthFlags.github_oauth_ui
        : connectorOAuthFlags.jira_oauth_ui;
}

function connectorOAuthAvailable(connectorType) {
    return connectorType === 'github'
        ? connectorOAuthFlags.github_oauth_available
        : connectorOAuthFlags.jira_oauth_available;
}

function applyConnectorAuthTabStyles(connectorType, method) {
    const oauthBtn = document.getElementById(`${connectorType}-auth-tab-btn-oauth`);
    const legacyBtn = document.getElementById(`${connectorType}-auth-tab-btn-legacy`);
    const isOAuth = method === 'oauth';

    if (oauthBtn) {
        oauthBtn.className = isOAuth ? CONNECTOR_AUTH_TAB_ACTIVE : CONNECTOR_AUTH_TAB_INACTIVE;
        oauthBtn.setAttribute('aria-selected', String(isOAuth));
    }
    if (legacyBtn) {
        legacyBtn.className = isOAuth ? CONNECTOR_AUTH_TAB_INACTIVE : CONNECTOR_AUTH_TAB_ACTIVE;
        legacyBtn.setAttribute('aria-selected', String(!isOAuth));
    }

    const oauthPane = document.getElementById(`${connectorType}-oauth-tab`);
    const legacyPane = document.getElementById(`${connectorType}-legacy-tab`);
    if (oauthPane) oauthPane.classList.toggle('hidden', !isOAuth);
    if (legacyPane) legacyPane.classList.toggle('hidden', isOAuth);
}

function setConnectorAuthMethod(connectorType, method) {
    if (connectorType !== 'github' && connectorType !== 'jira') return;

    const oauthUi = connectorOAuthUiEnabled(connectorType);
    let resolved = method === 'legacy' ? 'legacy' : 'oauth';

    if (!oauthUi) {
        resolved = 'legacy';
    }
    if (connectorOAuthFlags.disable_manual_tokens && resolved === 'legacy') {
        resolved = 'oauth';
    }

    applyConnectorAuthTabStyles(connectorType, resolved);
}

function inferConnectorAuthTab(connectorType, credentials) {
    const oauthUi = connectorOAuthUiEnabled(connectorType);
    if (!oauthUi) return 'legacy';

    if (!credentials || Object.keys(credentials).length === 0) {
        return 'oauth';
    }

    const method = (credentials.auth_method || '').toLowerCase();
    const secrets = credentials._configured_secrets || [];

    if (connectorType === 'github') {
        if (method === 'github_app' || credentials.github_installation_id) return 'oauth';
        if (method === 'manual' || secrets.includes('github_token')) return 'legacy';
    }
    if (connectorType === 'jira') {
        if (method === 'jira_oauth' || credentials.jira_cloud_id) return 'oauth';
        if (method === 'manual' || secrets.includes('jira_token')) return 'legacy';
    }

    return 'oauth';
}

function setConnectorAuthMethodFromCredentials(connectorType, credentials) {
    setConnectorAuthMethod(connectorType, inferConnectorAuthTab(connectorType, credentials));
}

function defaultConnectorAuthTab(connectorType) {
    if (connectorType !== 'github' && connectorType !== 'jira') return;
    setConnectorAuthMethod(connectorType, connectorOAuthUiEnabled(connectorType) ? 'oauth' : 'legacy');
}

async function loadConnectorOAuthUi(activeConnectorType) {
    try {
        const response = await connectorAuthFetch('/api/feature-flags');
        if (!response.ok) return;
        const flags = await response.json();
        connectorOAuthFlags = {
            github_oauth_ui: !!(flags.github_oauth_ui || flags.github_oauth_available),
            jira_oauth_ui: !!(flags.jira_oauth_ui || flags.jira_oauth_available),
            github_oauth_available: !!flags.github_oauth_available,
            jira_oauth_available: !!flags.jira_oauth_available,
            disable_manual_tokens: !!flags.disable_manual_tokens,
        };

        ['github', 'jira'].forEach((connectorType) => {
            const tabs = document.getElementById(`${connectorType}-auth-tabs`);
            const oauthUi = connectorOAuthUiEnabled(connectorType);
            if (tabs) tabs.classList.toggle('hidden', !oauthUi);

            const legacyBtn = document.getElementById(`${connectorType}-auth-tab-btn-legacy`);
            if (legacyBtn) {
                const hideLegacy = oauthUi && connectorOAuthFlags.disable_manual_tokens;
                legacyBtn.classList.toggle('hidden', hideLegacy);
                legacyBtn.disabled = hideLegacy;
            }

            const hint = document.getElementById(`${connectorType}-oauth-hint`);
            if (hint) {
                const showHint = oauthUi && !connectorOAuthAvailable(connectorType);
                hint.classList.toggle('hidden', !showHint);
                if (showHint) {
                    hint.textContent =
                        connectorType === 'github'
                            ? 'Connect is disabled until GITHUB_APP_ID and GITHUB_APP_SLUG are set on the server.'
                            : 'Connect is disabled until JIRA_OAUTH_CLIENT_ID is set on the server.';
                }
            }

            const connectBtn = document.getElementById(`${connectorType}-oauth-connect-btn`);
            if (connectBtn) connectBtn.disabled = !connectorOAuthAvailable(connectorType);
        });

        const targets = activeConnectorType ? [activeConnectorType] : ['github', 'jira'];
        targets.forEach((connectorType) => {
            if (connectorType !== 'github' && connectorType !== 'jira') return;
            const form = document.getElementById(`${connectorType}-form`);
            if (!activeConnectorType || form?.classList.contains('active')) {
                defaultConnectorAuthTab(connectorType);
            }
        });
    } catch (error) {
        console.warn('Connector OAuth flags unavailable:', error);
    }
}

function clearConnectorFormFields(connectorType) {
    const clearIds = {
        github: ['github_token', 'github_org', 'github_repos'],
        jira: ['jira_url', 'jira_email', 'jira_token', 'jira_projects'],
    };
    (clearIds[connectorType] || []).forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    if (connectorType === 'github' || connectorType === 'jira') {
        defaultConnectorAuthTab(connectorType);
    }
}

function populateConnectorFormFromCredentials(connectorType, credentials) {
    if (!credentials) {
        if (connectorType === 'github' || connectorType === 'jira') {
            defaultConnectorAuthTab(connectorType);
        }
        return;
    }
    const set = (id, value) => {
        const el = document.getElementById(id);
        if (el && value != null && value !== '') el.value = value;
    };
    if (connectorType === 'github') {
        set('github_org', credentials.github_org || credentials.org);
        set('github_repos', credentials.github_repos);
        setConnectorAuthMethodFromCredentials('github', credentials);
    } else if (connectorType === 'jira') {
        set('jira_url', credentials.jira_url);
        set('jira_email', credentials.jira_email);
        set('jira_projects', credentials.jira_projects);
        setConnectorAuthMethodFromCredentials('jira', credentials);
    }
    const secrets = credentials._configured_secrets || [];
    if (secrets.length && typeof showMessage === 'function') {
        showMessage('ℹ️ Saved credentials on file — re-enter secrets only to change them', 'success');
    }
}

async function loadConnectorCredentialsForAssignment(connectorType) {
    const workspaceId = connectorWorkspaceId();
    const assignmentId =
        document.getElementById(`${connectorType}_assignment`)?.value ||
        (typeof selectedConnectorAssignmentId !== 'undefined' ? selectedConnectorAssignmentId : null) ||
        (typeof selectedAssignmentId !== 'undefined' ? selectedAssignmentId : null);

    clearConnectorFormFields(connectorType);
    if (!assignmentId || !workspaceId) return;

    try {
        const response = await connectorAuthFetch(
            `/api/workspaces/${workspaceId}/assignments/${assignmentId}/credentials/${connectorType}`
        );
        if (!response.ok) return;
        const data = await response.json();
        populateConnectorFormFromCredentials(connectorType, data.credentials || {});
    } catch (error) {
        console.warn('Could not load assignment credentials:', error);
    }
}

function onConnectorAssignmentChanged(connectorType) {
    if (typeof clearMessages === 'function') clearMessages();
    loadConnectorCredentialsForAssignment(connectorType);
    if (connectorType === 'aws' && typeof loadAwsOnboardingHints === 'function') {
        loadAwsOnboardingHints().catch(() => {});
    }
}

async function startConnectorOAuth(connectorType) {
    const workspaceId = connectorWorkspaceId();
    const assignmentId = document.getElementById(`${connectorType}_assignment`)?.value;
    if (!assignmentId) {
        if (typeof showMessage === 'function') showMessage('Select an assignment before connecting', 'error');
        return;
    }
    if (!workspaceId) {
        if (typeof showMessage === 'function') showMessage('No workspace selected', 'error');
        return;
    }

    const startUrl =
        `/api/workspaces/${workspaceId}/oauth/${connectorType}/start` +
        `?assignment_id=${encodeURIComponent(assignmentId)}&redirect=false`;

    try {
        if (typeof showMessage === 'function') showMessage('Starting secure connection...', 'info');
        const response = await connectorAuthFetch(startUrl);
        const data = await response.json().catch(() => ({}));
        const redirectUrl = data.install_url || data.authorize_url;
        if (!response.ok || !redirectUrl) {
            const message = data.error || data.message || `Could not start ${connectorType} OAuth (${response.status})`;
            if (typeof showMessage === 'function') showMessage(`❌ ${message}`, 'error');
            return;
        }
        window.location.href = redirectUrl;
    } catch (error) {
        if (typeof showMessage === 'function') showMessage(`❌ Connection failed: ${error.message}`, 'error');
    }
}

async function disconnectConnectorOAuth(connectorType) {
    const workspaceId = connectorWorkspaceId();
    const assignmentId = document.getElementById(`${connectorType}_assignment`)?.value;
    if (!assignmentId) {
        if (typeof showMessage === 'function') showMessage('Select an assignment before disconnecting', 'error');
        return;
    }
    if (!confirm(`Disconnect ${connectorType} for this assignment?`)) return;

    try {
        const response = await connectorAuthFetch(
            `/api/workspaces/${workspaceId}/credentials/${connectorType}/oauth`,
            {
                method: 'DELETE',
                body: JSON.stringify({ assignment_id: assignmentId }),
            }
        );
        const result = await response.json();
        if (response.ok && result.success) {
            if (typeof showMessage === 'function') showMessage(`✅ ${connectorType} disconnected`, 'success');
            if (typeof loadCredentialStatus === 'function') loadCredentialStatus();
            loadConnectorCredentialsForAssignment(connectorType);
        } else if (typeof showMessage === 'function') {
            showMessage(`❌ ${result.error || 'Disconnect failed'}`, 'error');
        }
    } catch (error) {
        if (typeof showMessage === 'function') showMessage(`❌ Disconnect failed: ${error.message}`, 'error');
    }
}

function handleOAuthReturnBanner() {
    const params = new URLSearchParams(window.location.search);
    const connector = params.get('oauth');
    const status = params.get('oauth_status');
    const message = params.get('oauth_message');
    const assignmentId = params.get('assignment_id');
    const workspace = params.get('workspace');
    if (!connector || !status) return;

    if (workspace) {
        if (typeof currentWorkspace !== 'undefined') currentWorkspace = workspace;
        window.currentWorkspace = workspace;
    }
    if (assignmentId) {
        if (typeof selectedConnectorAssignmentId !== 'undefined') {
            selectedConnectorAssignmentId = assignmentId;
        }
        if (typeof selectedAssignmentId !== 'undefined') {
            selectedAssignmentId = assignmentId;
        }
    }

    const openModal = () => {
        if (typeof configureConnector === 'function') {
            configureConnector(connector);
        }
    };

    const text = message || `${connector} OAuth ${status}`;
    if (status === 'success') {
        if (typeof showMessage === 'function') showMessage(`✅ ${text}`, 'success');
    } else if (status === 'warning') {
        if (typeof showMessage === 'function') showMessage(`⚠️ ${text}`, 'success');
    } else if (typeof showMessage === 'function') {
        showMessage(`❌ ${text}`, 'error');
    }

    if (typeof isAuthenticated !== 'undefined' && isAuthenticated) {
        openModal();
    } else {
        setTimeout(openModal, 1500);
    }

    params.delete('oauth');
    params.delete('oauth_status');
    params.delete('oauth_message');
    params.delete('assignment_id');
    params.delete('workspace');
    const next = params.toString();
    const cleanUrl = window.location.pathname + (next ? `?${next}` : '');
    window.history.replaceState({}, '', cleanUrl);
}

