/* CTO Lens dashboard module: 01-auth-billing.js */
function formatTrialDate(iso) {
    if (!iso) return '—';
    try {
        return new Date(iso).toLocaleDateString(undefined, { dateStyle: 'medium' });
    } catch (e) {
        return iso;
    }
}

function applyTrialUI(trial) {
    trialState = trial;
    const banner = document.getElementById('trial-banner');
    if (banner) {
        if (trial && trial.banner && trial.banner.message) {
            banner.textContent = trial.banner.message;
            banner.classList.remove('hidden', 'bg-amber-50', 'text-amber-900', 'border', 'border-amber-200', 'bg-red-50', 'text-red-800', 'border-red-200');
            if (trial.banner.level === 'error') {
                banner.classList.add('bg-red-50', 'text-red-800', 'border', 'border-red-200');
            } else {
                banner.classList.add('bg-amber-50', 'text-amber-900', 'border', 'border-amber-200');
            }
        } else {
            banner.classList.add('hidden');
            banner.textContent = '';
        }
    }

    const readOnly = trial && trial.can_write === false;
    const importBtn = document.getElementById('import-assignments-btn');
    if (importBtn) {
        importBtn.disabled = readOnly;
        importBtn.classList.toggle('opacity-50', readOnly);
        importBtn.classList.toggle('cursor-not-allowed', readOnly);
        importBtn.title = readOnly ? 'Trial expired — upgrade to import' : '';
    }
    const addTab = document.getElementById('tab-add-new');
    if (addTab) {
        addTab.classList.toggle('pointer-events-none', readOnly);
        addTab.classList.toggle('opacity-50', readOnly);
    }

    const trialInfo = document.getElementById('profile-trial-info');
    if (trialInfo && trial) {
        const onPaidPlan = trial.billing_status === 'active' || trial.trial_status === 'paid';
        trialInfo.classList.toggle('hidden', onPaidPlan);
        if (!onPaidPlan) {
            document.getElementById('profile-trial-status').textContent = trial.trial_status || '—';
            document.getElementById('profile-trial-start').textContent = formatTrialDate(trial.trial_start_date);
            document.getElementById('profile-trial-end').textContent = formatTrialDate(trial.trial_end_date);
            document.getElementById('profile-trial-days').textContent =
                trial.days_remaining != null ? trial.days_remaining : '—';
        }
    }

    applyBillingUI(trial);
}

function formatBillingStatus(status) {
    const labels = {
        trial: 'Trial',
        active: 'Active',
        canceled: 'Canceled',
        past_due: 'Past due',
    };
    return labels[status] || status || '—';
}

function applyBillingUI(state) {
    const section = document.getElementById('profile-billing-section');
    if (!section || !state) return;

    const billingEnabled = state.enabled === true;
    section.classList.toggle('hidden', !billingEnabled);
    if (!billingEnabled) return;

    document.getElementById('profile-billing-plan').textContent = state.plan_name || 'Trial';
    document.getElementById('profile-billing-status').textContent = formatBillingStatus(state.billing_status);
    document.getElementById('profile-billing-renewal').textContent =
        state.renewal_date ? formatTrialDate(state.renewal_date) : '—';

    const showUpgrade = state.billing_status !== 'active';
    const upgradeBlock = document.getElementById('profile-billing-upgrade');
    if (upgradeBlock) {
        upgradeBlock.classList.toggle('hidden', !showUpgrade);
    }

    const upgradeButtons = document.getElementById('profile-billing-upgrade-buttons');
    if (upgradeButtons) {
        upgradeButtons.innerHTML = '';
        if (showUpgrade && Array.isArray(state.available_plans)) {
            state.available_plans.forEach(function(planOption) {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'px-3 py-1.5 bg-indigo-600 text-white rounded text-xs hover:bg-indigo-700';
                btn.textContent = planOption.name + ' — $' + planOption.amount + '/mo';
                btn.onclick = function() { startBillingCheckout(planOption.id); };
                upgradeButtons.appendChild(btn);
            });
        }
    }

    const manageBtn = document.getElementById('profile-billing-manage-btn');
    if (manageBtn) {
        manageBtn.classList.toggle('hidden', !state.can_manage_billing);
    }
}

