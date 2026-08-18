/**
 * Collaborative Workspace - Frontend
 * Real-time синхронизация через WebSocket
 */

// ===== КОНФИГУРАЦИЯ =====
const CONFIG = {
    get API_URL() { return `${window.location.protocol}//${window.location.host}`; },
    get WS_URL() { return `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`; },
    RECONNECT_INTERVAL: 3000,
    SYNC_DEBOUNCE: 300
};

// ===== СОСТОЯНИЕ =====
const state = {
    currentUser: localStorage.getItem('collab_username') || '',
    currentProject: null,
    projects: [],
    ws: null,
    reconnectTimer: null,
    syncTimer: null,
    lastContent: '',
    isLocalChange: false,
    participants: [],
    versions: [],
    feedback: []
};

// ===== DOM ЭЛЕМЕНТЫ =====
const elements = {
    // Проекты
    projectsList: document.getElementById('projects-list'),
    newProjectBtn: document.getElementById('new-project-btn'),
    newProjectModal: document.getElementById('new-project-modal'),
    newProjectTitle: document.getElementById('new-project-title'),
    newProjectContent: document.getElementById('new-project-content'),
    createProjectBtn: document.getElementById('create-project-btn'),
    cancelNewProject: document.getElementById('cancel-new-project'),
    
    // Редактор
    projectTitle: document.getElementById('project-title'),
    editor: document.getElementById('editor'),
    wordCount: document.getElementById('word-count'),
    lastSaved: document.getElementById('last-saved'),
    saveVersionBtn: document.getElementById('save-version-btn'),
    analyzeBtn: document.getElementById('analyze-btn'),
    brainstormBtn: document.getElementById('brainstorm-btn'),
    
    // Версии
    versionModal: document.getElementById('version-modal'),
    versionComment: document.getElementById('version-comment'),
    confirmSaveVersion: document.getElementById('confirm-save-version'),
    cancelVersion: document.getElementById('cancel-version'),
    versionsList: document.getElementById('versions-list'),
    
    // Фидбек
    feedbackType: document.getElementById('feedback-type'),
    feedbackInput: document.getElementById('feedback-input'),
    addFeedbackBtn: document.getElementById('add-feedback-btn'),
    feedbackList: document.getElementById('feedback-list'),
    
    // Анализ
    analysisContent: document.getElementById('analysis-content'),
    
    // Чат
    chatMessages: document.getElementById('chat-messages'),
    chatInput: document.getElementById('chat-input'),
    sendChatBtn: document.getElementById('send-chat-btn'),
    
    // Табы
    tabBtns: document.querySelectorAll('.tab-btn'),
    tabPanels: document.querySelectorAll('.tab-panel'),
    
    // Пользователь
    userBtn: document.getElementById('user-btn'),
    userModal: document.getElementById('user-modal'),
    usernameInput: document.getElementById('username-input'),
    setUsernameBtn: document.getElementById('set-username-btn'),
    
    // Статус
    connectionStatus: document.getElementById('connection-status'),
    participantsCount: document.getElementById('participants-count')
};

// ===== API =====
const api = {
    async getProjects() {
        const res = await fetch(`${CONFIG.API_URL}/api/projects`);
        return res.json();
    },
    
    async createProject(title, content = '', author) {
        const res = await fetch(`${CONFIG.API_URL}/api/projects`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, content, author })
        });
        return res.json();
    },
    
    async getProject(id) {
        const res = await fetch(`${CONFIG.API_URL}/api/projects/${id}`);
        return res.json();
    },
    
    async updateProject(id, content, author) {
        const res = await fetch(`${CONFIG.API_URL}/api/projects/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content, author })
        });
        return res.json();
    },
    
    async getVersions(projectId) {
        const res = await fetch(`${CONFIG.API_URL}/api/projects/${projectId}/versions`);
        return res.json();
    },
    
    async getFeedback(projectId) {
        const res = await fetch(`${CONFIG.API_URL}/api/projects/${projectId}/feedback`);
        return res.json();
    },
    
    async addFeedback(projectId, author, content, feedbackType, lineNumber = null) {
        const res = await fetch(`${CONFIG.API_URL}/api/projects/${projectId}/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_id: projectId, author, content, feedback_type: feedbackType, line_number: lineNumber })
        });
        return res.json();
    },
    
    async analyzeProject(projectId) {
        const res = await fetch(`${CONFIG.API_URL}/api/projects/${projectId}/analysis`);
        return res.json();
    }
};

