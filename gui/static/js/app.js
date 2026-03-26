/**
 * Oracle Agent GUI - Frontend Application
 * Handles WebSocket communication, UI interactions, and real-time updates
 */

class OracleGUI {
    constructor() {
        this.socket = null;
        this.sessionId = 'default';
        this.messageHistory = [];
        this.isConnected = false;
        this.isThinking = false;
        this.currentView = 'chat';
        this.sessions = [];
        this.analytics = {
            conversations: 0,
            toolsExecuted: 0,
            avgResponseTime: 0,
            successRate: 100
        };
        
        this.initializeElements();
        this.initializeSocket();
        this.bindEvents();
        this.loadStatus();
        this.initializeAdvancedFeatures();
    }

    initializeAdvancedFeatures() {
        // Initialize dashboard data
        this.updateDashboardStats();
        
        // Initialize sessions
        this.loadSessions();
        
        // Initialize analytics
        this.initializeAnalytics();
        
        // Add keyboard shortcuts
        this.setupKeyboardShortcuts();
        
        // Initialize search functionality
        this.setupSearch();
        
        // Start real-time updates
        this.startRealTimeUpdates();
    }

    initializeElements() {
        // Core elements
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('btn-send');
        this.messagesContainer = document.getElementById('messages');
        this.loadingOverlay = document.getElementById('loading-overlay');
        this.toastContainer = document.getElementById('toast-container');
        this.toolPanel = document.getElementById('tool-panel');
        
        // Status elements
        this.statusDot = document.querySelector('.status-dot');
        this.statusText = document.querySelector('.status-text');
        this.configModel = document.getElementById('config-model');
        this.configGcs = document.getElementById('config-gcs');
        this.configTurns = document.getElementById('config-turns');
        this.sessionIdDisplay = document.getElementById('session-id');
        
        // Buttons
        this.backupBtn = document.getElementById('btn-backup');
        this.clearBtn = document.getElementById('btn-clear');
        this.closePanelBtn = document.getElementById('btn-close-panel');
        
        // Navigation elements
        this.navItems = document.querySelectorAll('.nav-item');
        this.viewContainers = document.querySelectorAll('.view-container');
        
        // Dashboard elements
        this.dashboardElements = {
            totalConversations: document.getElementById('total-conversations'),
            toolsExecuted: document.getElementById('tools-executed'),
            avgResponseTime: document.getElementById('avg-response-time'),
            successRate: document.getElementById('success-rate'),
            activityList: document.getElementById('activity-list'),
            statusModel: document.getElementById('status-model'),
            statusDb: document.getElementById('status-db'),
            statusCloud: document.getElementById('status-cloud'),
            statusMemory: document.getElementById('status-memory')
        };
        
        // Sessions elements
        this.sessionsElements = {
            sessionsList: document.getElementById('sessions-list'),
            newSessionBtn: document.getElementById('btn-new-session'),
            exportBtn: document.getElementById('btn-export-sessions'),
            importBtn: document.getElementById('btn-import-sessions')
        };
        
        // Analytics elements
        this.analyticsElements = {
            timeframe: document.getElementById('analytics-timeframe'),
            metric: document.getElementById('analytics-metric'),
            conversationChart: document.getElementById('conversation-chart'),
            toolChart: document.getElementById('tool-chart'),
            performanceChart: document.getElementById('performance-chart'),
            insightsList: document.getElementById('insights-list')
        };
        
        // Settings elements
        this.settingsElements = {
            modelSelect: document.getElementById('model-select'),
            maxTurns: document.getElementById('max-turns'),
            temperature: document.getElementById('temperature'),
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
            exportBtn: document.getElementById('export-settings')
        };
        
        // Search elements
        this.searchInput = document.getElementById('search-input');
        this.searchResults = document.getElementById('search-results');
    }