async function startBillingCheckout(plan) {
    try {
        const resp = await authFetch('/api/billing/checkout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ plan }),
        });
        const data = await resp.json();
        if (!resp.ok) {
            alert(data.error || 'Could not start checkout');
            return;
        }
        if (data.checkout_url) {
            window.location.href = data.checkout_url;
        }
    } catch (e) {
        console.error('Checkout failed:', e);
        alert('Could not start checkout. Please try again.');
    }
}

async function openBillingPortal() {
    try {
        const resp = await authFetch('/api/billing/portal', { method: 'POST' });
        const data = await resp.json();
        if (!resp.ok) {
            alert(data.error || 'Could not open billing portal');
            return;
        }
        if (data.portal_url) {
            window.location.href = data.portal_url;
        }
    } catch (e) {
        console.error('Billing portal failed:', e);
        alert('Could not open billing portal. Please try again.');
    }
}

async function loadTrialStatus() {
    if (!isAuthenticated) return;
    try {
        const resp = await authFetch('/api/auth/trial');
        if (resp.ok) {
            const trial = await resp.json();
            applyTrialUI(trial);
        }
        const params = new URLSearchParams(window.location.search);
        if (params.get('billing') === 'success') {
            const sessionId = params.get('session_id');
            if (sessionId) {
                try {
                    const confirmResp = await authFetch('/api/billing/confirm', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ session_id: sessionId }),
                    });
                    if (confirmResp.ok) {
                        const state = await confirmResp.json();
                        applyTrialUI(state);
                    }
                } catch (confirmErr) {
                    console.warn('Billing confirm failed:', confirmErr);
                }
            }
            const msg = document.getElementById('profile-message');
            if (msg) {
                msg.textContent = 'Subscription activated. Thank you!';
                msg.className = 'mb-4 p-3 rounded bg-green-100 text-green-800 border border-green-200';
                msg.classList.remove('hidden');
            }
            window.history.replaceState({}, '', window.location.pathname);
        }
    } catch (e) {
        console.warn('Trial status load failed:', e);
    }
}

function updateAdminUI() {
    const isAdmin = currentUser && currentUser.role === 'admin';
    const badge = document.getElementById('admin-badge');
    const panel = document.getElementById('admin-trial-panel');
    if (badge) {
        badge.classList.toggle('hidden', !isAdmin);
    }
    if (panel && !isAdmin) {
        panel.classList.add('hidden');
    }
}

async function refreshCurrentUserFromServer() {
    try {
        const resp = await authFetch('/api/auth/profile');
        if (!resp.ok) return false;
        const profile = await resp.json();
        if (!profile || !profile.email) return false;
        currentUser = {
            email: profile.email,
            display_name: profile.display_name,
            name: profile.display_name,
            role: profile.role,
            workspaces: profile.workspaces,
            preferences: profile.preferences,
        };
        localStorage.setItem('current_user', JSON.stringify(currentUser));
        updateAdminUI();
        return true;
    } catch (e) {
        console.warn('Profile refresh failed:', e);
        return false;
    }
}

async function loadAdminTrialList() {
    const panel = document.getElementById('admin-trial-panel');
    const list = document.getElementById('admin-trial-list');
    if (!panel || !list) return;
    if (!currentUser || currentUser.role !== 'admin') {
        panel.classList.add('hidden');
        return;
    }
    try {
        const resp = await authFetch('/api/auth/users');
        if (!resp.ok) {
            list.innerHTML = '<div class="text-red-600 py-1">Unable to load users (' + resp.status + ')</div>';
            panel.classList.remove('hidden');
            return;
        }
        const data = await resp.json();
        panel.classList.remove('hidden');
        list.innerHTML = '';
        if (!(data.users || []).length) {
            list.innerHTML = '<div class="text-gray-500 py-1">No users found.</div>';
            return;
        }
        (data.users || []).forEach(function(u) {
            const line = document.createElement('div');
            line.className = 'border-b border-gray-100 py-1';
            line.textContent = (u.email || '') + ' — ' + (u.trial_status || '?')
                + ' — ends ' + formatTrialDate(u.trial_end_date)
                + (u.days_remaining != null ? ' (' + u.days_remaining + 'd)' : '');
            list.appendChild(line);
        });
    } catch (e) {
        console.warn('Admin trial list failed:', e);
    }
}