// ===== WEBSOCKET =====
function connectWebSocket() {
    if (!state.currentProject) return;
    if (state.ws?.readyState === WebSocket.OPEN) return;
    
    const wsUrl = `${CONFIG.WS_URL}/${state.currentProject.id}?user=${encodeURIComponent(state.currentUser)}`;
    state.ws = new WebSocket(wsUrl);
    
    state.ws.onopen = () => {
        console.log('WebSocket подключен');
        updateConnectionStatus(true);
    };
    
    state.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleWebSocketMessage(msg);
    };
    
    state.ws.onclose = () => {
        console.log('WebSocket отключен');
        updateConnectionStatus(false);
        scheduleReconnect();
    };
    
    state.ws.onerror = (error) => {
        console.error('WebSocket ошибка:', error);
    };
}

function scheduleReconnect() {
    if (state.reconnectTimer) return;
    state.reconnectTimer = setTimeout(() => {
        state.reconnectTimer = null;
        connectWebSocket();
    }, CONFIG.RECONNECT_INTERVAL);
}

function handleWebSocketMessage(msg) {
    switch (msg.type) {
        case 'content_updated':
            if (msg.author !== state.currentUser) {
                // Применяем изменения от других
                state.isLocalChange = true;
                elements.editor.value = msg.content;
                state.lastContent = msg.content;
                state.isLocalChange = false;
                updateWordCount();
            }
            break;
            
        case 'user_joined':
            state.participants = msg.participants || [];
            updateParticipantsCount();
            addChatMessage('system', `${msg.user} присоединился`);
            break;
            
        case 'user_left':
            addChatMessage('system', `${msg.user} вышел`);
            break;
            
        case 'chat_message':
            addChatMessage(msg.user, msg.message, msg.user === state.currentUser);
            break;
            
        case 'version_saved':
            loadVersions();
            addChatMessage('system', `${msg.by} сохранил версию ${msg.version.version_number}`);
            break;
            
        case 'cursor_moved':
            // Можно показать позицию курсора других пользователей
            break;
    }
}

function sendWebSocketMessage(msg) {
    if (state.ws?.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify(msg));
    }
}

// ===== UI ОБНОВЛЕНИЯ =====
function updateConnectionStatus(connected) {
    elements.connectionStatus.className = `status ${connected ? 'connected' : 'disconnected'}`;
    elements.connectionStatus.textContent = '●';
}

function updateParticipantsCount() {
    elements.participantsCount.textContent = `${state.participants.length} участников`;
}

function updateWordCount() {
    const text = elements.editor.value;
    const count = text.trim() ? text.trim().split(/\s+/).length : 0;
    elements.wordCount.textContent = `${count} слов`;
}

// ===== ПРОЕКТЫ =====
async function loadProjects() {
    try {
        state.projects = await api.getProjects();
        renderProjects();
    } catch (e) {
        console.error('Ошибка загрузки проектов:', e);
    }
}

function renderProjects() {
    if (state.projects.length === 0) {
        elements.projectsList.innerHTML = '<div class="empty-state">Нет проектов. Создайте первый!</div>';
        return;
    }
    
    elements.projectsList.innerHTML = state.projects.map(p => `
        <div class="project-item ${p.id === state.currentProject?.id ? 'active' : ''}" data-id="${p.id}">
            <div class="project-title">${escapeHtml(p.title)}</div>
            <div class="project-meta">${p.collaborators?.length || 1} участников</div>
        </div>
    `).join('');
    
    // Обработчики клика
    elements.projectsList.querySelectorAll('.project-item').forEach(item => {
        item.addEventListener('click', () => selectProject(item.dataset.id));
    });
}

async function selectProject(projectId) {
    // Закрываем текущее WebSocket
    if (state.ws) {
        state.ws.close();
        state.ws = null;
    }
    
    try {
        const project = await api.getProject(projectId);
        state.currentProject = project;
        
        // Обновляем UI
        elements.projectTitle.value = project.title;
        elements.editor.value = project.content;
        state.lastContent = project.content;
        updateWordCount();
        
        // Обновляем список проектов
        renderProjects();
        
        // Загружаем данные
        loadVersions();
        loadFeedback();
        
        // Подключаем WebSocket
        connectWebSocket();
        
    } catch (e) {
        console.error('Ошибка выбора проекта:', e);
    }
}

async function createNewProject() {
    const title = elements.newProjectTitle.value.trim();
    const content = elements.newProjectContent.value;
    
    if (!title) return;
    
    try {
        const project = await api.createProject(title, content, state.currentUser);
        state.projects.unshift(project);
        renderProjects();
        
        // Закрываем модалку
        elements.newProjectModal.classList.add('hidden');
        elements.newProjectTitle.value = '';
        elements.newProjectContent.value = '';
        
        // Выбираем новый проект
        selectProject(project.id);
        
    } catch (e) {
        console.error('Ошибка создания проекта:', e);
        alert('Не удалось создать проект');
    }
}