    initializeSocket() {
        // Connect to Socket.IO server
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Connected to Oracle Agent server');
            this.isConnected = true;
            this.showToast('Connected to Oracle Agent', 'success');
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.isConnected = false;
            this.updateStatus('disconnected');
            this.showToast('Disconnected from server', 'warning');
        });
        
        this.socket.on('agent_status', (data) => {
            if (data.initialized) {
                this.updateStatus('ready', data);
            } else {
                this.updateStatus('error');
            }
        });
        
        this.socket.on('message', (data) => {
            this.hideLoading();
            this.addMessage(data.content, 'assistant', data.timestamp);
            this.isThinking = false;
            this.updateSendButton();
        });
        
        this.socket.on('thinking', () => {
            this.showLoading();
            this.isThinking = true;
            this.updateSendButton();
        });
        
        this.socket.on('error', (data) => {
            this.hideLoading();
            this.showToast(data.message, 'error');
            this.isThinking = false;
            this.updateSendButton();
        });
        
        this.socket.on('tool_result', (data) => {
            this.displayToolResult(data);
        });
        
        this.socket.on('backup_result', (data) => {
            if (data.success) {
                this.showToast(`Backup successful: ${data.gcs_uri || 'local'}`, 'success');
            } else {
                this.showToast(`Backup failed: ${data.error}`, 'error');
            }
        });
        
        this.socket.on('history_cleared', () => {
            this.clearMessages();
            this.showToast('History cleared', 'success');
        });
    }

    bindEvents() {
        // Message input
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
            
            // Auto-resize textarea
            setTimeout(() => {
                this.messageInput.style.height = 'auto';
                this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
            }, 0);
        });
        
        this.messageInput.addEventListener('input', () => {
            this.updateSendButton();
        });
        
        // Send button
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Sidebar buttons
        this.backupBtn.addEventListener('click', () => this.triggerBackup());
        this.clearBtn.addEventListener('click', () => this.clearHistory());
        
        // Tool panel
        this.closePanelBtn.addEventListener('click', () => this.closeToolPanel());
        
        // Tool items
        document.querySelectorAll('.tool-item').forEach(item => {
            item.addEventListener('click', () => {
                const tool = item.dataset.tool;
                this.openToolPanel(tool);
            });
        });
        
        // Navigation items
        this.navItems.forEach(item => {
            item.addEventListener('click', () => {
                const view = item.dataset.view;
                this.switchView(view);
            });
        });
        
        // Dashboard events
        this.bindDashboardEvents();
        
        // Sessions events
        this.bindSessionsEvents();
        
        // Analytics events
        this.bindAnalyticsEvents();
        
        // Settings controls
        this.bindSettingsEvents();
        
        // Focus input on load
        this.messageInput.focus();
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === '/') {
                e.preventDefault();
                this.showKeyboardShortcuts();
            }
            if (e.key === 'Escape') {
                this.closeToolPanel();
            }
        });
    }
    
    bindDashboardEvents() {
        // Dashboard refresh button
        const refreshBtn = document.getElementById('btn-refresh-dashboard');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.updateDashboardStats();
                this.showToast('Dashboard refreshed', 'success');
            });
        }
    }
    
    bindSessionsEvents() {
        // New session button
        if (this.sessionsElements.newSessionBtn) {
            this.sessionsElements.newSessionBtn.addEventListener('click', () => {
                this.createNewSession();
            });
        }
        
        // Export sessions button
        if (this.sessionsElements.exportBtn) {
            this.sessionsElements.exportBtn.addEventListener('click', () => {
                this.exportSessions();
            });
        }
        
        // Import sessions button
        if (this.sessionsElements.importBtn) {
            this.sessionsElements.importBtn.addEventListener('click', () => {
                this.importSessions();
            });
        }
    }
    
    bindAnalyticsEvents() {
        // Analytics timeframe and metric filters are handled in initializeAnalytics()
        
        // Export analytics button
        const exportAnalyticsBtn = document.getElementById('btn-export-analytics');
        if (exportAnalyticsBtn) {
            exportAnalyticsBtn.addEventListener('click', () => {
                this.exportAnalytics();
            });
        }
    }
    
    exportAnalytics() {
        const analyticsData = {
            timestamp: new Date().toISOString(),
            stats: this.analytics,
            sessions: this.sessions.length,
            timeframe: this.analyticsElements.timeframe?.value || '24h'
        };
        
        const dataStr = JSON.stringify(analyticsData, null, 2);
        const dataBlob = new Blob([dataStr], {type: 'application/json'});
        const url = URL.createObjectURL(dataBlob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `oracle_analytics_${new Date().toISOString().split('T')[0]}.json`;
        link.click();
        
        URL.revokeObjectURL(url);
        this.showToast('Analytics exported', 'success');
    }

    // Advanced Features Methods
    
    updateDashboardStats() {
        // Update dashboard statistics
        if (this.dashboardElements.totalConversations) {
            this.dashboardElements.totalConversations.textContent = this.analytics.conversations;
        }
        if (this.dashboardElements.toolsExecuted) {
            this.dashboardElements.toolsExecuted.textContent = this.analytics.toolsExecuted;
        }
        if (this.dashboardElements.avgResponseTime) {
            this.dashboardElements.avgResponseTime.textContent = `${this.analytics.avgResponseTime}ms`;
        }
        if (this.dashboardElements.successRate) {
            this.dashboardElements.successRate.textContent = `${this.analytics.successRate}%`;
        }
        
        // Update system status
        this.updateSystemStatus();
        
        // Add recent activity
        this.addActivityItem('🚀', 'Oracle Agent started', 'Just now');
    }
    
    updateSystemStatus() {
        if (this.dashboardElements.statusModel) {
            this.dashboardElements.statusModel.textContent = 'Connected';
        }
        if (this.dashboardElements.statusDb) {
            this.dashboardElements.statusDb.textContent = 'Healthy';
        }
        if (this.dashboardElements.statusCloud) {
            this.dashboardElements.statusCloud.textContent = 'Ready';
        }
        if (this.dashboardElements.statusMemory) {
            this.dashboardElements.statusMemory.textContent = 'Normal';
        }
    }
    
    addActivityItem(icon, title, time) {
        if (!this.dashboardElements.activityList) return;
        
        const activityItem = document.createElement('div');
        activityItem.className = 'activity-item';
        activityItem.innerHTML = `
            <div class="activity-icon">${icon}</div>
            <div class="activity-content">
                <div class="activity-title">${title}</div>
                <div class="activity-time">${time}</div>
            </div>
        `;
        
        this.dashboardElements.activityList.insertBefore(activityItem, this.dashboardElements.activityList.firstChild);
        
        // Keep only last 10 activities
        const items = this.dashboardElements.activityList.querySelectorAll('.activity-item');
        if (items.length > 10) {
            items[items.length - 1].remove();
        }
    }
    
    loadSessions() {
        // Load sessions from localStorage or API
        const savedSessions = localStorage.getItem('oracle_sessions');
        if (savedSessions) {
            this.sessions = JSON.parse(savedSessions);
        } else {
            // Create default session
            this.sessions = [{
                id: 'default',
                title: 'Default Session',
                created: new Date().toISOString(),
                messages: [],
                lastActive: new Date().toISOString()
            }];
        }
        
        this.renderSessions();
    }
    
    renderSessions() {
        if (!this.sessionsElements.sessionsList) return;
        
        this.sessionsElements.sessionsList.innerHTML = '';
        
        this.sessions.forEach(session => {
            const sessionCard = document.createElement('div');
            sessionCard.className = 'session-card';
            sessionCard.innerHTML = `
                <div class="session-header">
                    <div class="session-title">${session.title}</div>
                    <div class="session-actions">
                        <button class="btn btn-secondary btn-sm" onclick="oracleGUI.loadSession('${session.id}')">Load</button>
                        <button class="btn btn-secondary btn-sm" onclick="oracleGUI.deleteSession('${session.id}')">Delete</button>
                    </div>
                </div>
                <div class="session-meta">
                    <span>Created: ${new Date(session.created).toLocaleDateString()}</span>
                    <span>Messages: ${session.messages?.length || 0}</span>
                </div>
                <div class="session-preview">
                    ${session.messages?.[0]?.content?.substring(0, 100) || 'No messages yet'}...
                </div>
            `;
            
            this.sessionsElements.sessionsList.appendChild(sessionCard);
        });
    }
    
    createNewSession() {
        const sessionName = prompt('Enter session name:');
        if (!sessionName) return;
        
        const newSession = {
            id: 'session_' + Date.now(),
            title: sessionName,
            created: new Date().toISOString(),
            messages: [],
            lastActive: new Date().toISOString()
        };
        
        this.sessions.push(newSession);
        this.saveSessions();
        this.renderSessions();
        this.loadSession(newSession.id);
        
        this.showToast('New session created', 'success');
    }
    
    loadSession(sessionId) {
        const session = this.sessions.find(s => s.id === sessionId);
        if (!session) return;
        
        this.sessionId = sessionId;
        this.sessionIdDisplay.textContent = session.title;
        this.messageHistory = session.messages || [];
        
        // Clear and reload messages
        this.messagesContainer.innerHTML = '';
        this.messageHistory.forEach(msg => {
            this.addMessage(msg.content, msg.role, msg.timestamp, false);
        });
        
        this.switchView('chat');
        this.showToast('Session loaded', 'success');
    }
    
    deleteSession(sessionId) {
        if (!confirm('Are you sure you want to delete this session?')) return;
        
        this.sessions = this.sessions.filter(s => s.id !== sessionId);
        this.saveSessions();
        this.renderSessions();
        
        if (this.sessionId === sessionId) {
            this.loadSession('default');
        }
        
        this.showToast('Session deleted', 'success');
    }
    
    saveSessions() {
        localStorage.setItem('oracle_sessions', JSON.stringify(this.sessions));
    }
    
    exportSessions() {
        const dataStr = JSON.stringify(this.sessions, null, 2);
        const dataBlob = new Blob([dataStr], {type: 'application/json'});
        const url = URL.createObjectURL(dataBlob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `oracle_sessions_${new Date().toISOString().split('T')[0]}.json`;
        link.click();
        
        URL.revokeObjectURL(url);
        this.showToast('Sessions exported', 'success');
    }
    
    importSessions() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const imported = JSON.parse(e.target.result);
                    if (Array.isArray(imported)) {
                        this.sessions = [...this.sessions, ...imported];
                        this.saveSessions();
                        this.renderSessions();
                        this.showToast('Sessions imported', 'success');
                    } else {
                        throw new Error('Invalid format');
                    }
                } catch (error) {
                    this.showToast('Failed to import sessions', 'error');
                }
            };
            reader.readAsText(file);
        };
        
        input.click();
    }
    
    initializeAnalytics() {
        // Initialize charts (placeholder for Chart.js integration)
        this.setupCharts();
        
        // Generate insights
        this.generateInsights();
        
        // Setup analytics filters
        if (this.analyticsElements.timeframe) {
            this.analyticsElements.timeframe.addEventListener('change', () => {
                this.updateAnalytics();
            });
        }
        
        if (this.analyticsElements.metric) {
            this.analyticsElements.metric.addEventListener('change', () => {
                this.updateAnalytics();
            });
        }
    }
    
    setupCharts() {
        // Placeholder for Chart.js integration
        // In a real implementation, you would initialize Chart.js charts here
        console.log('Charts would be initialized here with Chart.js');
    }
    
    generateInsights() {
        const insights = [
            {
                icon: '📈',
                title: 'High Engagement',
                description: 'Your conversations have increased by 25% this week'
            },
            {
                icon: '⚡',
                title: 'Fast Response',
                description: 'Average response time is under 500ms'
            },
            {
                icon: '🎯',
                title: 'Tool Efficiency',
                description: 'Shell commands are your most used tool'
            }
        ];
        
        if (!this.analyticsElements.insightsList) return;
        
        this.analyticsElements.insightsList.innerHTML = '';
        
        insights.forEach(insight => {
            const insightItem = document.createElement('div');
            insightItem.className = 'insight-item';
            insightItem.innerHTML = `
                <div class="insight-icon">${insight.icon}</div>
                <div class="insight-content">
                    <div class="insight-title">${insight.title}</div>
                    <div class="insight-description">${insight.description}</div>
                </div>
            `;
            
            this.analyticsElements.insightsList.appendChild(insightItem);
        });
    }
    
    updateAnalytics() {
        // Update analytics based on selected filters
        const timeframe = this.analyticsElements.timeframe?.value || '24h';
        const metric = this.analyticsElements.metric?.value || 'all';
        
        console.log(`Updating analytics for ${timeframe} and ${metric}`);
        // In a real implementation, this would fetch data and update charts
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K for quick search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.showQuickSearch();
            }
            
            // Ctrl/Cmd + N for new session
            if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
                e.preventDefault();
                this.createNewSession();
            }
            
            // Ctrl/Cmd + D for dashboard
            if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
                e.preventDefault();
                this.switchView('dashboard');
            }
            
            // Ctrl/Cmd + S for settings
            if ((e.ctrlKey || e.metaKey) && e.key === ',') {
                e.preventDefault();
                this.switchView('settings');
            }
            
            // Ctrl/Cmd + / for help
            if ((e.ctrlKey || e.metaKey) && e.key === '/') {
                e.preventDefault();
                this.showKeyboardShortcuts();
            }
            
            // Escape to close panels
            if (e.key === 'Escape') {
                this.closeToolPanel();
                this.hideQuickSearch();
            }
        });
    }
    
    setupSearch() {
        // Add search input to header if it doesn't exist
        if (!this.searchInput) {
            const searchContainer = document.createElement('div');
            searchContainer.className = 'search-container';
            searchContainer.innerHTML = `
                <input type="text" id="search-input" placeholder="Search conversations, tools, settings..." />
                <div id="search-results" class="search-results" style="display: none;"></div>
            `;
            
            // Add to header (implementation depends on your layout)
            document.querySelector('.chat-header')?.prepend(searchContainer);
            this.searchInput = document.getElementById('search-input');
            this.searchResults = document.getElementById('search-results');
        }
        
        if (this.searchInput) {
            this.searchInput.addEventListener('input', (e) => {
                this.performSearch(e.target.value);
            });
        }
    }
    
    performSearch(query) {
        if (!query.trim()) {
            this.hideSearchResults();
            return;
        }
        
        const results = this.searchAcrossViews(query);
        this.displaySearchResults(results);
    }
    
    searchAcrossViews(query) {
        const results = [];
        const lowerQuery = query.toLowerCase();
        
        // Search in message history
        this.messageHistory.forEach((msg, index) => {
            if (msg.content.toLowerCase().includes(lowerQuery)) {
                results.push({
                    type: 'message',
                    title: `Message ${index + 1}`,
                    content: msg.content.substring(0, 100) + '...',
                    action: () => this.scrollToMessage(index)
                });
            }
        });
        
        // Search in settings
        const settingsOptions = [
            { key: 'model', label: 'AI Model' },
            { key: 'maxTurns', label: 'Max Turns' },
            { key: 'temperature', label: 'Temperature' }
        ];
        
        settingsOptions.forEach(option => {
            if (option.label.toLowerCase().includes(lowerQuery)) {
                results.push({
                    type: 'setting',
                    title: option.label,
                    content: `Go to ${option.label} settings`,
                    action: () => this.switchView('settings')
                });
            }
        });
        
        return results;
    }
    
    displaySearchResults(results) {
        if (!this.searchResults) return;
        
        this.searchResults.innerHTML = '';
        
        if (results.length === 0) {
            this.searchResults.innerHTML = '<div class="search-no-results">No results found</div>';
        } else {
            results.forEach(result => {
                const resultItem = document.createElement('div');
                resultItem.className = 'search-result-item';
                resultItem.innerHTML = `
                    <div class="search-result-title">${result.title}</div>
                    <div class="search-result-content">${result.content}</div>
                `;
                resultItem.addEventListener('click', result.action);
                this.searchResults.appendChild(resultItem);
            });
        }
        
        this.searchResults.style.display = 'block';
    }
    
    hideSearchResults() {
        if (this.searchResults) {
            this.searchResults.style.display = 'none';
        }
    }
    
    showQuickSearch() {
        if (this.searchInput) {
            this.searchInput.focus();
            this.searchInput.select();
        }
    }
    
    hideQuickSearch() {
        this.hideSearchResults();
        if (this.searchInput) {
            this.searchInput.value = '';
            this.searchInput.blur();
        }
    }
    
    showKeyboardShortcuts() {
        const shortcuts = [
            { key: 'Ctrl/Cmd + K', description: 'Quick search' },
            { key: 'Ctrl/Cmd + N', description: 'New session' },
            { key: 'Ctrl/Cmd + D', description: 'Dashboard' },
            { key: 'Ctrl/Cmd + ,', description: 'Settings' },
            { key: 'Ctrl/Cmd + /', description: 'Show shortcuts' },
            { key: 'Escape', description: 'Close panels' },
            { key: 'Enter', description: 'Send message' },
            { key: 'Shift + Enter', description: 'New line' }
        ];
        
        let shortcutsHtml = '<div class="shortcuts-modal"><h3>Keyboard Shortcuts</h3><div class="shortcuts-list">';
        
        shortcuts.forEach(shortcut => {
            shortcutsHtml += `
                <div class="shortcut-item">
                    <kbd>${shortcut.key}</kbd>
                    <span>${shortcut.description}</span>
                </div>
            `;
        });
        
        shortcutsHtml += '</div></div>';
        
        // Show modal (implementation depends on your modal system)
        this.showToast('Keyboard shortcuts: ' + shortcuts.map(s => s.key).join(', '), 'info');
    }
    
    startRealTimeUpdates() {
        // Update dashboard stats every 30 seconds
        setInterval(() => {
            this.updateDashboardStats();
        }, 30000);
        
        // Update system status every 10 seconds
        setInterval(() => {
            this.updateSystemStatus();
        }, 10000);
    }
    
    switchView(viewName) {
        // Update navigation
        this.navItems.forEach(item => {
            item.classList.remove('active');
            if (item.dataset.view === viewName) {
                item.classList.add('active');
            }
        });
        
        // Update views
        this.viewContainers.forEach(container => {
            container.classList.remove('active');
        });
        
        const targetView = document.getElementById(`${viewName}-view`);
        if (targetView) {
            targetView.classList.add('active');
        }
        
        this.currentView = viewName;
        
        // View-specific initialization
        if (viewName === 'dashboard') {
            this.updateDashboardStats();
        } else if (viewName === 'sessions') {
            this.renderSessions();
        } else if (viewName === 'analytics') {
            this.updateAnalytics();
        }
    }
    
    scrollToMessage(index) {
        const messages = this.messagesContainer.querySelectorAll('.message');
        if (messages[index]) {
            messages[index].scrollIntoView({ behavior: 'smooth' });
            messages[index].classList.add('highlighted');
            setTimeout(() => {
                messages[index].classList.remove('highlighted');
            }, 2000);
        }
        
        this.switchView('chat');
    }

    async loadStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            if (data.initialized) {
                this.updateStatus('ready', data);
            } else {
                this.updateStatus('error');
                this.showToast(data.error || 'Agent not initialized', 'error');
            }
        } catch (error) {
            console.error('Failed to load status:', error);
            this.updateStatus('error');
        }
    }

    updateStatus(status, data = null) {
        this.statusDot.className = 'status-dot';
        
        switch (status) {
            case 'ready':
                this.statusDot.classList.add('ready');
                this.statusText.textContent = 'Ready';
                
                if (data) {
                    this.configModel.textContent = data.model_id || '-';
                    this.configGcs.textContent = data.gcs_enabled ? 'Enabled' : 'Disabled';
                    this.configTurns.textContent = data.max_turns || '-';
                }
                break;
                
            case 'error':
                this.statusDot.classList.add('error');
                this.statusText.textContent = 'Error';
                break;
                
            case 'disconnected':
                this.statusDot.classList.add('error');
                this.statusText.textContent = 'Disconnected';
                break;
                
            default:
                this.statusText.textContent = 'Initializing...';
        }
    }

    sendMessage() {
        const message = this.messageInput.value.trim();
        
        if (!message || this.isThinking) return;
        
        // Add user message to UI
        this.addMessage(message, 'user', new Date().toISOString());
        
        // Clear input
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';
        
        // Send to server
        this.socket.emit('send_message', {
            message: message,
            session_id: this.sessionId
        });
        
        this.isThinking = true;
        this.updateSendButton();
    }

    addMessage(content, role, timestamp) {
        // Remove welcome message if present
        const welcome = this.messagesContainer.querySelector('.welcome-message');
        if (welcome) {
            welcome.remove();
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = role === 'user' ? '👤' : '🤖';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Parse markdown for assistant messages
        if (role === 'assistant') {
            contentDiv.innerHTML = marked.parse(content);
            // Apply syntax highlighting
            contentDiv.querySelectorAll('pre code').forEach(block => {
                hljs.highlightElement(block);
            });
        } else {
            contentDiv.textContent = content;
        }
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = this.formatTime(timestamp);
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
        
        this.messagesContainer.appendChild(messageDiv);
        this.messagesContainer.appendChild(timeDiv);
        
        // Scroll to bottom
        this.scrollToBottom();
        
        // Store in history
        this.messageHistory.push({ role, content, timestamp });
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    updateSendButton() {
        const hasText = this.messageInput.value.trim().length > 0;
        this.sendButton.disabled = !hasText || this.isThinking;
    }

    showLoading() {
        this.loadingOverlay.classList.add('visible');
    }

    hideLoading() {
        this.loadingOverlay.classList.remove('visible');
    }

    showToast(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        // Icon based on type
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        
        toast.innerHTML = `
            <span style="font-size: 1.2rem;">${icons[type]}</span>
            <span>${message}</span>
        `;
        
        this.toastContainer.appendChild(toast);
        
        // Remove after duration
        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    triggerBackup() {
        this.socket.emit('backup_to_gcs');
        this.showToast('Starting backup...', 'info');
    }

    clearHistory() {
        if (confirm('Are you sure you want to clear the conversation history?')) {
            this.socket.emit('clear_history', { session_id: this.sessionId });
        }
    }

    clearMessages() {
        this.messagesContainer.innerHTML = '';
        this.messageHistory = [];
        
        // Add welcome message back
        const welcome = document.createElement('div');
        welcome.className = 'welcome-message';
        welcome.innerHTML = `
            <h1>👋 Welcome to Oracle Agent</h1>
            <p>Your production-grade AI assistant with:</p>
            <ul>
                <li>🔧 Sandboxed tool execution (shell, files, HTTP, vision)</li>
                <li>💾 Persistent conversation history</li>
                <li>☁️ Cloud backup integration</li>
                <li>🔄 Multi-LLM support with automatic failover</li>
            </ul>
            <p class="hint">Type a message below to start the conversation.</p>
        `;
        this.messagesContainer.appendChild(welcome);
    }

    openToolPanel(tool) {
        const content = document.getElementById('tool-panel-content');
        
        const toolForms = {
            shell_execute: {
                title: 'Shell Execute',
                fields: [
                    { name: 'command', label: 'Command', type: 'textarea', placeholder: 'Enter shell command...' }
                ]
            },
            file_system_ops: {
                title: 'File System Operations',
                fields: [
                    { name: 'operation', label: 'Operation', type: 'select', options: ['read', 'write', 'list', 'delete'] },
                    { name: 'path', label: 'Path', type: 'text', placeholder: 'Relative path' },
                    { name: 'content', label: 'Content (write only)', type: 'textarea', placeholder: 'File content...', optional: true }
                ]
            },
            http_fetch: {
                title: 'HTTP Fetch',
                fields: [
                    { name: 'url', label: 'URL', type: 'text', placeholder: 'https://api.example.com/data' },
                    { name: 'method', label: 'Method', type: 'select', options: ['GET', 'POST', 'PUT', 'DELETE'] },
                    { name: 'headers', label: 'Headers (JSON)', type: 'textarea', placeholder: '{"Authorization": "Bearer token"}', optional: true }
                ]
            },
            vision_capture: {
                title: 'Vision Capture',
                fields: [
                    { name: 'reason', label: 'Reason', type: 'text', placeholder: 'Why are you capturing the screen?' }
                ]
            }
        };
        
        const formConfig = toolForms[tool];
        if (!formConfig) return;
        
        let formHTML = `<form class="tool-form" data-tool="${tool}">`;
        formHTML += `<h4>${formConfig.title}</h4>`;
        
        formConfig.fields.forEach(field => {
            formHTML += `
                <div class="form-group">
                    <label>${field.label}${field.optional ? '' : ' *'}</label>
            `;
            
            if (field.type === 'select') {
                formHTML += `<select name="${field.name}">`;
                field.options.forEach(opt => {
                    formHTML += `<option value="${opt.toLowerCase()}">${opt}</option>`;
                });
                formHTML += `</select>`;
            } else if (field.type === 'textarea') {
                formHTML += `<textarea name="${field.name}" placeholder="${field.placeholder}" ${field.optional ? '' : 'required'}></textarea>`;
            } else {
                formHTML += `<input type="${field.type}" name="${field.name}" placeholder="${field.placeholder}" ${field.optional ? '' : 'required'}>`;
            }
            
            formHTML += `</div>`;
        });
        
        formHTML += `
            <button type="submit" class="btn btn-primary">Execute</button>
        </form>
        
        <div id="tool-result" style="margin-top: 20px;"></div>
        `;
        
        content.innerHTML = formHTML;
        
        // Bind form submit
        const form = content.querySelector('form');
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.executeTool(tool, form);
        });
        
        this.toolPanel.classList.add('open');
    }

    executeTool(tool, form) {
        const formData = new FormData(form);
        const args = {};
        
        formData.forEach((value, key) => {
            if (value) {
                // Parse JSON for headers
                if (key === 'headers') {
                    try {
                        args[key] = JSON.parse(value);
                    } catch {
                        args[key] = value;
                    }
                } else {
                    args[key] = value;
                }
            }
        });
        
        this.socket.emit('execute_tool', {
            tool: tool,
            args: args
        });
        
        this.showToast(`Executing ${tool}...`, 'info');
    }

    displayToolResult(data) {
        const resultDiv = document.getElementById('tool-result');
        if (!resultDiv) return;
        
        const success = data.result && data.result.success;
        const result = data.result || {};
        
        let resultHTML = `
            <div style="padding: 12px; border-radius: 6px; border: 1px solid ${success ? 'var(--success)' : 'var(--error)'}; background: rgba(0,0,0,0.2);">
                <div style="font-weight: 600; margin-bottom: 8px; color: ${success ? 'var(--success)' : 'var(--error)'};">
                    ${success ? '✓ Success' : '✕ Failed'}
                </div>
        `;
        
        if (result.stdout) {
            resultHTML += `<pre style="margin: 8px 0;">${this.escapeHtml(result.stdout)}</pre>`;
        }
        
        if (result.content) {
            resultHTML += `<pre style="margin: 8px 0;">${this.escapeHtml(result.content)}</pre>`;
        }
        
        if (result.error) {
            resultHTML += `<div style="color: var(--error); margin-top: 8px;">${this.escapeHtml(result.error)}</div>`;
        }
        
        // Show raw JSON for debugging
        resultHTML += `
            <details style="margin-top: 12px;">
                <summary style="cursor: pointer; color: var(--text-muted); font-size: 0.875rem;">Raw Result</summary>
                <pre style="margin-top: 8px; font-size: 0.75rem;">${JSON.stringify(result, null, 2)}</pre>
            </details>
        </div>
        `;
        
        resultDiv.innerHTML = resultHTML;
    }

    closeToolPanel() {
        this.toolPanel.classList.remove('open');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Navigation Methods
    switchView(viewName) {
        // Update navigation items
        this.navItems.forEach(item => {
            item.classList.remove('active');
            if (item.dataset.view === viewName) {
                item.classList.add('active');
            }
        });

        // Update view containers
        this.viewContainers.forEach(container => {
            container.classList.remove('active');
        });

        const targetView = document.getElementById(`${viewName}-view`);
        if (targetView) {
            targetView.classList.add('active');
        }

        // Load view-specific data
        if (viewName === 'settings') {
            this.loadSettings();
        }
    }

    // Settings Methods
    bindSettingsEvents() {
        const elements = this.settingsElements;
        
        // Slider updates
        elements.maxTurns?.addEventListener('input', (e) => {
            const value = e.target.value;
            e.target.nextElementSibling.textContent = `${value} turns`;
        });

        elements.temperature?.addEventListener('input', (e) => {
            const value = e.target.value;
            e.target.nextElementSibling.textContent = `${value}%`;
        });

        // GCS backup toggle
        elements.enableGcsBackup?.addEventListener('change', (e) => {
            const gcsSettings = document.getElementById('gcs-settings');
            if (gcsSettings) {
                gcsSettings.style.display = e.target.checked ? 'block' : 'none';
            }
        });

        // Settings actions
        elements.saveBtn?.addEventListener('click', () => this.saveSettings());
        elements.resetBtn?.addEventListener('click', () => this.resetSettings());
        elements.exportBtn?.addEventListener('click', () => this.exportSettings());
    }

    async loadSettings() {
        try {
            const response = await fetch('/api/config');
            const config = await response.json();
            
            // Update form fields
            if (this.settingsElements.modelSelect) {
                this.settingsElements.modelSelect.value = config.model_id || 'gemini-2.0-flash-exp';
            }
            
            if (this.settingsElements.maxTurns) {
                this.settingsElements.maxTurns.value = config.max_turns || 20;
                this.settingsElements.maxTurns.nextElementSibling.textContent = `${config.max_turns || 20} turns`;
            }
            
            if (this.settingsElements.shellTimeout) {
                this.settingsElements.shellTimeout.value = config.shell_timeout || 60;
            }
            
            if (this.settingsElements.httpTimeout) {
                this.settingsElements.httpTimeout.value = config.http_timeout || 15;
            }
            
            if (this.settingsElements.enableFileSandbox) {
                this.settingsElements.enableFileSandbox.checked = true; // Always enabled for security
            }
            
            if (this.settingsElements.enableGcsBackup) {
                this.settingsElements.enableGcsBackup.checked = config.gcs_enabled || false;
                const gcsSettings = document.getElementById('gcs-settings');
                if (gcsSettings) {
                    gcsSettings.style.display = config.gcs_enabled ? 'block' : 'none';
                }
            }
            
            if (this.settingsElements.gcsBucket) {
                this.settingsElements.gcsBucket.value = config.gcs_bucket || '';
            }
            
            if (this.settingsElements.autoBackup) {
                this.settingsElements.autoBackup.checked = true;
            }
            
            if (this.settingsElements.enableDebug) {
                this.settingsElements.enableDebug.checked = true;
            }
            
            if (this.settingsElements.enableMetrics) {
                this.settingsElements.enableMetrics.checked = true;
            }
            
            if (this.settingsElements.logLevel) {
                this.settingsElements.logLevel.value = config.log_level || 'INFO';
            }
            
        } catch (error) {
            console.error('Failed to load settings:', error);
            this.showToast('Failed to load settings', 'error');
        }
    }

    async saveSettings() {
        try {
            const settings = {
                model_id: this.settingsElements.modelSelect?.value,
                max_turns: parseInt(this.settingsElements.maxTurns?.value) || 20,
                temperature: parseFloat(this.settingsElements.temperature?.value) / 100 || 0.7,
                shell_timeout: parseInt(this.settingsElements.shellTimeout?.value) || 60,
                http_timeout: parseInt(this.settingsElements.httpTimeout?.value) || 15,
                enable_file_sandbox: this.settingsElements.enableFileSandbox?.checked || false,
                enable_gcs_backup: this.settingsElements.enableGcsBackup?.checked || false,
                gcs_bucket: this.settingsElements.gcsBucket?.value || '',
                auto_backup: this.settingsElements.autoBackup?.checked || false,
                enable_debug: this.settingsElements.enableDebug?.checked || false,
                enable_metrics: this.settingsElements.enableMetrics?.checked || false,
                log_level: this.settingsElements.logLevel?.value || 'INFO'
            };

            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });

            const result = await response.json();
            
            if (result.success) {
                this.showToast('Settings saved successfully', 'success');
                // Update status display
                await this.loadStatus();
            } else {
                this.showToast(result.error || 'Failed to save settings', 'error');
            }
            
        } catch (error) {
            console.error('Failed to save settings:', error);
            this.showToast('Failed to save settings', 'error');
        }
    }

    resetSettings() {
        if (confirm('Are you sure you want to reset all settings to their default values?')) {
            // Reset form to defaults
            if (this.settingsElements.modelSelect) {
                this.settingsElements.modelSelect.value = 'gemini-2.0-flash-exp';
            }
            
            if (this.settingsElements.maxTurns) {
                this.settingsElements.maxTurns.value = 20;
                this.settingsElements.maxTurns.nextElementSibling.textContent = '20 turns';
            }
            
            if (this.settingsElements.temperature) {
                this.settingsElements.temperature.value = 70;
                this.settingsElements.temperature.nextElementSibling.textContent = '70%';
            }
            
            if (this.settingsElements.shellTimeout) {
                this.settingsElements.shellTimeout.value = 60;
            }
            
            if (this.settingsElements.httpTimeout) {
                this.settingsElements.httpTimeout.value = 15;
            }
            
            if (this.settingsElements.enableFileSandbox) {
                this.settingsElements.enableFileSandbox.checked = true;
            }
            
            if (this.settingsElements.enableGcsBackup) {
                this.settingsElements.enableGcsBackup.checked = false;
                const gcsSettings = document.getElementById('gcs-settings');
                if (gcsSettings) {
                    gcsSettings.style.display = 'none';
                }
            }
            
            if (this.settingsElements.gcsBucket) {
                this.settingsElements.gcsBucket.value = '';
            }
            
            if (this.settingsElements.autoBackup) {
                this.settingsElements.autoBackup.checked = true;
            }
            
            if (this.settingsElements.enableDebug) {
                this.settingsElements.enableDebug.checked = true;
            }
            
            if (this.settingsElements.enableMetrics) {
                this.settingsElements.enableMetrics.checked = true;
            }
            
            if (this.settingsElements.logLevel) {
                this.settingsElements.logLevel.value = 'INFO';
            }
            
            this.showToast('Settings reset to defaults', 'info');
        }
    }

    exportSettings() {
        try {
            const settings = {
                model_id: this.settingsElements.modelSelect?.value,
                max_turns: parseInt(this.settingsElements.maxTurns?.value) || 20,
                temperature: parseFloat(this.settingsElements.temperature?.value) / 100 || 0.7,
                shell_timeout: parseInt(this.settingsElements.shellTimeout?.value) || 60,
                http_timeout: parseInt(this.settingsElements.httpTimeout?.value) || 15,
                enable_file_sandbox: this.settingsElements.enableFileSandbox?.checked || false,
                enable_gcs_backup: this.settingsElements.enableGcsBackup?.checked || false,
                gcs_bucket: this.settingsElements.gcsBucket?.value || '',
                auto_backup: this.settingsElements.autoBackup?.checked || false,
                enable_debug: this.settingsElements.enableDebug?.checked || false,
                enable_metrics: this.settingsElements.enableMetrics?.checked || false,
                log_level: this.settingsElements.logLevel?.value || 'INFO'
            };

            const dataStr = JSON.stringify(settings, null, 2);
            const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
            
            const exportFileDefaultName = 'oracle-agent-settings.json';
            
            const linkElement = document.createElement('a');
            linkElement.setAttribute('href', dataUri);
            linkElement.setAttribute('download', exportFileDefaultName);
            linkElement.click();
            
            this.showToast('Settings exported successfully', 'success');
            
        } catch (error) {
            console.error('Failed to export settings:', error);
            this.showToast('Failed to export settings', 'error');
        }
    }

    showKeyboardShortcuts() {
        const shortcuts = [
            { key: 'Enter', description: 'Send message' },
            { key: 'Shift + Enter', description: 'New line in message' },
            { key: 'Ctrl + /', description: 'Show keyboard shortcuts' },
            { key: 'Esc', description: 'Close panels' }
        ];

        let content = '<h3>Keyboard Shortcuts</h3><div class="shortcuts-list">';
        shortcuts.forEach(shortcut => {
            content += `
                <div class="shortcut-item">
                    <kbd>${shortcut.key}</kbd>
                    <span>${shortcut.description}</span>
                </div>
            `;
        });
        content += '</div>';

        this.showToast('Keyboard shortcuts - check console for details', 'info');
        console.log('Keyboard Shortcuts:', shortcuts);
    }
}

// Initialize GUI when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.oracleGUI = new OracleGUI();
});