function assertTrialWrite(actionLabel) {
    if (trialState && trialState.can_write === false) {
        alert('Your trial has expired. Upgrade to continue' + (actionLabel ? ' (' + actionLabel + ').' : '.'));
        return false;
    }
    return true;
}

// Initialize authentication state on page load
function initializeAuth() {
    // Check if user is already logged in (token in localStorage or session)
    const savedToken = localStorage.getItem('auth_token');
    const savedUser = localStorage.getItem('current_user');
    
    if (savedToken && savedUser) {
        try {
            authToken = savedToken;
            currentUser = JSON.parse(savedUser);
            // Verify token is still valid with server
            verifyAuthToken();
        } catch (error) {
            console.error('Error parsing saved user data:', error);
            clearAuthAndRedirect();
        }
    } else {
        // Check if server session exists (after page refresh)
        checkServerSession();
    }
}

async function restoreSessionFromServer() {
    const response = await fetch('/api/auth/verify', {
        method: 'GET',
        credentials: 'include',
        headers: getAuthHeaders(),
    });
    if (!response.ok) {
        return false;
    }
    const data = await response.json();
    if (!data.valid || !data.token) {
        return false;
    }
    authToken = data.token;
    currentUser = data.user;
    localStorage.setItem('auth_token', authToken);
    localStorage.setItem('current_user', JSON.stringify(currentUser));
    updateAdminUI();
    return true;
}

// Check if server has valid session (e.g. after page refresh)
async function checkServerSession() {
    try {
        if (await restoreSessionFromServer()) {
            await refreshCurrentUserFromServer();
            showDashboard();
            return;
        }
    } catch (error) {
        console.log('No valid server session found', error);
    }
    showAuthOverlay();
}

// Verify stored token is still valid
async function verifyAuthToken() {
    try {
        const response = await fetch('/api/auth/verify', {
            headers: getAuthHeaders(),
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.valid && data.token) {
                authToken = data.token;
                currentUser = data.user;
                localStorage.setItem('auth_token', authToken);
                localStorage.setItem('current_user', JSON.stringify(currentUser));
                updateAdminUI();
                await refreshCurrentUserFromServer();
            }
            showDashboard();
        } else {
            clearAuthAndRedirect();
        }
    } catch (error) {
        clearAuthAndRedirect();
    }
}

function clearAuthAndRedirect() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('current_user');
    authToken = null;
    currentUser = null;
    isAuthenticated = false;
    showAuthOverlay();
}

function showAuthOverlay() {
    document.getElementById('auth-overlay').classList.remove('hidden');
    document.getElementById('user-info').classList.add('hidden');
    // Arriving via the "7-day free trial" CTA? Default to signup.
    try {
        const params = new URLSearchParams(window.location.search);
        if (params.get('signup') === '1') {
            showRegisterForm();
        }
    } catch (e) {}
}

function hideAuthOverlay() {
    document.getElementById('auth-overlay').classList.add('hidden');
    if (currentUser) {
        isAuthenticated = true;
        document.getElementById('user-info').classList.remove('hidden');
        document.getElementById('user-display-name').textContent =
            currentUser.display_name || currentUser.name || currentUser.email;
        document.getElementById('user-email').textContent = currentUser.email;
        updateAdminUI();
        // Workspace selector visibility is set by loadWorkspaces() (multi-workspace only)
    }
}

function showDashboard() {
    hideAuthOverlay();
    loadWorkspaces(); // Load available workspaces first - will trigger dashboard loading when appropriate
}

function showLoginForm() {
    document.getElementById('login-form').classList.remove('hidden');
    document.getElementById('register-form').classList.add('hidden');
    clearAuthError();
    clearRegisterError();
}

function cancelAuth() {
    // Abandon any queued save/create and return to the landing / CTA page
    window._pendingAuthRetry = null;
    hideAuthOverlay();
    window.location.href = '/';
}

function showRegisterForm() {
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('register-form').classList.remove('hidden');
    clearAuthError();
    clearRegisterError();
}

