/* CTO Lens dashboard module: 05-chatbot.js */
function showTab(tabId) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        content.classList.add('hidden');
    });
    
    // Remove active class from all tab buttons
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.classList.remove('active-tab');
    });
    
    // Show selected tab content
    const selectedContent = document.getElementById(tabId + '-content');
    if (selectedContent) {
        selectedContent.classList.remove('hidden');
    }
    
    // Add active class to selected tab button
    const selectedButton = document.getElementById('tab-' + tabId);
    if (selectedButton) {
        selectedButton.classList.add('active-tab');
    }

    // Keep chatbot assignment context in sync with active assignment tab
    if (tabId && tabId.startsWith('assignment-')) {
        selectedAssignmentId = tabId.replace('assignment-', '');
    } else if (tabId === 'overview') {
        selectedAssignmentId = null;
    }
    updateChatbotPrompts();
}

function getActiveAssignmentId() {
    if (selectedAssignmentId) {
        return selectedAssignmentId;
    }
    const activeTab = document.querySelector('.tab-button.active-tab');
    if (activeTab && activeTab.id.startsWith('tab-assignment-')) {
        return activeTab.id.replace('tab-assignment-', '');
    }
    return null;
}

function getActiveAssignmentLabel() {
    const id = getActiveAssignmentId();
    if (!id) return null;
    const list = window.assignments || assignments || [];
    const match = list.find(a => a.id === id);
    return match ? (match.name || match.id) : id;
}

function updateChatbotPrompts() {
    const label = getActiveAssignmentLabel();
    const input = document.getElementById('chatbot-input');
    const quickActions = document.getElementById('chatbot-quick-actions');
    const welcomeHint = document.getElementById('chatbot-welcome-hint');
    if (!input || !quickActions) return;

    const btnClass = 'px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition-colors';

    function addQuickButton(container, text, prompt) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = btnClass;
        btn.textContent = text;
        btn.onclick = () => setChatbotInput(prompt);
        container.appendChild(btn);
    }

    quickActions.innerHTML = '';

    if (label) {
        input.placeholder = 'Ask me about ' + label + ', costs, metrics, team...';
        if (welcomeHint) {
            welcomeHint.textContent = 'Try asking: "What is ' + label + ' status?" or "Show me ' + label + ' AWS costs"';
        }
        addQuickButton(quickActions, label + ' Status', 'What is the status of ' + label + '?');
        addQuickButton(quickActions, label + ' AWS Costs', 'Show me ' + label + ' AWS costs');
        addQuickButton(quickActions, label + ' Burn Rate', 'What is ' + label + ' monthly burn rate?');
        addQuickButton(quickActions, label + ' GitHub', 'Show me ' + label + ' GitHub activity');
        addQuickButton(quickActions, label + ' Team', 'What is ' + label + ' team size?');
    } else {
        input.placeholder = 'Ask me about assignments, costs, metrics...';
        if (welcomeHint) {
            welcomeHint.textContent = 'Open an assignment tab for specific prompts, or ask: "How many assignments do I have?"';
        }
        addQuickButton(quickActions, 'All Assignments', 'How many assignments do I have?');
        addQuickButton(quickActions, 'Workspace Overview', 'Summarize my workspace assignments');
    }
}

// Chatbot Functions
function toggleChatbot() {
    const modal = document.getElementById('chatbot-modal');
    modal.classList.toggle('hidden');
    
    // Load conversation history when opening
    if (!modal.classList.contains('hidden')) {
        updateChatbotPrompts();
        loadChatbotHistory();
    }
}