// ===== ВЕРСИИ =====
async function loadVersions() {
    if (!state.currentProject) return;
    
    try {
        state.versions = await api.getVersions(state.currentProject.id);
        renderVersions();
    } catch (e) {
        console.error('Ошибка загрузки версий:', e);
    }
}

function renderVersions() {
    if (state.versions.length === 0) {
        elements.versionsList.innerHTML = '<div class="empty-state">Версий пока нет</div>';
        return;
    }
    
    elements.versionsList.innerHTML = state.versions.map(v => `
        <div class="version-item" data-id="${v.id}">
            <div class="version-number">Версия ${v.version_number}</div>
            <div class="version-comment">${escapeHtml(v.comment) || 'Без комментария'}</div>
            <div class="version-meta">${v.author} • ${formatDate(v.created_at)}</div>
        </div>
    `).join('');
}

function saveVersion() {
    const comment = elements.versionComment.value.trim();
    
    sendWebSocketMessage({
        type: 'save_version',
        content: elements.editor.value,
        comment: comment
    });
    
    elements.versionModal.classList.add('hidden');
    elements.versionComment.value = '';
    elements.lastSaved.textContent = 'Сохранено: ' + new Date().toLocaleTimeString();
}

// ===== ФИДБЕК =====
async function loadFeedback() {
    if (!state.currentProject) return;
    
    try {
        state.feedback = await api.getFeedback(state.currentProject.id);
        renderFeedback();
    } catch (e) {
        console.error('Ошибка загрузки фидбека:', e);
    }
}

function renderFeedback() {
    if (state.feedback.length === 0) {
        elements.feedbackList.innerHTML = '<div class="empty-state">Фидбеков пока нет</div>';
        return;
    }
    
    elements.feedbackList.innerHTML = state.feedback.map(f => `
        <div class="feedback-item">
            <div class="feedback-header">
                <span class="feedback-author">${escapeHtml(f.author)}</span>
                <span class="feedback-type ${f.feedback_type}">${getFeedbackTypeLabel(f.feedback_type)}</span>
            </div>
            <div class="feedback-content">${escapeHtml(f.content)}</div>
            <div class="feedback-time">${formatDate(f.created_at)}</div>
        </div>
    `).join('');
}

async function addFeedback() {
    if (!state.currentProject) return;
    
    const content = elements.feedbackInput.value.trim();
    if (!content) return;
    
    const type = elements.feedbackType.value;
    
    try {
        await api.addFeedback(state.currentProject.id, state.currentUser, content, type);
        elements.feedbackInput.value = '';
        loadFeedback();
    } catch (e) {
        console.error('Ошибка добавления фидбека:', e);
    }
}

function getFeedbackTypeLabel(type) {
    const labels = {
        'strength': '✅ Сильная сторона',
        'improvement': '🔧 Улучшение',
        'question': '❓ Вопрос',
        'idea': '💡 Идея',
        'general': '💬 Комментарий'
    };
    return labels[type] || type;
}

// ===== АНАЛИЗ =====
async function analyzeProject() {
    if (!state.currentProject) return;
    
    elements.analysisContent.innerHTML = '<div class="empty-state">Анализируем...</div>';
    
    try {
        const analysis = await api.analyzeProject(state.currentProject.id);
        renderAnalysis(analysis);
    } catch (e) {
        console.error('Ошибка анализа:', e);
        elements.analysisContent.innerHTML = '<div class="empty-state">Ошибка анализа</div>';
    }
}

function renderAnalysis(analysis) {
    if (analysis.error) {
        elements.analysisContent.innerHTML = `<div class="empty-state">${analysis.error}</div>`;
        return;
    }
    
    const sentimentClass = `sentiment-${analysis.sentiment}`;
    const sentimentText = analysis.sentiment === 'positive' ? 'Позитивная' : 
                          analysis.sentiment === 'negative' ? 'Негативная' : 'Нейтральная';
    
    elements.analysisContent.innerHTML = `
        <div class="analysis-section">
            <h4>Темы</h4>
            <ul class="analysis-list">
                ${analysis.themes.map(t => `<li>${escapeHtml(t)}</li>`).join('')}
            </ul>
        </div>
        
        <div class="analysis-section">
            <h4>Тональность</h4>
            <div class="analysis-value ${sentimentClass}">${sentimentText}</div>
        </div>
        
        <div class="analysis-section">
            <h4>Сложность</h4>
            <div class="analysis-value">${analysis.complexity_score}/100</div>
        </div>
        
        <div class="analysis-section">
            <h4>Статистика</h4>
            <ul class="analysis-list">
                <li>Слов: ${analysis.word_count}</li>
                <li>Время чтения: ~${analysis.reading_time_minutes} мин</li>
            </ul>
        </div>
        
        <div class="analysis-section">
            <h4>Предложения</h4>
            <ul class="analysis-list">
                ${analysis.suggestions.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
            </ul>
        </div>
        
        ${analysis.key_elements.length > 0 ? `
        <div class="analysis-section">
            <h4>Ключевые элементы</h4>
            <ul class="analysis-list">
                ${analysis.key_elements.slice(0, 5).map(e => `<li>${escapeHtml(e)}</li>`).join('')}
            </ul>
        </div>
        ` : ''}
    `;
}