function clearAuthError() {
    const errorDiv = document.getElementById('auth-error');
    errorDiv.classList.add('hidden');
    errorDiv.textContent = '';
}

function clearRegisterError() {
    const errorDiv = document.getElementById('register-error');
    errorDiv.classList.add('hidden');
    errorDiv.textContent = '';
}

function showAuthError(message) {
    const errorDiv = document.getElementById('auth-error');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

function showRegisterError(message) {
    const errorDiv = document.getElementById('register-error');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

async function handleLogin(event) {
    event.preventDefault();
    clearAuthError();
    
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const loginButton = document.getElementById('login-button');
    
    // Show loading state
    loginButton.disabled = true;
    loginButton.textContent = 'Signing In...';
    
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',  // Include session cookies
            body: JSON.stringify({
                email: email,
                password: password
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Success - save token and user data
            authToken = data.token;
            currentUser = data.user;
            isAuthenticated = true;

            localStorage.setItem('auth_token', authToken);
            localStorage.setItem('current_user', JSON.stringify(currentUser));
            updateAdminUI();
            await refreshCurrentUserFromServer();

            // Resume a save/create that was interrupted by an expired session
            if (window._pendingAuthRetry) {
                const retry = window._pendingAuthRetry;
                window._pendingAuthRetry = null;
                hideAuthOverlay();
                setTimeout(retry, 100);
            } else {
                showDashboard();
            }
        } else {
            showAuthError(data.error || 'Login failed. Please check your credentials.');
        }
    } catch (error) {
        console.error('Login error:', error);
        showAuthError('Connection error. Please try again.');
    } finally {
        // Reset button state
        loginButton.disabled = false;
        loginButton.textContent = 'Sign In';
    }
}

async function handleRegister(event) {
    event.preventDefault();
    clearRegisterError();
    
    const name = document.getElementById('register-name').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    const registerButton = document.getElementById('register-button');
    
    // Show loading state
    registerButton.disabled = true;
    registerButton.textContent = 'Creating Account...';
    
    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                display_name: name,
                name: name,
                email: email,
                password: password
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.token) {
            authToken = data.token;
            currentUser = data.user;
            localStorage.setItem('auth_token', authToken);
            localStorage.setItem('current_user', JSON.stringify(currentUser));
            showDashboard();
        } else if (response.ok) {
            if (await restoreSessionFromServer()) {
                showDashboard();
            } else {
                showRegisterError(
                    data.message || 'Account created. Please sign in with your new credentials.'
                );
                showLoginForm();
            }
        } else {
            showRegisterError(data.error || 'Registration failed. Please try again.');
        }
    } catch (error) {
        console.error('Registration error:', error);
        showRegisterError('Connection error. Please try again.');
    } finally {
        // Reset button state
        registerButton.disabled = false;
        registerButton.textContent = 'Start 7-Day Free Trial';
    }
}

async function handleLogout() {
    // Clear client auth state
    authToken = null;
    currentUser = null;
    currentWorkspace = null;
    isAuthenticated = false;
    window._pendingAuthRetry = null;

    // Clear localStorage auth + cached assignment data
    localStorage.removeItem('auth_token');
    localStorage.removeItem('current_user');
    if (typeof cache !== 'undefined' && cache.clear) {
        cache.clear();
    }

    // Best-effort: also clear the server-side session cookie
    try {
        await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
    } catch (e) {
        console.warn('Server logout failed (continuing):', e);
    }

    // Return to the landing / CTA page (not the login dialog)
    window.location.href = '/';
}

// Helper function to get authorization headers for API calls
function getAuthHeaders() {
    const headers = {
        'Content-Type': 'application/json'
    };
    if (authToken && authToken !== 'session') {
        headers['Authorization'] = `Bearer ${authToken}`;
    }
    return headers;
}

function authFetch(url, options = {}) {
    const headers = { ...getAuthHeaders(), ...(options.headers || {}) };
    // FormData needs the browser-set multipart boundary — do not force JSON Content-Type
    if (options.body instanceof FormData) {
        delete headers['Content-Type'];
    }
    return fetch(url, {
        credentials: 'include',
        ...options,
        headers,
    });
}