async function loadChatbotHistory() {
    const messages = document.getElementById('chatbot-messages');
    
    try {
        const response = await fetch('/api/chatbot/history?user_id=dashboard_user&limit=20', {
            headers: getAuthHeaders()
        });
        const data = await response.json();
        
        if (data.history && data.history.length > 0) {
            // Clear existing messages except welcome message
            messages.innerHTML = '';
            
            // Add conversation history (backend stores role/content)
            data.history.forEach(msg => {
                const messageDiv = document.createElement('div');
                const text = msg.content || msg.question || msg.response || '';
                if (msg.role === 'user') {
                    messageDiv.className = 'flex justify-end';
                    messageDiv.innerHTML = '<div class="max-w-[80%] rounded-lg px-4 py-2 bg-blue-500 text-white"><div class="whitespace-pre-wrap">' + text + '</div></div>';
                } else {
                    messageDiv.className = 'flex justify-start';
                    messageDiv.innerHTML = '<div class="max-w-[80%] rounded-lg px-4 py-2 bg-gray-100 text-gray-900"><div class="whitespace-pre-wrap">' + text + '</div></div>';
                }
                messages.appendChild(messageDiv);
            });
        }
        
        // Scroll to bottom
        messages.scrollTop = messages.scrollHeight;
        
    } catch (error) {
        console.error('Error loading chat history:', error);
    }
}

async function clearChatbotHistory() {
    if (confirm('Are you sure you want to clear the conversation history?')) {
        try {
            const response = await fetch('/api/chatbot/clear', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({
                    user_id: 'dashboard_user'
                })
            });
            
            if (response.ok) {
                // Clear messages and show welcome message
                const messages = document.getElementById('chatbot-messages');
                messages.innerHTML = '<div class="text-center text-gray-500 py-8"><div class="text-4xl mb-4">🤖</div><h3 class="text-lg font-medium mb-2">Welcome to CTO Lens Assistant!</h3><p class="text-sm">I can help you with questions about:</p><ul class="text-sm mt-2 space-y-1"><li>• Your assignments and projects</li><li>• AWS costs and resource usage</li><li>• GitHub metrics and activity</li><li>• Jira project status</li><li>• Team information and tech stacks</li><li>• Service health and configuration</li></ul><p id="chatbot-welcome-hint" class="text-sm mt-4 text-gray-400">Open an assignment tab for specific prompts, or ask about your workspace.</p></div>';
                updateChatbotPrompts();
            }
        } catch (error) {
            console.error('Error clearing chat history:', error);
        }
    }
}

function handleChatbotKeyPress(event) {
    if (event.key === 'Enter') {
        sendChatbotMessage();
    }
}

function setChatbotInput(text) {
    const input = document.getElementById('chatbot-input');
    input.value = text;
    input.focus();
}

function appendChatbotUserMessage(messages, text) {
    const userMessage = document.createElement('div');
    userMessage.className = 'flex justify-end';
    userMessage.innerHTML = '<div class="max-w-[80%] rounded-lg px-4 py-2 bg-blue-500 text-white"><div class="whitespace-pre-wrap">' + text + '</div></div>';
    messages.appendChild(userMessage);
}

function showMetricsConsentButtons(messages, pendingQuestion) {
    const row = document.createElement('div');
    row.className = 'flex justify-start gap-2 mt-2';
    row.innerHTML = `
        <button type="button" class="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700">Yes, fetch metrics (90+ sec)</button>
        <button type="button" class="bg-gray-500 text-white px-3 py-1 rounded text-sm hover:bg-gray-600">No, use details only</button>
    `;
    const yesBtn = row.querySelector('button:first-child');
    const noBtn = row.querySelector('button:last-child');
    yesBtn.onclick = () => {
        row.remove();
        sendChatbotMessage(pendingQuestion, { fetch_metrics: true, showUserBubble: false });
    };
    noBtn.onclick = () => {
        row.remove();
        sendChatbotMessage(pendingQuestion, { skip_metrics_fetch: true, showUserBubble: false });
    };
    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;
}