// ===== ЧАТ =====
function addChatMessage(author, text, isOwn = false) {
    const div = document.createElement('div');
    div.className = `chat-message ${isOwn ? 'own' : ''}`;
    
    if (author === 'system') {
        div.className = 'system-message';
        div.textContent = text;
    } else {
        div.innerHTML = `
            <div class="author">${escapeHtml(author)}</div>
            <div class="text">${escapeHtml(text)}</div>
        `;
    }
    
    elements.chatMessages.appendChild(div);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function sendChatMessage() {
    const text = elements.chatInput.value.trim();
    if (!text) return;
    
    sendWebSocketMessage({
        type: 'chat_message',
        message: text
    });
    
    elements.chatInput.value = '';
}

// ===== УТИЛИТЫ =====
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleString('ru-RU', {
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ===== ОБРАБОТЧИКИ СОБЫТИЙ =====
function setupEventListeners() {
    // Редактор - синхронизация
    elements.editor.addEventListener('input', () => {
        if (state.isLocalChange) return;
        
        updateWordCount();
        
        // Дебаунс для отправки
        clearTimeout(state.syncTimer);
        state.syncTimer = setTimeout(() => {
            const content = elements.editor.value;
            if (content !== state.lastContent) {
                sendWebSocketMessage({
                    type: 'content_update',
                    content: content,
                    author: state.currentUser
                });
                state.lastContent = content;
            }
        }, CONFIG.SYNC_DEBOUNCE);
    });
    
    // Новый проект
    elements.newProjectBtn.addEventListener('click', () => {
        elements.newProjectModal.classList.remove('hidden');
    });
    
    elements.cancelNewProject.addEventListener('click', () => {
        elements.newProjectModal.classList.add('hidden');
    });
    
    elements.createProjectBtn.addEventListener('click', createNewProject);
    
    // Сохранение версии
    elements.saveVersionBtn.addEventListener('click', () => {
        elements.versionModal.classList.remove('hidden');
    });
    
    elements.cancelVersion.addEventListener('click', () => {
        elements.versionModal.classList.add('hidden');
    });
    
    elements.confirmSaveVersion.addEventListener('click', saveVersion);
    
    // Фидбек
    elements.addFeedbackBtn.addEventListener('click', addFeedback);
    
    // Анализ
    elements.analyzeBtn.addEventListener('click', analyzeProject);
    
    // Табы
    elements.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            
            // Активный таб
            elements.tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Активная панель
            elements.tabPanels.forEach(p => p.classList.remove('active'));
            document.getElementById(`tab-${tab}`).classList.add('active');
        });
    });
    
    // Чат
    elements.sendChatBtn.addEventListener('click', sendChatMessage);
    elements.chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChatMessage();
    });
    
    // Пользователь
    elements.userBtn.addEventListener('click', () => {
        elements.userModal.classList.remove('hidden');
    });
    
    elements.setUsernameBtn.addEventListener('click', () => {
        const name = elements.usernameInput.value.trim();
        if (name) {
            state.currentUser = name;
            localStorage.setItem('collab_username', name);
            elements.userBtn.textContent = `👤 ${name}`;
            elements.userModal.classList.add('hidden');
        }
    });
    
    // Закрытие модалок по Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal').forEach(m => {
                if (m.id !== 'user-modal') m.classList.add('hidden');
            });
        }
    });
}

// ===== ИНИЦИАЛИЗАЦИЯ =====
async function init() {
    // Проверяем имя пользователя
    if (!state.currentUser) {
        elements.userModal.classList.remove('hidden');
    } else {
        elements.userBtn.textContent = `👤 ${state.currentUser}`;
        elements.usernameInput.value = state.currentUser;
    }
    
    setupEventListeners();
    await loadProjects();
    
    // Выбираем первый проект если есть
    if (state.projects.length > 0) {
        selectProject(state.projects[0].id);
    }
}

// Запуск
init();
