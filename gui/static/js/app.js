class OracleGUI {
    constructor() {
        this.socket = null;
        this.currentView = 'chat';
        this.sessionId = 'default';
        this.messageHistory = [];
        this.sessions = [];
        this.activity = [];
        this.toolHistory = [];
        this.isConnected = false;
        this.isThinking = false;
        this.pendingStartedAt = null;
        this.helpFeatures = null;
        this.status = null;
        this.health = null;
        this.settings = null;
        this.analytics = {
            conversations: 0,
            toolsExecuted: 0,
            avgResponseTime: 0,
            successRate: 100,
        };
        this.commandItems = [];
        this.activePaletteIndex = 0;
        this.maxActivity = 14;

        this.toolSchemas = {
            shell_execute: [
                { name: 'command', label: 'Command', type: 'textarea', required: true, placeholder: 'rg -n "OracleAgent" src/oracle' },
            ],
            file_system_ops: [
                {
                    name: 'operation',
                    label: 'Operation',
                    type: 'select',
                    required: true,
                    options: ['read', 'write', 'list', 'delete'],
                },
                { name: 'path', label: 'Path', type: 'text', required: true, placeholder: 'src/oracle/agent_system.py' },
                { name: 'content', label: 'Content', type: 'textarea', required: false, placeholder: 'Only used for write operations.' },
            ],
            http_fetch: [
                { name: 'url', label: 'URL', type: 'text', required: true, placeholder: 'https://api.github.com/repos/openai/openai-python' },
                {
                    name: 'method',
                    label: 'Method',
                    type: 'select',
                    required: true,
                    options: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
                },
                { name: 'headers', label: 'Headers JSON', type: 'textarea', required: false, placeholder: '{"Accept":"application/json"}' },
            ],
            vision_capture: [
                { name: 'reason', label: 'Reason', type: 'text', required: true, placeholder: 'Capture the current desktop state for inspection.' },
            ],
        };

        this.cacheElements();
        this.restoreState();
        this.configureMarkdown();
        this.bindEvents();
        this.initializeSocket();
        this.bootstrap();
    }

    cacheElements() {
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('btn-send');
        this.messagesContainer = document.getElementById('messages');
        this.welcomeCard = document.getElementById('welcome-card');
        this.loadingOverlay = document.getElementById('loading-overlay');
        this.toastContainer = document.getElementById('toast-container');
        this.promptBank = document.getElementById('prompt-bank');
        this.sessionIdDisplay = document.getElementById('session-id');
        this.sessionTitle = document.getElementById('session-title');
        this.heroSubtitle = document.getElementById('hero-subtitle');
        this.currentViewLabel = document.getElementById('current-view-label');
        this.heroMessageCount = document.getElementById('hero-message-count');
        this.heroToolCount = document.getElementById('hero-tool-count');
        this.heroResponseTime = document.getElementById('hero-response-time');
        this.statusText = document.getElementById('status-text');
        this.railStatusText = document.getElementById('rail-status-text');
        this.railStatusDot = document.getElementById('rail-status-dot');
        this.connectionPill = document.getElementById('connection-pill');
        this.connectionPillText = document.getElementById('connection-pill-text');
        this.telemetryProject = document.getElementById('telemetry-project');
        this.telemetryModel = document.getElementById('telemetry-model');
        this.telemetryTime = document.getElementById('telemetry-time');
        this.configModel = document.getElementById('config-model');
        this.configGcs = document.getElementById('config-gcs');
        this.configTurns = document.getElementById('config-turns');
        this.activityList = document.getElementById('activity-list');
        this.miniActivityFeed = document.getElementById('mini-activity-feed');
        this.toolDeck = document.getElementById('tool-deck');
        this.sessionsList = document.getElementById('sessions-list');
        this.helpGrid = document.getElementById('help-grid');
        this.commandPalette = document.getElementById('command-palette');
        this.commandSearchInput = document.getElementById('command-search-input');
        this.commandResults = document.getElementById('command-results');
        this.sessionModal = document.getElementById('session-modal');
        this.newSessionName = document.getElementById('new-session-name');
        this.toolPanel = document.getElementById('tool-panel');
        this.toolPanelTitle = document.getElementById('tool-panel-title');
        this.toolPanelContent = document.getElementById('tool-panel-content');
        this.viewNavItems = Array.from(document.querySelectorAll('.nav-pill'));
        this.viewStages = Array.from(document.querySelectorAll('.view-stage'));
        this.promptCards = Array.from(document.querySelectorAll('.prompt-card'));

        this.dashboardElements = {
            totalConversations: document.getElementById('total-conversations'),
            toolsExecuted: document.getElementById('tools-executed'),
            avgResponseTime: document.getElementById('avg-response-time'),
            successRate: document.getElementById('success-rate'),
            statusModel: document.getElementById('status-model'),
            statusDb: document.getElementById('status-db'),
            statusCloud: document.getElementById('status-cloud'),
            statusMemory: document.getElementById('status-memory'),
        };

        this.analyticsElements = {
            timeframe: document.getElementById('analytics-timeframe'),
            metric: document.getElementById('analytics-metric'),
            conversationChart: document.getElementById('conversation-chart'),
            toolChart: document.getElementById('tool-chart'),
            performanceChart: document.getElementById('performance-chart'),
            insightsList: document.getElementById('insights-list'),
        };

        this.settingsElements = {
            modelSelect: document.getElementById('model-select'),
            maxTurns: document.getElementById('max-turns'),
            maxTurnsDisplay: document.getElementById('max-turns-display'),
            temperature: document.getElementById('temperature'),
            temperatureDisplay: document.getElementById('temperature-display'),
            guiApiKey: document.getElementById('gui-api-key'),
            shellTimeout: document.getElementById('shell-timeout'),
            httpTimeout: document.getElementById('http-timeout'),
            enableFileSandbox: document.getElementById('enable-file-sandbox'),
            enableGcsBackup: document.getElementById('enable-gcs-backup'),
            gcsBucket: document.getElementById('gcs-bucket'),
            autoBackup: document.getElementById('auto-backup'),
            enableDebug: document.getElementById('enable-debug'),
            enableMetrics: document.getElementById('enable-metrics'),
            logLevel: document.getElementById('log-level'),
            saveBtn: document.getElementById('save-settings'),
            resetBtn: document.getElementById('reset-settings'),
            exportBtn: document.getElementById('export-settings'),
            note: document.getElementById('settings-note'),
        };
    }

    configureMarkdown() {
        marked.setOptions({
            breaks: true,
            gfm: true,
            headerIds: false,
        });
    }

    restoreState() {
        this.restoreApiKey();
        this.restoreSessions();
        this.loadSession(this.sessionId, { announce: false });
    }

    restoreApiKey() {
        const apiKey = sessionStorage.getItem('oracle_gui_api_key') || '';
        if (this.settingsElements.guiApiKey) {
            this.settingsElements.guiApiKey.value = apiKey;
        }
    }

    setApiKey(apiKey) {
        const normalized = typeof apiKey === 'string' ? apiKey.trim() : '';
        if (normalized) {
            sessionStorage.setItem('oracle_gui_api_key', normalized);
        } else {
            sessionStorage.removeItem('oracle_gui_api_key');
        }
        if (this.settingsElements.guiApiKey) {
            this.settingsElements.guiApiKey.value = normalized;
        }
    }

    getApiKey() {
        return sessionStorage.getItem('oracle_gui_api_key') || '';
    }

    restoreSessions() {
        const saved = localStorage.getItem('oracle_gui_sessions');
        if (saved) {
            try {
                this.sessions = JSON.parse(saved);
            } catch (_error) {
                this.sessions = [];
            }
        }
        if (!Array.isArray(this.sessions) || this.sessions.length === 0) {
            this.sessions = [this.createSessionObject('default', 'Default Session')];
        }
        if (!this.sessions.some((session) => session.id === this.sessionId)) {
            this.sessionId = this.sessions[0].id;
        }
    }

    persistSessions() {
        localStorage.setItem('oracle_gui_sessions', JSON.stringify(this.sessions));
    }

    createSessionObject(id, title) {
        return {
            id,
            title,
            created: new Date().toISOString(),
            lastActive: new Date().toISOString(),
            messages: [],
        };
    }

    bootstrap() {
        this.renderSessions();
        this.renderTranscript();
        this.populateCommandPalette();
        this.renderAnalytics();
        this.renderHelpFallback();
        this.renderToolDeck();
        this.updateSettingsDisplays();
        this.loadStatus();
        this.loadHelp();
        this.loadSettings();
        this.refreshStats();
        this.pushActivity('System ready', 'Interface boot sequence completed.', 'system');
    }

    buildApiHeaders(json = false) {
        const headers = {};
        if (json) {
            headers['Content-Type'] = 'application/json';
        }
        const apiKey = this.getApiKey();
        if (apiKey) {
            headers['X-API-Key'] = apiKey;
        }
        return headers;
    }

    bindEvents() {
        this.messageInput.addEventListener('input', () => {
            this.autoResizeComposer();
            this.updateSendButton();
        });
        this.messageInput.addEventListener('keydown', (event) => this.handleComposerKeydown(event));
        this.sendButton.addEventListener('click', () => this.sendMessage());
        document.getElementById('focus-composer-button').addEventListener('click', () => this.messageInput.focus());

        this.promptCards.forEach((card) => {
            card.addEventListener('click', () => {
                this.messageInput.value = card.dataset.prompt || '';
                this.autoResizeComposer();
                this.updateSendButton();
                this.messageInput.focus();
            });
        });

        this.viewNavItems.forEach((item) => {
            item.addEventListener('click', () => this.switchView(item.dataset.view));
        });

        document.querySelectorAll('.tool-chip').forEach((chip) => {
            chip.addEventListener('click', () => this.openToolPanel(chip.dataset.tool));
        });

        document.getElementById('btn-open-command').addEventListener('click', () => this.openCommandPalette());
        document.getElementById('command-palette-trigger').addEventListener('click', () => this.openCommandPalette());
        document.getElementById('close-command-palette').addEventListener('click', () => this.closeCommandPalette());
        this.commandPalette.addEventListener('click', (event) => {
            if (event.target === this.commandPalette) {
                this.closeCommandPalette();
            }
        });
        this.commandSearchInput.addEventListener('input', () => this.renderCommandResults());
        this.commandSearchInput.addEventListener('keydown', (event) => this.handlePaletteKeydown(event));

        document.getElementById('btn-backup').addEventListener('click', () => this.triggerBackup());
        document.getElementById('btn-clear').addEventListener('click', () => this.clearHistory());
        document.getElementById('btn-new-session').addEventListener('click', () => this.openSessionModal());
        document.getElementById('create-session-confirm').addEventListener('click', () => this.createSessionFromModal());
        document.getElementById('create-session-cancel').addEventListener('click', () => this.closeSessionModal());
        this.sessionModal.addEventListener('click', (event) => {
            if (event.target === this.sessionModal) {
                this.closeSessionModal();
            }
        });

        document.getElementById('btn-close-panel').addEventListener('click', () => this.closeToolPanel());

        document.getElementById('btn-refresh-dashboard').addEventListener('click', () => {
            this.loadStatus();
            this.refreshStats();
            this.showToast('Dashboard refreshed.', 'success');
        });

        document.getElementById('btn-export-sessions').addEventListener('click', () => this.exportSessions());
        document.getElementById('btn-import-sessions').addEventListener('click', () => this.importSessions());

        this.analyticsElements.timeframe.addEventListener('change', () => this.renderAnalytics());
        this.analyticsElements.metric.addEventListener('change', () => this.renderAnalytics());

        this.settingsElements.saveBtn.addEventListener('click', () => this.saveSettings());
        this.settingsElements.resetBtn.addEventListener('click', () => this.resetSettings());
        this.settingsElements.exportBtn.addEventListener('click', () => this.exportSettings());
        this.settingsElements.maxTurns.addEventListener('input', () => this.updateSettingsDisplays());
        this.settingsElements.temperature.addEventListener('input', () => this.updateSettingsDisplays());
        this.settingsElements.guiApiKey.addEventListener('change', () => this.reconnectSocket());

        document.addEventListener('keydown', (event) => this.handleGlobalShortcuts(event));
    }

    initializeSocket() {
        if (this.socket) {
            this.socket.disconnect();
        }

        this.socket = io({
            auth: { apiKey: this.getApiKey() },
        });

        this.socket.on('connect', () => {
            this.isConnected = true;
            this.updateConnectionState('ready');
            this.pushActivity('Socket connected', 'Live link to Oracle established.', 'network');
        });

        this.socket.on('disconnect', () => {
            this.isConnected = false;
            this.updateConnectionState('error');
            this.pushActivity('Socket disconnected', 'Realtime link dropped.', 'network');
        });

        this.socket.on('connect_error', (error) => {
            this.isConnected = false;
            this.updateConnectionState('error');
            this.showToast(error?.message || 'Socket connection rejected.', 'error');
        });

        this.socket.on('agent_status', (data) => {
            this.updateConnectionState(data?.initialized ? 'ready' : 'initializing', data);
            this.refreshTelemetry(data);
        });

        this.socket.on('thinking', () => {
            this.isThinking = true;
            this.showLoading();
            this.updateSendButton();
            this.pushActivity('Oracle thinking', 'Inference request sent to the agent.', 'thinking');
        });

        this.socket.on('message', (payload) => {
            this.isThinking = false;
            this.hideLoading();
            const timestamp = payload?.timestamp || new Date().toISOString();
            this.addMessage({
                role: payload?.role || 'assistant',
                content: payload?.content || '',
                timestamp,
            });

            if (this.pendingStartedAt) {
                const latency = Date.now() - this.pendingStartedAt;
                this.recordResponseTime(latency);
                this.pendingStartedAt = null;
            }

            this.pushActivity('Response received', 'Oracle returned an assistant turn.', 'assistant');
            this.updateSendButton();
        });

        this.socket.on('tool_executing', (payload) => {
            this.pushActivity(`Tool running: ${payload.tool}`, 'Manual tool execution started.', 'tool');
        });

        this.socket.on('tool_result', (payload) => {
            this.toolHistory.unshift({
                name: payload.tool,
                result: payload.result,
                timestamp: payload.timestamp || new Date().toISOString(),
            });
            this.toolHistory = this.toolHistory.slice(0, 8);
            this.analytics.toolsExecuted += 1;
            this.renderToolDeck();
            this.refreshStats();
            this.renderToolResult(payload.tool, payload.result);
            this.pushActivity(`Tool complete: ${payload.tool}`, 'Tool execution finished.', 'tool');
        });

        this.socket.on('backup_result', (payload) => {
            if (payload?.success) {
                this.showToast('Backup completed successfully.', 'success');
                this.pushActivity('Backup complete', payload.gcs_uri || 'Cloud backup completed.', 'system');
            } else {
                this.showToast(`Backup failed: ${payload?.error || 'Unknown error'}`, 'error');
            }
        });

        this.socket.on('history_cleared', () => {
            this.clearCurrentSessionMessages();
            this.showToast('Session history cleared.', 'success');
            this.pushActivity('History cleared', 'Session transcript reset.', 'system');
        });

        this.socket.on('error', (payload) => {
            this.isThinking = false;
            this.hideLoading();
            this.showToast(payload?.message || 'An error occurred.', 'error');
            this.recordFailure();
            this.updateSendButton();
        });
    }

    reconnectSocket() {
        this.setApiKey(this.settingsElements.guiApiKey.value);
        this.initializeSocket();
        this.loadSettings();
    }

    handleComposerKeydown(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            this.sendMessage();
        }
    }

    handleGlobalShortcuts(event) {
        const isModifier = event.ctrlKey || event.metaKey;

        if (isModifier && event.key.toLowerCase() === 'k') {
            event.preventDefault();
            this.openCommandPalette();
            return;
        }

        if (isModifier && event.key.toLowerCase() === 'n') {
            event.preventDefault();
            this.openSessionModal();
            return;
        }

        if (event.key === 'Escape') {
            this.closeToolPanel();
            this.closeCommandPalette();
            this.closeSessionModal();
        }
    }

    handlePaletteKeydown(event) {
        const items = Array.from(this.commandResults.querySelectorAll('.palette-item'));
        if (event.key === 'ArrowDown') {
            event.preventDefault();
            this.activePaletteIndex = Math.min(this.activePaletteIndex + 1, items.length - 1);
            this.highlightPaletteItem();
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            this.activePaletteIndex = Math.max(this.activePaletteIndex - 1, 0);
            this.highlightPaletteItem();
        } else if (event.key === 'Enter') {
            event.preventDefault();
            items[this.activePaletteIndex]?.click();
        }
    }

    openCommandPalette() {
        this.commandPalette.classList.add('open');
        this.commandPalette.setAttribute('aria-hidden', 'false');
        this.commandSearchInput.value = '';
        this.activePaletteIndex = 0;
        this.renderCommandResults();
        this.commandSearchInput.focus();
    }

    closeCommandPalette() {
        this.commandPalette.classList.remove('open');
        this.commandPalette.setAttribute('aria-hidden', 'true');
    }

    populateCommandPalette() {
        this.commandItems = [
            { title: 'Switch to Mission', description: 'Open the live conversation view.', action: () => this.switchView('chat') },
            { title: 'Switch to Pulse', description: 'Open the dashboard view.', action: () => this.switchView('dashboard') },
            { title: 'Open Sessions', description: 'Review and load stored sessions.', action: () => this.switchView('sessions') },
            { title: 'Open Analytics', description: 'Inspect usage and performance patterns.', action: () => this.switchView('analytics') },
            { title: 'Open Settings', description: 'Edit runtime controls and API credentials.', action: () => this.switchView('settings') },
            { title: 'Open Guide', description: 'Show help and workflow documentation.', action: () => this.switchView('help') },
            { title: 'Create session', description: 'Start a new named conversation.', action: () => this.openSessionModal() },
            { title: 'Backup to GCS', description: 'Trigger the backup flow.', action: () => this.triggerBackup() },
            { title: 'Clear history', description: 'Clear the active session transcript.', action: () => this.clearHistory() },
            { title: 'Run shell tool', description: 'Open manual shell execution.', action: () => this.openToolPanel('shell_execute') },
            { title: 'Run file tool', description: 'Open manual file operations.', action: () => this.openToolPanel('file_system_ops') },
            { title: 'Run HTTP tool', description: 'Open manual HTTP fetch.', action: () => this.openToolPanel('http_fetch') },
            { title: 'Run vision tool', description: 'Open manual vision capture.', action: () => this.openToolPanel('vision_capture') },
        ];
    }

    renderCommandResults() {
        const query = this.commandSearchInput.value.trim().toLowerCase();
        const results = this.commandItems.filter((item) => {
            return `${item.title} ${item.description}`.toLowerCase().includes(query);
        });

        this.commandResults.innerHTML = '';
        results.forEach((item, index) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'palette-item';
            if (index === 0) {
                button.classList.add('active');
            }
            button.innerHTML = `<strong>${item.title}</strong><small>${item.description}</small>`;
            button.addEventListener('click', () => {
                item.action();
                this.closeCommandPalette();
            });
            this.commandResults.appendChild(button);
        });
        this.activePaletteIndex = 0;
    }

    highlightPaletteItem() {
        const items = Array.from(this.commandResults.querySelectorAll('.palette-item'));
        items.forEach((item, index) => item.classList.toggle('active', index === this.activePaletteIndex));
    }

    switchView(view) {
        this.currentView = view;
        this.viewNavItems.forEach((item) => item.classList.toggle('active', item.dataset.view === view));
        this.viewStages.forEach((stage) => stage.classList.toggle('active', stage.id === `${view}-view`));
        this.currentViewLabel.textContent = this.viewName(view);

        if (view === 'help') {
            this.loadHelp();
        }
        if (view === 'settings') {
            this.loadSettings();
        }
        if (view === 'analytics') {
            this.renderAnalytics();
        }
    }

    viewName(view) {
        const names = {
            chat: 'Mission',
            dashboard: 'Pulse',
            sessions: 'Sessions',
            analytics: 'Analytics',
            settings: 'Settings',
            help: 'Guide',
        };
        return names[view] || 'Mission';
    }

    loadStatus() {
        Promise.all([
            fetch('/api/status'),
            fetch('/api/health'),
        ])
            .then(async ([statusResponse, healthResponse]) => {
                this.status = statusResponse.ok ? await statusResponse.json() : null;
                this.health = healthResponse.ok ? await healthResponse.json() : null;
                this.applyStatus();
            })
            .catch(() => {
                this.updateConnectionState('error');
                this.showToast('Unable to load GUI status.', 'warning');
            });
    }

    applyStatus() {
        const initialized = Boolean(this.status?.initialized);
        this.updateConnectionState(initialized ? 'ready' : 'initializing', this.status);
        this.refreshTelemetry(this.status);

        this.configModel.textContent = this.status?.model_id || '-';
        this.configGcs.textContent = this.status?.gcs_enabled ? 'Ready' : 'Off';
        this.configTurns.textContent = this.status?.max_turns ?? '-';

        this.dashboardElements.statusModel.textContent = this.status?.model_id || 'Unavailable';
        this.dashboardElements.statusDb.textContent = this.health?.config_loaded ? 'Healthy' : 'Waiting';
        this.dashboardElements.statusCloud.textContent = this.status?.gcs_enabled ? 'Ready' : 'Disabled';
        this.dashboardElements.statusMemory.textContent = initialized ? 'Stable' : 'Cold start';
    }

    refreshTelemetry(statusData) {
        this.telemetryProject.textContent = statusData?.gcp_project || 'Local mode';
        this.telemetryModel.textContent = statusData?.model_id || 'Unknown';
        this.telemetryTime.textContent = new Date(statusData?.timestamp || Date.now()).toLocaleTimeString();
        this.statusText.textContent = this.railStatusText.textContent;
    }

    updateConnectionState(state, data = null) {
        const labels = {
            ready: 'Connected',
            error: 'Attention',
            initializing: 'Booting',
        };
        const label = data?.initialized === false ? 'Booting' : labels[state] || 'Booting';

        this.railStatusText.textContent = label;
        this.statusText.textContent = label;
        this.connectionPillText.textContent = this.isConnected ? label : 'Offline';

        ['ready', 'error', 'initializing'].forEach((className) => {
            this.railStatusDot.classList.remove(className);
            this.connectionPill.querySelector('.signal-dot').classList.remove(className);
        });

        const normalizedState = this.isConnected ? state : 'error';
        this.railStatusDot.classList.add(normalizedState);
        this.connectionPill.querySelector('.signal-dot').classList.add(normalizedState);
    }

    autoResizeComposer() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = `${Math.min(this.messageInput.scrollHeight, 220)}px`;
    }

    updateSendButton() {
        const hasMessage = this.messageInput.value.trim().length > 0;
        this.sendButton.disabled = !hasMessage || this.isThinking || !this.isConnected;
    }

    sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isThinking || !this.socket) {
            return;
        }

        const timestamp = new Date().toISOString();
        this.addMessage({ role: 'user', content: message, timestamp });
        this.socket.emit('send_message', {
            message,
            session_id: this.sessionId,
        });

        this.pendingStartedAt = Date.now();
        this.messageInput.value = '';
        this.autoResizeComposer();
        this.updateSendButton();
    }

    addMessage(message) {
        const session = this.getCurrentSession();
        if (!session) {
            return;
        }

        session.messages.push(message);
        session.lastActive = new Date().toISOString();
        this.messageHistory = session.messages;
        this.persistSessions();
        this.renderTranscript();
        this.renderSessions();
        this.refreshStats();
    }

    renderTranscript() {
        const session = this.getCurrentSession();
        if (!session) {
            return;
        }

        this.messageHistory = session.messages || [];
        this.sessionIdDisplay.textContent = this.sessionId;
        this.sessionTitle.textContent = session.title;
        this.heroSubtitle.textContent = this.messageHistory.length
            ? 'Session memory is active and ready to continue.'
            : 'A clean runway for the next task, audit, or build step.';

        this.messagesContainer.innerHTML = '';
        if (this.messageHistory.length === 0) {
            this.messagesContainer.appendChild(this.welcomeCard);
        } else {
            this.welcomeCard.remove();
        }

        this.messageHistory.forEach((message) => {
            this.messagesContainer.appendChild(this.createMessageNode(message));
        });

        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    createMessageNode(message) {
        const article = document.createElement('article');
        article.className = `message-card ${message.role}`;

        const meta = document.createElement('div');
        meta.className = 'message-meta';
        const role = document.createElement('span');
        role.textContent = message.role === 'assistant' ? 'Oracle' : 'Operator';
        const timestamp = document.createElement('span');
        timestamp.textContent = new Date(message.timestamp || Date.now()).toLocaleTimeString();
        const metaRight = document.createElement('div');
        metaRight.className = 'message-actions';
        const copyButton = document.createElement('button');
        copyButton.type = 'button';
        copyButton.className = 'message-action';
        copyButton.textContent = 'Copy';
        copyButton.addEventListener('click', async () => {
            await navigator.clipboard.writeText(message.content || '');
            this.showToast('Message copied.', 'success');
        });
        metaRight.appendChild(copyButton);
        meta.appendChild(role);
        meta.appendChild(timestamp);
        meta.appendChild(metaRight);

        const content = document.createElement('div');
        content.className = 'message-content';
        if (message.role === 'assistant') {
            const rendered = DOMPurify.sanitize(marked.parse(message.content || ''));
            content.innerHTML = rendered;
            content.querySelectorAll('pre code').forEach((block) => hljs.highlightElement(block));
        } else {
            content.textContent = message.content || '';
        }

        article.appendChild(meta);
        article.appendChild(content);
        return article;
    }

    getCurrentSession() {
        let session = this.sessions.find((item) => item.id === this.sessionId);
        if (!session) {
            session = this.sessions[0];
            this.sessionId = session.id;
        }
        return session;
    }

    renderSessions() {
        this.sessionsList.innerHTML = '';
        const sorted = [...this.sessions].sort((left, right) => {
            return new Date(right.lastActive).getTime() - new Date(left.lastActive).getTime();
        });

        sorted.forEach((session) => {
            const card = document.createElement('article');
            card.className = 'session-entry';
            const preview = session.messages[0]?.content || 'No messages yet.';
            card.innerHTML = `
                <div class="session-entry-head">
                    <div>
                        <h4>${this.escapeHtml(session.title)}</h4>
                        <div class="session-entry-meta">
                            <span>${new Date(session.created).toLocaleDateString()}</span>
                            <span>${session.messages.length} messages</span>
                            <span>${new Date(session.lastActive).toLocaleTimeString()}</span>
                        </div>
                    </div>
                    <div class="session-entry-actions">
                        <button class="ghost-button" type="button" data-action="load">Load</button>
                        <button class="ghost-button" type="button" data-action="delete">Delete</button>
                    </div>
                </div>
                <p>${this.escapeHtml(preview.slice(0, 180))}${preview.length > 180 ? '…' : ''}</p>
            `;
            card.querySelector('[data-action="load"]').addEventListener('click', () => this.loadSession(session.id));
            card.querySelector('[data-action="delete"]').addEventListener('click', () => this.deleteSession(session.id));
            this.sessionsList.appendChild(card);
        });
    }

    loadSession(sessionId, options = { announce: true }) {
        const session = this.sessions.find((item) => item.id === sessionId);
        if (!session) {
            return;
        }
        this.sessionId = session.id;
        this.messageHistory = session.messages;
        this.renderTranscript();
        this.refreshStats();
        if (options.announce) {
            this.showToast(`Loaded session "${session.title}".`, 'success');
        }
    }

    openSessionModal() {
        this.sessionModal.classList.add('open');
        this.sessionModal.setAttribute('aria-hidden', 'false');
        this.newSessionName.value = '';
        this.newSessionName.focus();
    }

    closeSessionModal() {
        this.sessionModal.classList.remove('open');
        this.sessionModal.setAttribute('aria-hidden', 'true');
    }

    createSessionFromModal() {
        const title = this.newSessionName.value.trim();
        if (!title) {
            this.showToast('Choose a session name first.', 'warning');
            return;
        }

        const id = `session_${Date.now()}`;
        this.sessions.unshift(this.createSessionObject(id, title));
        this.persistSessions();
        this.renderSessions();
        this.loadSession(id, { announce: false });
        this.closeSessionModal();
        this.showToast(`Created session "${title}".`, 'success');
        this.pushActivity('Session created', title, 'session');
    }

    deleteSession(sessionId) {
        if (this.sessions.length === 1) {
            this.showToast('At least one session must remain.', 'warning');
            return;
        }

        const session = this.sessions.find((item) => item.id === sessionId);
        if (!session) {
            return;
        }

        this.sessions = this.sessions.filter((item) => item.id !== sessionId);
        if (this.sessionId === sessionId) {
            this.sessionId = this.sessions[0].id;
        }
        this.persistSessions();
        this.loadSession(this.sessionId, { announce: false });
        this.renderSessions();
        this.showToast(`Deleted session "${session.title}".`, 'success');
    }

    exportSessions() {
        this.downloadJson(this.sessions, `oracle_sessions_${new Date().toISOString().slice(0, 10)}.json`);
        this.showToast('Sessions exported.', 'success');
    }

    importSessions() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json,application/json';
        input.addEventListener('change', async () => {
            const [file] = input.files;
            if (!file) {
                return;
            }
            try {
                const text = await file.text();
                const parsed = JSON.parse(text);
                if (!Array.isArray(parsed)) {
                    throw new Error('Expected an array of sessions');
                }
                this.sessions = [...parsed, ...this.sessions].map((session, index) => ({
                    id: session.id || `imported_${Date.now()}_${index}`,
                    title: session.title || `Imported Session ${index + 1}`,
                    created: session.created || new Date().toISOString(),
                    lastActive: session.lastActive || new Date().toISOString(),
                    messages: Array.isArray(session.messages) ? session.messages : [],
                }));
                this.persistSessions();
                this.renderSessions();
                this.refreshStats();
                this.showToast('Sessions imported.', 'success');
            } catch (_error) {
                this.showToast('Failed to import sessions.', 'error');
            }
        });
        input.click();
    }

    refreshStats() {
        const allMessages = this.sessions.flatMap((session) => session.messages);
        this.analytics.conversations = allMessages.length;
        this.heroMessageCount.textContent = `${this.messageHistory.length}`;
        this.heroToolCount.textContent = `${this.analytics.toolsExecuted}`;
        this.heroResponseTime.textContent = `${Math.round(this.analytics.avgResponseTime)}ms`;
        this.dashboardElements.totalConversations.textContent = `${this.analytics.conversations}`;
        this.dashboardElements.toolsExecuted.textContent = `${this.analytics.toolsExecuted}`;
        this.dashboardElements.avgResponseTime.textContent = `${Math.round(this.analytics.avgResponseTime)}ms`;
        this.dashboardElements.successRate.textContent = `${Math.max(0, Math.min(100, Math.round(this.analytics.successRate)))}%`;
        this.renderAnalytics();
    }

    recordResponseTime(latencyMs) {
        const current = this.analytics.avgResponseTime;
        if (current === 0) {
            this.analytics.avgResponseTime = latencyMs;
        } else {
            this.analytics.avgResponseTime = (current * 0.7) + (latencyMs * 0.3);
        }
        this.refreshStats();
    }

    recordFailure() {
        this.analytics.successRate = Math.max(60, this.analytics.successRate - 4);
        this.refreshStats();
    }

    pushActivity(title, description, tone = 'system') {
        const item = {
            title,
            description,
            tone,
            timestamp: new Date().toISOString(),
        };
        this.activity.unshift(item);
        this.activity = this.activity.slice(0, this.maxActivity);
        this.renderActivity();
    }

    renderActivity() {
        const iconMap = {
            system: 'S',
            assistant: 'A',
            network: 'N',
            tool: 'T',
            session: 'M',
            thinking: '…',
        };

        const renderTarget = (container, compact = false) => {
            container.innerHTML = '';
            this.activity.forEach((item) => {
                const row = document.createElement('div');
                row.className = compact ? 'mini-feed-item' : 'activity-item';
                row.innerHTML = `
                    <div class="${compact ? 'mini-feed-icon' : 'activity-icon'}">${iconMap[item.tone] || '•'}</div>
                    <div>
                        <div class="activity-title">${this.escapeHtml(item.title)}</div>
                        <div class="${compact ? 'activity-time' : 'activity-time'}">${this.escapeHtml(item.description)}</div>
                    </div>
                `;
                container.appendChild(row);
            });
        };

        renderTarget(this.activityList, false);
        renderTarget(this.miniActivityFeed, true);
    }

    renderToolDeck() {
        const entries = this.toolHistory.slice(0, 4);
        this.toolDeck.innerHTML = '';
        if (entries.length === 0) {
            this.toolDeck.innerHTML = '<div class="tool-deck-item"><strong>No tool executions yet.</strong><p>Run a direct tool or let Oracle call one during a task.</p></div>';
            return;
        }

        entries.forEach((entry) => {
            const row = document.createElement('div');
            row.className = 'tool-deck-item';
            row.innerHTML = `
                <strong>${this.escapeHtml(entry.name)}</strong>
                <p>${this.escapeHtml(this.summarizeResult(entry.result))}</p>
            `;
            this.toolDeck.appendChild(row);
        });
    }

    summarizeResult(result) {
        if (!result || typeof result !== 'object') {
            return 'No result payload.';
        }
        if (result.error) {
            return `Error: ${result.error}`;
        }
        if (result.stdout) {
            return String(result.stdout).slice(0, 120);
        }
        if (result.content) {
            return String(result.content).slice(0, 120);
        }
        if (result.path) {
            return `Path: ${result.path}`;
        }
        return JSON.stringify(result).slice(0, 120);
    }

    renderAnalytics() {
        const timeframe = this.analyticsElements.timeframe.value;
        const base = timeframe === '1h' ? 6 : timeframe === '7d' ? 8 : 7;

        this.renderBarSeries(this.analyticsElements.conversationChart, [
            ['Now', this.messageHistory.length || 1],
            ['Sessions', this.sessions.length],
            ['Total', Math.max(1, this.analytics.conversations)],
        ]);

        const toolDistribution = {};
        this.toolHistory.forEach((entry) => {
            toolDistribution[entry.name] = (toolDistribution[entry.name] || 0) + 1;
        });
        const toolEntries = Object.entries(toolDistribution);
        this.renderBarSeries(this.analyticsElements.toolChart, toolEntries.length ? toolEntries : [['None', 1]]);

        const lineValues = Array.from({ length: base }).map((_item, index) => {
            return Math.max(18, Math.round((this.analytics.avgResponseTime || 120) / 8) + (index * 8));
        });
        this.analyticsElements.performanceChart.innerHTML = '';
        lineValues.forEach((value, index) => {
            const column = document.createElement('div');
            column.className = 'line-column';
            column.style.height = `${Math.min(180, value)}px`;
            column.innerHTML = `<span>${index + 1}</span>`;
            this.analyticsElements.performanceChart.appendChild(column);
        });

        this.analyticsElements.insightsList.innerHTML = '';
        [
            {
                title: 'Session velocity',
                description: `${this.sessions.length} active sessions currently retained in local storage.`,
            },
            {
                title: 'Tool confidence',
                description: `${this.analytics.toolsExecuted} direct tool runs recorded in this browser workspace.`,
            },
            {
                title: 'Runtime profile',
                description: `${Math.round(this.analytics.avgResponseTime)}ms average UI response window with ${Math.round(this.analytics.successRate)}% success.`,
            },
        ].forEach((insight) => {
            const card = document.createElement('div');
            card.className = 'insight-item';
            card.innerHTML = `<div class="insight-title">${insight.title}</div><div class="insight-description">${insight.description}</div>`;
            this.analyticsElements.insightsList.appendChild(card);
        });
    }

    renderBarSeries(container, entries) {
        const max = Math.max(...entries.map((entry) => entry[1]), 1);
        container.innerHTML = '';
        entries.forEach(([label, value]) => {
            const row = document.createElement('div');
            row.className = 'bar-row';
            row.innerHTML = `
                <span class="bar-label">${this.escapeHtml(String(label))}</span>
                <div class="bar-track"><div class="bar-fill" style="width: ${(Number(value) / max) * 100}%"></div></div>
                <span class="bar-value">${this.escapeHtml(String(value))}</span>
            `;
            container.appendChild(row);
        });
    }

    loadHelp() {
        fetch('/api/help/features')
            .then(async (response) => {
                if (!response.ok) {
                    throw new Error('Help unavailable');
                }
                return response.json();
            })
            .then((payload) => {
                this.helpFeatures = payload;
                this.renderHelp();
            })
            .catch(() => {
                this.renderHelpFallback();
            });
    }

    renderHelp() {
        if (!this.helpFeatures) {
            this.renderHelpFallback();
            return;
        }

        this.helpGrid.innerHTML = '';
        Object.values(this.helpFeatures).forEach((section) => {
            const card = document.createElement('article');
            card.className = 'help-card';
            const listItems = (section.capabilities || section.examples || []).map((item) => `<li>${this.escapeHtml(item)}</li>`).join('');
            card.innerHTML = `
                <h4>${this.escapeHtml(section.title)}</h4>
                <p>${this.escapeHtml(section.description || '')}</p>
                ${listItems ? `<ul>${listItems}</ul>` : ''}
            `;
            this.helpGrid.appendChild(card);
        });
    }

    renderHelpFallback() {
        this.helpGrid.innerHTML = `
            <article class="help-card">
                <h4>Mission workflow</h4>
                <p>Type a task, let Oracle reason, and use the tool deck when you need direct control.</p>
            </article>
            <article class="help-card">
                <h4>Quick controls</h4>
                <p>Use the command palette, start named sessions, and capture tool results without leaving the main deck.</p>
            </article>
            <article class="help-card">
                <h4>Protected settings</h4>
                <p>When `ORACLE_API_KEY` is configured, enter the key in Settings to unlock protected reads and writes.</p>
            </article>
            <article class="help-card">
                <h4>Telemetry</h4>
                <p>Use Pulse and Analytics to understand what the interface and agent are doing in real time.</p>
            </article>
        `;
    }

    loadSettings() {
        const apiKey = this.getApiKey();
        if (!apiKey) {
            this.settings = null;
            this.settingsElements.note.textContent = 'Protected settings are locked until you provide the GUI API key.';
            this.updateSettingsDisplays();
            return;
        }

        fetch('/api/settings', { headers: this.buildApiHeaders() })
            .then(async (response) => {
                if (!response.ok) {
                    throw new Error('Settings fetch failed');
                }
                return response.json();
            })
            .then((settings) => {
                this.settings = settings;
                this.applySettings(settings);
                this.settingsElements.note.textContent = 'Settings are unlocked and ready to save.';
            })
            .catch(() => {
                this.settingsElements.note.textContent = 'Settings could not be loaded. Verify the API key and backend state.';
            });
    }

    applySettings(settings) {
        this.settingsElements.modelSelect.value = settings.model_id || 'gemini-2.0-flash-exp';
        this.settingsElements.maxTurns.value = settings.max_turns || 20;
        this.settingsElements.temperature.value = Math.round((settings.temperature || 0.7) * 100);
        this.settingsElements.shellTimeout.value = settings.shell_timeout || 60;
        this.settingsElements.httpTimeout.value = settings.http_timeout || 15;
        this.settingsElements.gcsBucket.value = settings.gcs_bucket || '';
        this.settingsElements.enableGcsBackup.checked = Boolean(settings.gcs_enabled);
        this.settingsElements.logLevel.value = settings.log_level || 'INFO';
        this.updateSettingsDisplays();
    }

    updateSettingsDisplays() {
        this.settingsElements.maxTurnsDisplay.textContent = `${this.settingsElements.maxTurns.value} turns`;
        this.settingsElements.temperatureDisplay.textContent = `${this.settingsElements.temperature.value}%`;
    }

    saveSettings() {
        this.setApiKey(this.settingsElements.guiApiKey.value);
        const payload = {
            model_id: this.settingsElements.modelSelect.value,
            max_turns: Number(this.settingsElements.maxTurns.value),
            temperature: Number(this.settingsElements.temperature.value) / 100,
            shell_timeout: Number(this.settingsElements.shellTimeout.value),
            http_timeout: Number(this.settingsElements.httpTimeout.value),
            gcs_bucket: this.settingsElements.gcsBucket.value.trim(),
            log_level: this.settingsElements.logLevel.value,
        };

        fetch('/api/config', {
            method: 'POST',
            headers: this.buildApiHeaders(true),
            body: JSON.stringify(payload),
        })
            .then(async (response) => {
                const data = await response.json();
                if (!response.ok || !data.success) {
                    throw new Error(data.error || 'Unable to save settings');
                }
                this.showToast('Settings saved.', 'success');
                this.reconnectSocket();
                this.loadStatus();
            })
            .catch((error) => {
                this.showToast(error.message || 'Failed to save settings.', 'error');
            });
    }

    resetSettings() {
        this.setApiKey(this.settingsElements.guiApiKey.value);
        fetch('/api/settings/reset', {
            method: 'POST',
            headers: this.buildApiHeaders(),
        })
            .then(async (response) => {
                const data = await response.json();
                if (!response.ok || !data.success) {
                    throw new Error(data.error || 'Reset failed');
                }
                this.showToast('Settings reset.', 'success');
                this.loadSettings();
                this.loadStatus();
            })
            .catch((error) => this.showToast(error.message || 'Failed to reset settings.', 'error'));
    }

    exportSettings() {
        this.setApiKey(this.settingsElements.guiApiKey.value);
        fetch('/api/settings/export', {
            headers: this.buildApiHeaders(),
        })
            .then(async (response) => {
                if (!response.ok) {
                    const payload = await response.json();
                    throw new Error(payload.error || 'Export failed');
                }
                return response.json();
            })
            .then((payload) => {
                this.downloadJson(payload, `oracle_gui_config_${new Date().toISOString().slice(0, 10)}.json`);
                this.showToast('Configuration exported.', 'success');
            })
            .catch((error) => this.showToast(error.message || 'Failed to export settings.', 'error'));
    }

    triggerBackup() {
        if (!this.socket) {
            return;
        }
        this.socket.emit('backup_to_gcs');
    }

    clearHistory() {
        if (!this.socket) {
            return;
        }
        this.socket.emit('clear_history', { session_id: this.sessionId });
    }

    clearCurrentSessionMessages() {
        const session = this.getCurrentSession();
        session.messages = [];
        session.lastActive = new Date().toISOString();
        this.messageHistory = [];
        this.persistSessions();
        this.renderTranscript();
        this.renderSessions();
        this.refreshStats();
    }

    openToolPanel(toolName) {
        const schema = this.toolSchemas[toolName];
        if (!schema) {
            return;
        }

        this.toolPanelTitle.textContent = this.titleize(toolName.replace(/_/g, ' '));
        this.toolPanelContent.innerHTML = '';

        const form = document.createElement('form');
        form.className = 'tool-form';

        schema.forEach((field) => {
            const wrapper = document.createElement('label');
            wrapper.className = 'field-label';
            wrapper.textContent = field.label;
            let input;
            if (field.type === 'textarea') {
                input = document.createElement('textarea');
                input.rows = 4;
            } else if (field.type === 'select') {
                input = document.createElement('select');
                field.options.forEach((option) => {
                    const element = document.createElement('option');
                    element.value = option;
                    element.textContent = option;
                    input.appendChild(element);
                });
            } else {
                input = document.createElement('input');
                input.type = field.type;
            }
            input.name = field.name;
            input.required = Boolean(field.required);
            if (field.placeholder) {
                input.placeholder = field.placeholder;
            }
            wrapper.appendChild(input);
            form.appendChild(wrapper);
        });

        const actions = document.createElement('div');
        actions.className = 'button-stack horizontal';
        actions.innerHTML = `
            <button class="primary-button" type="submit">Run tool</button>
            <button class="ghost-button" type="button" id="tool-clear-button">Clear</button>
        `;
        form.appendChild(actions);

        const result = document.createElement('div');
        result.className = 'tool-result';
        result.innerHTML = '<pre>Waiting for execution…</pre>';

        form.addEventListener('submit', (event) => {
            event.preventDefault();
            const values = {};
            schema.forEach((field) => {
                const element = form.elements[field.name];
                values[field.name] = element.value;
            });

            if (toolName === 'http_fetch' && values.headers) {
                try {
                    values.headers = JSON.parse(values.headers);
                } catch (_error) {
                    this.showToast('Headers must be valid JSON.', 'error');
                    return;
                }
            }

            if (toolName === 'file_system_ops' && values.operation !== 'write') {
                delete values.content;
            }

            this.socket.emit('execute_tool', { tool: toolName, args: values });
            result.innerHTML = '<pre>Tool request sent…</pre>';
        });

        actions.querySelector('#tool-clear-button').addEventListener('click', () => {
            form.reset();
            result.innerHTML = '<pre>Waiting for execution…</pre>';
        });

        this.toolPanelContent.appendChild(form);
        this.toolPanelContent.appendChild(result);
        this.toolPanel.classList.add('open');
        this.toolPanel.setAttribute('aria-hidden', 'false');
    }

    renderToolResult(toolName, payload) {
        if (!this.toolPanel.classList.contains('open')) {
            return;
        }
        const result = this.toolPanelContent.querySelector('.tool-result');
        if (!result) {
            return;
        }
        result.innerHTML = `<pre>${this.escapeHtml(JSON.stringify({ tool: toolName, ...payload }, null, 2))}</pre>`;
    }

    closeToolPanel() {
        this.toolPanel.classList.remove('open');
        this.toolPanel.setAttribute('aria-hidden', 'true');
    }

    showLoading() {
        this.loadingOverlay.hidden = false;
    }

    hideLoading() {
        this.loadingOverlay.hidden = true;
    }

    showToast(message, tone = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${tone}`;
        toast.textContent = message;
        this.toastContainer.appendChild(toast);
        window.setTimeout(() => toast.remove(), 2800);
    }

    downloadJson(payload, filename) {
        const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = filename;
        anchor.click();
        URL.revokeObjectURL(url);
    }

    titleize(value) {
        return value.replace(/\b\w/g, (char) => char.toUpperCase());
    }

    escapeHtml(value) {
        return String(value)
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    }
}

window.addEventListener('DOMContentLoaded', () => {
    window.oracleGui = new OracleGUI();
});