async function sendChatbotMessage(questionOverride, options = {}) {
    const input = document.getElementById('chatbot-input');
    const messages = document.getElementById('chatbot-messages');
    const question = (questionOverride || input.value || '').trim();
    const assignmentId = getActiveAssignmentId();
    const fetch_metrics = !!options.fetch_metrics;
    const skip_metrics_fetch = !!options.skip_metrics_fetch;
    const showUserBubble = options.showUserBubble !== false;

    if (!question) {
        return;
    }

    if (showUserBubble) {
        appendChatbotUserMessage(messages, question);
        input.value = '';
    }

    const botMessageContainer = document.createElement('div');
    botMessageContainer.className = 'flex justify-start';
    const botMessageContent = document.createElement('div');
    botMessageContent.className = 'max-w-[80%] rounded-lg px-4 py-2 bg-gray-100 text-gray-900';
    const botMessageText = document.createElement('div');
    botMessageText.className = 'whitespace-pre-wrap';
    botMessageText.innerHTML = '<span class="inline-block w-2 h-4 bg-gray-400 animate-pulse">▋</span>';
    botMessageContent.appendChild(botMessageText);
    botMessageContainer.appendChild(botMessageContent);
    messages.appendChild(botMessageContainer);
    messages.scrollTop = messages.scrollHeight;

    try {
        const response = await fetch('/api/chatbot/ask-stream', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                question: question,
                user_id: 'dashboard_user',
                workspace_id: currentWorkspace,
                assignment_id: assignmentId,
                fetch_metrics: fetch_metrics,
                skip_metrics_fetch: skip_metrics_fetch,
            })
        });

        if (!response.ok) {
            throw new Error('Stream request failed');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = '';
        let receivedAny = false;
        let pendingQuestion = null;

        while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                let data;
                try {
                    data = JSON.parse(line.substring(6));
                } catch (parseErr) {
                    continue;
                }
                if (data.status === 'fetching_metrics') {
                    botMessageText.textContent = data.message || 'Loading metrics...';
                    continue;
                }
                if (data.init) {
                    if (!fetch_metrics) {
                        botMessageText.textContent = '';
                    }
                    continue;
                }
                if (data.token) {
                    receivedAny = true;
                    fullResponse += data.token;
                    botMessageText.textContent = fullResponse + '▋';
                    messages.scrollTop = messages.scrollHeight;
                    continue;
                }
                if (data.done) {
                    botMessageText.textContent = data.full_response || fullResponse || '(no response)';
                    if (data.metrics_action_required === 'confirm_fetch' && data.pending_question) {
                        pendingQuestion = data.pending_question;
                        showMetricsConsentButtons(messages, pendingQuestion);
                    }
                    continue;
                }
                if (data.error) {
                    throw new Error(data.error);
                }
            }
        }

        if (!receivedAny && !pendingQuestion) {
            const fallback = await fetch('/api/chatbot/ask', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({
                    question,
                    user_id: 'dashboard_user',
                    workspace_id: currentWorkspace,
                    assignment_id: assignmentId,
                    fetch_metrics: fetch_metrics,
                    skip_metrics_fetch: skip_metrics_fetch,
                })
            });
            const json = await fallback.json();
            botMessageText.textContent = (json && json.response) ? json.response : '(no response)';
            if (json && json.metrics_action_required === 'confirm_fetch' && json.pending_question) {
                showMetricsConsentButtons(messages, json.pending_question);
            }
        }

    } catch (error) {
        console.error('Chatbot error:', error);
        botMessageContainer.remove();
        const errorMessage = document.createElement('div');
        errorMessage.className = 'flex justify-start';
        errorMessage.innerHTML = '<div class="max-w-[80%] rounded-lg px-4 py-2 bg-red-100 text-red-800"><div class="whitespace-pre-wrap">Sorry, I encountered an error. Please try again.</div></div>';
        messages.appendChild(errorMessage);
    }

    messages.scrollTop = messages.scrollHeight;
}

// Phase 5B: Enhanced Assignment Management Functions
