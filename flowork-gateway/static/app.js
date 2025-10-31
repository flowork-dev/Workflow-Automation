document.addEventListener("DOMContentLoaded", function() {
    const serverStatusList = document.getElementById('server-status-list');
    const addServerForm = document.getElementById('add-server-form');
    const newServerUrlInput = document.getElementById('new-server-url');
    const totalRequestsSpan = document.getElementById('total-requests');
    const healthyServersSpan = document.getElementById('healthy-servers');
    const totalServersSpan = document.getElementById('total-servers');
    const trafficLogContainer = document.getElementById('traffic-log-container');
    const serverFilterButtons = document.getElementById('server-filter-buttons');
    const aiPerformanceBar = document.getElementById('ai-performance');
    let currentFilter = 'all';
    let allServersCache = [];
    let performanceLevel = 87;
    function updateAIPerformance() {
        performanceLevel += (Math.random() - 0.5) * 5;
        performanceLevel = Math.max(50, Math.min(100, performanceLevel));
        if (aiPerformanceBar) {
            aiPerformanceBar.style.width = performanceLevel + '%';
            if (performanceLevel > 80) {
                aiPerformanceBar.style.background = 'var(--success-gradient)';
            } else if (performanceLevel > 60) {
                aiPerformanceBar.style.background = 'var(--warning-gradient)';
            } else {
                aiPerformanceBar.style.background = 'var(--danger-gradient)';
            }
        }
    }
    function logAI(message, type = 'INFO') {
        const icons = {
            'INFO': '🔵',
            'SUCCESS': '✅',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'AI': '🤖'
        };
        console.log(`${icons[type]} [NEURAL-AI] ${message}`);
    }
    async function updateDashboard() {
        try {
            logAI('Fetching neural dashboard data...', 'AI');
            const response = await fetch('/api/status');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            allServersCache = data.servers;
            renderServerList();
            animateNumber(totalRequestsSpan, data.total_requests);
            animateNumber(healthyServersSpan, data.healthy_server_count);
            animateNumber(totalServersSpan, data.total_server_count);
            renderTrafficLog(data.traffic);
            logAI('Dashboard neural sync completed', 'SUCCESS');
        } catch (error) {
            logAI(`Failed to update dashboard: ${error.message}`, 'ERROR');
            serverStatusList.innerHTML = `
                <li class="ai-list-item text-center py-4">
                    <i class="fas fa-exclamation-triangle fa-2x text-danger mb-2"></i>
                    <p class="text-danger mb-0">Neural Gateway Connection Lost</p>
                    <small class="text-muted">Unable to connect to AI backend</small>
                </li>
            `;
            showDemoData();
        }
    }
    function showDemoData() {
        logAI('Loading demo neural data for development', 'WARNING');
        allServersCache = [
            { url: 'http://neural-core-01:8989', status: 'HEALTHY' },
            { url: 'http://neural-core-02:8989', status: 'HEALTHY' },
            { url: 'http://ai-processor-03:8989', status: 'UNHEALTHY' }
        ];
        renderServerList();
        animateNumber(totalRequestsSpan, 15420);
        animateNumber(healthyServersSpan, 2);
        animateNumber(totalServersSpan, 3);
        const demoTraffic = [
            { time: new Date().toLocaleTimeString(), method: 'POST', path: '/ai/neural-process', status: 'FORWARDED', forwarded_to: 'neural-core-01:8989' },
            { time: new Date().toLocaleTimeString(), method: 'GET', path: '/ai/model-predict', status: 'FORWARDED', forwarded_to: 'neural-core-02:8989' },
            { time: new Date().toLocaleTimeString(), method: 'PUT', path: '/ai/training-data', status: 'FAILED', forwarded_to: 'ai-processor-03:8989' }
        ];
        renderTrafficLog(demoTraffic);
    }
    function animateNumber(element, targetValue) {
        const currentValue = parseInt(element.textContent) || 0;
        const difference = targetValue - currentValue;
        const duration = 1000;
        const steps = 30;
        const stepValue = difference / steps;
        const stepDuration = duration / steps;
        let step = 0;
        const timer = setInterval(() => {
            step++;
            const newValue = Math.round(currentValue + stepValue * step);
            element.textContent = newValue.toLocaleString();
            if (step >= steps) {
                element.textContent = targetValue.toLocaleString();
                clearInterval(timer);
            }
        }, stepDuration);
    }
    async function addServer(url) {
        try {
            logAI(`Adding new neural server: ${url}`, 'AI');
            const response = await fetch('/api/servers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to add neural server');
            }
            newServerUrlInput.value = '';
            updateDashboard();
            logAI('Neural server added successfully', 'SUCCESS');
            showNotification('Neural server added to the matrix', 'success');
        } catch (error) {
            logAI(`Error adding server: ${error.message}`, 'ERROR');
            showNotification(`Error: ${error.message}`, 'danger');
        }
    }
    async function deleteServer(url) {
        const confirmMessage = `⚠️ NEURAL ALERT ⚠️\
\
Deactivate neural server:\
${url}\
\
This will disconnect the server from the AI matrix.\
Proceed with neural disconnection?`;
        if (!confirm(confirmMessage)) return;
        try {
            logAI(`Removing neural server: ${url}`, 'AI');
            const response = await fetch('/api/servers', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to remove neural server');
            }
            updateDashboard();
            logAI('Neural server removed successfully', 'SUCCESS');
            showNotification('Neural server disconnected from matrix', 'info');
        } catch (error) {
            logAI(`Error deleting server: ${error.message}`, 'ERROR');
            showNotification(`Error: ${error.message}`, 'danger');
        }
    }
    function renderServerList() {
        serverStatusList.innerHTML = '';
        const serversToRender = allServersCache.filter(server => {
            if (currentFilter === 'all') return true;
            if (currentFilter === 'healthy') return server.status === 'HEALTHY';
            if (currentFilter === 'unhealthy') return server.status !== 'HEALTHY';
            return true;
        });
        if (serversToRender.length === 0) {
            let message = 'No neural cores configured in the matrix.';
            let icon = 'fas fa-server';
            if (allServersCache.length > 0) {
                message = `No ${currentFilter} neural servers detected.`;
                icon = 'fas fa-search';
            }
            serverStatusList.innerHTML = `
                <li class="ai-list-item text-center py-4">
                    <i class="${icon} fa-2x text-muted mb-3"></i>
                    <p class="text-muted mb-0">${message}</p>
                    <small class="text-muted">Add neural servers to expand the AI network</small>
                </li>
            `;
            return;
        }
        serversToRender.forEach((server, index) => {
            const isHealthy = server.status === 'HEALTHY';
            const dotClass = isHealthy ? 'dot-healthy' : 'dot-unhealthy';
            const statusTitle = isHealthy ? 'Neural Core Online' : 'Neural Core Critical';
            const statusText = isHealthy ? 'ONLINE' : 'CRITICAL';
            const statusColor = isHealthy ? 'text-success' : 'text-danger';
            const li = document.createElement('li');
            li.className = 'ai-list-item d-flex justify-content-between align-items-center';
            li.style.animationDelay = (index * 0.1) + 's';
            li.innerHTML = `
                <div class="flex-grow-1" style="word-break: break-all;">
                    <div class="d-flex align-items-center mb-1">
                        <span class="server-status-dot ${dotClass}" title="${statusTitle}"></span>
                        <code class="text-info">${server.url}</code>
                    </div>
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="${statusColor} fw-bold orbitron">${statusText}</small>
                        <small class="text-muted">Neural Core #${String(index + 1).padStart(2, '0')}</small>
                    </div>
                </div>
                <button class="btn btn-sm ai-btn-danger ms-3" title="Disconnect Neural Server">
                    <i class="fas fa-trash-alt"></i>
                </button>
            `;
            li.addEventListener('mouseenter', () => {
                li.style.background = 'rgba(0, 245, 255, 0.15)';
                li.style.borderColor = 'var(--neon-blue)';
            });
            li.addEventListener('mouseleave', () => {
                li.style.background = 'rgba(0, 0, 0, 0.2)';
                li.style.borderColor = 'var(--glass-border)';
            });
            li.querySelector('button').addEventListener('click', (e) => {
                e.preventDefault();
                deleteServer(server.url);
            });
            serverStatusList.appendChild(li);
        });
    }
    function renderTrafficLog(traffic) {
        if (traffic.length === 0) {
            trafficLogContainer.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-satellite-dish fa-3x text-muted mb-3"></i>
                    <p class="text-muted">Neural traffic stream is quiet...</p>
                    <small class="text-muted">Waiting for AI network activity</small>
                </div>
            `;
            return;
        }
        let logHtml = '';
        traffic.forEach((log, index) => {
            const isForwarded = log.status === 'FORWARDED';
            const statusColor = isForwarded ? 'text-success' : 'text-danger';
            const statusIcon = isForwarded ? '✓' : '✗';
            const entryClass = isForwarded ? 'traffic-forwarded' : 'traffic-failed';
            logHtml += `
                <div class="traffic-entry ${entryClass}" style="animation-delay: ${index * 0.05}s;">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <span class="text-muted small">[${log.time}]</span>
                        <span class="${statusColor}">${statusIcon} ${log.status}</span>
                    </div>
                    <div class="mb-1">
                        <span class="fw-bold text-warning">${log.method}</span>
                        <span class="text-light ms-2">${log.path}</span>
                    </div>
                    <div class="small">
                        <span class="text-muted">→ Routed to:</span>
                        <span class="text-info ms-1">${log.forwarded_to}</span>
                    </div>
                </div>
            `;
        });
        trafficLogContainer.innerHTML = logHtml;
        trafficLogContainer.scrollTop = trafficLogContainer.scrollHeight;
    }
    function showNotification(message, type = 'info') {
        const colors = {
            'success': 'var(--matrix-green)',
            'danger': 'var(--neon-pink)',
            'warning': 'var(--neural-orange)',
            'info': 'var(--neon-blue)'
        };
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--glass-bg);
            backdrop-filter: blur(15px);
            border: 2px solid ${colors[type]};
            border-radius: 15px;
            padding: 1rem 1.5rem;
            color: white;
            font-family: 'Orbitron', monospace;
            font-size: 0.9rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            z-index: 10000;
            transform: translateX(400px);
            transition: all 0.3s ease;
        `;
        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-robot me-2" style="color: ${colors[type]};"></i>
                <span>${message}</span>
            </div>
        `;
        document.body.appendChild(notification);
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);
        setTimeout(() => {
            notification.style.transform = 'translateX(400px)';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 4000);
    }
    addServerForm.addEventListener('submit', (event) => {
        event.preventDefault();
        const url = newServerUrlInput.value.trim();
        if (url) {
            addServer(url);
        }
    });
    serverFilterButtons.addEventListener('click', (event) => {
        if (event.target.tagName === 'BUTTON') {
            currentFilter = event.target.dataset.filter;
            serverFilterButtons.querySelectorAll('button').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            renderServerList();
            logAI(`Neural filter changed to: ${currentFilter}`, 'AI');
        }
    });
    newServerUrlInput.addEventListener('focus', () => {
        newServerUrlInput.style.boxShadow = '0 0 25px rgba(0, 245, 255, 0.4)';
        newServerUrlInput.style.borderColor = 'var(--neon-blue)';
    });
    newServerUrlInput.addEventListener('blur', () => {
        newServerUrlInput.style.boxShadow = 'none';
        newServerUrlInput.style.borderColor = 'var(--glass-border)';
    });
    setInterval(updateAIPerformance, 3000);
    logAI('Initializing Flowork AI Gateway Control System...', 'AI');
    logAI('Neural networks coming online...', 'AI');
    updateDashboard();
    setInterval(updateDashboard, 5000);
    setTimeout(() => {
        showNotification('AI Gateway Neural System Online', 'success');
    }, 1000);
    setTimeout(() => {
        console.log(`
    ╔══════════════════════════════════════════════════╗
    ║              FLOWORK AI GATEWAY v3.0             ║
    ║            Neural Command & Control              ║
    ║                                                  ║
    ║  🤖 AI Core: ONLINE                              ║
    ║  🧠 Neural Networks: CONNECTED                   ║
    ║  ⚡ Quantum Gateway: ACTIVE                      ║
    ║  🔮 Predictive Engine: LEARNING                  ║
    ║                                                  ║
    ║  Status: Ready for neural server management      ║
    ║  Performance: Optimal AI processing power        ║
    ╚══════════════════════════════════════════════════╝
        `);
    }, 1500);
});
