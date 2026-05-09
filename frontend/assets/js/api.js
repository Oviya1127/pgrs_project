const API_BASE_URL = 'const API_BASE_URL = "/api";';

const TokenManager = {
    getToken() { return localStorage.getItem('access_token'); },
    setToken(token) { localStorage.setItem('access_token', token); },
    removeToken() { localStorage.removeItem('access_token'); },
    getUser() { const u = localStorage.getItem('user'); return u ? JSON.parse(u) : null; },
    setUser(user) { localStorage.setItem('user', JSON.stringify(user)); },
    removeUser() { localStorage.removeItem('user'); },
    isAuthenticated() { return !!this.getToken(); },
    clear() { this.removeToken(); this.removeUser(); }
};

async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    const token = TokenManager.getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    try {
        const response = await fetch(url, { ...options, headers });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || data.message || 'Request failed');
        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

const AuthAPI = {
    async login(email, password) {
        const data = await apiRequest('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
        if (data.success && data.data) { TokenManager.setToken(data.data.access_token); TokenManager.setUser(data.data.user); }
        return data;
    },
    async register(fullName, email, phone, password) {
        const data = await apiRequest('/auth/register', { method: 'POST', body: JSON.stringify({ full_name: fullName, email, phone, password }) });
        if (data.success && data.data) { TokenManager.setToken(data.data.access_token); TokenManager.setUser(data.data.user); }
        return data;
    },
    async logout() { try { await apiRequest('/auth/logout', { method: 'POST' }); } finally { TokenManager.clear(); } }
};

const UserAPI = {
    async getProfile() { return apiRequest('/user/profile'); },
    async updateProfile(data) { return apiRequest('/user/profile', { method: 'PUT', body: JSON.stringify(data) }); },
    async getNotifications(unreadOnly = false) { return apiRequest(`/user/notifications?unread_only=${unreadOnly}`); },
    async markNotificationRead(id) { return apiRequest(`/user/notifications/${id}/read`, { method: 'PUT' }); },
    async markAllNotificationsRead() { return apiRequest('/user/notifications/read-all', { method: 'PUT' }); }
};

const GrievanceAPI = {
    async getCategories() { return apiRequest('/grievances/categories'); },
    async getLocations() { return apiRequest('/grievances/locations'); },
    async submit(data) { return apiRequest('/grievances/', { method: 'POST', body: JSON.stringify(data) }); },
    async getMyGrievances(page = 1, perPage = 10) { return apiRequest(`/grievances/?page=${page}&per_page=${perPage}`); },
    async getById(id) { return apiRequest(`/grievances/${id}`); },
    async validate(id) { return apiRequest(`/grievances/${id}/validate`, { method: 'POST' }); },
    async getSimilar(catId, locId, text) { return apiRequest(`/grievances/similar?category_id=${catId}&location_id=${locId}&complaint_text=${encodeURIComponent(text)}`); },
    async uploadAttachments(grievanceId, files) {
        const formData = new FormData();
        for (const file of files) formData.append('files', file);
        const url = `${API_BASE_URL}/grievances/${grievanceId}/attachments`;
        const headers = {};
        const token = TokenManager.getToken();
        if (token) headers['Authorization'] = `Bearer ${token}`;
        const response = await fetch(url, { method: 'POST', headers, body: formData });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Upload failed');
        return data;
    },
    async getAttachments(grievanceId) { return apiRequest(`/grievances/${grievanceId}/attachments`); },
    async deleteAttachment(grievanceId, attachmentId) { return apiRequest(`/grievances/${grievanceId}/attachments/${attachmentId}`, { method: 'DELETE' }); }
};

const AdminAPI = {
    async getGrievances(filters = {}) {
        const params = new URLSearchParams();
        if (filters.status) params.append('status', filters.status);
        if (filters.category_id) params.append('category_id', filters.category_id);
        if (filters.priority_level) params.append('priority_level', filters.priority_level);
        if (filters.location_id) params.append('location_id', filters.location_id);
        if (filters.search) params.append('search', filters.search);
        params.append('page', filters.page || 1);
        params.append('per_page', filters.per_page || 20);
        return apiRequest(`/admin/grievances?${params.toString()}`);
    },
    async getGrievanceDetail(id) { return apiRequest(`/admin/grievances/${id}`); },
    async updateStatus(id, status) { return apiRequest(`/admin/grievances/${id}/status`, { method: 'PUT', body: JSON.stringify({ status }) }); },
    async assignGrievance(id, deptId, adminId = null) { return apiRequest(`/admin/grievances/${id}/assign`, { method: 'POST', body: JSON.stringify({ department_id: deptId, admin_id: adminId }) }); },
    async getDepartments() { return apiRequest('/admin/departments'); },
    async getAdmins() { return apiRequest('/admin/admins'); },
    async getUsersCount() { return apiRequest('/admin/users/count'); },
    async getUsers(page = 1, per_page = 50) { return apiRequest(`/admin/users?page=${page}&per_page=${per_page}`); },
    async getFeedbackList(page = 1, per_page = 50) { return apiRequest(`/admin/feedback?page=${page}&per_page=${per_page}`); },
    async getAlerts() { return apiRequest('/admin/alerts'); }
};

const FeedbackAPI = {
    async submit(grievanceId, rating, comments) { return apiRequest('/feedback/', { method: 'POST', body: JSON.stringify({ grievance_id: grievanceId, rating, comments }) }); },
    async get(grievanceId) { return apiRequest(`/feedback/${grievanceId}`); }
};

const AnalyticsAPI = {
    async getOverview() { return apiRequest('/analytics/overview'); },
    async getCategories() { return apiRequest('/analytics/categories'); },
    async getDepartments() { return apiRequest('/analytics/departments'); },
    async getTrends() { return apiRequest('/analytics/trends'); },
    async getLocations() { return apiRequest('/analytics/locations'); }
};

function formatDate(d) { return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }); }
function formatDateTime(d) { return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }); }
function timeAgo(d) { const s = Math.floor((new Date() - new Date(d)) / 1000); if (s < 60) return 'Just now'; if (s < 3600) return `${Math.floor(s / 60)} min ago`; if (s < 86400) return `${Math.floor(s / 3600)} hrs ago`; return formatDate(d); }
function getPriorityClass(p) { return p ? `priority-${p.toLowerCase()}` : 'priority-low'; }
function getStatusClass(s) { return s ? `status-${s.toLowerCase().replace('_', '-')}` : 'status-submitted'; }
function getStatusLabel(s) { return { 'SUBMITTED': 'Submitted', 'IN_PROGRESS': 'In Progress', 'RESOLVED': 'Resolved' }[s] || s; }
function getPriorityLabel(p) { return { 'LOW': 'Low', 'MEDIUM': 'Medium', 'HIGH': 'High', 'CRITICAL': 'Critical' }[p] || p || 'Low'; }

function showToast(msg, type = 'info') {
    let c = document.getElementById('toast-container');
    if (!c) { c = document.createElement('div'); c.id = 'toast-container'; c.className = 'toast-container'; document.body.appendChild(c); }
    const t = document.createElement('div'); t.className = `toast toast-${type}`; t.textContent = msg; c.appendChild(t);
    setTimeout(() => { t.remove(); }, 3000);
}
function showLoading() { let o = document.getElementById('loading-overlay'); if (!o) { o = document.createElement('div'); o.id = 'loading-overlay'; o.className = 'loading-overlay'; o.innerHTML = '<div class="loading-spinner"></div>'; document.body.appendChild(o); } o.style.display = 'flex'; }
function hideLoading() { const o = document.getElementById('loading-overlay'); if (o) o.style.display = 'none'; }
function requireAuth(url = '/static/user/user_login.html') { if (!TokenManager.isAuthenticated()) { window.location.href = url; return false; } return true; }
function requireUser(url = '/static/user/user_login.html') {
    if (!TokenManager.isAuthenticated()) {
        window.location.href = url;
        return false;
    }
    const user = TokenManager.getUser();
    if (user?.role === 'ADMIN') {
        window.location.href = '/static/admin/admin_login.html';
        return false;
    }
    return true;
}
function requireAdmin(url = '/static/admin/admin_login.html') { 
    if (!TokenManager.isAuthenticated()) { 
        window.location.href = url; 
        return false; 
    }
    const user = TokenManager.getUser();
    if (user?.role !== 'ADMIN') {
        window.location.href = url;
        return false;
    }
    return true;
}

window.API = { Auth: AuthAPI, User: UserAPI, Grievance: GrievanceAPI, Admin: AdminAPI, Feedback: FeedbackAPI, Analytics: AnalyticsAPI };
window.TokenManager = TokenManager;
window.Utils = { formatDate, formatDateTime, timeAgo, getPriorityClass, getStatusClass, getStatusLabel, getPriorityLabel, showToast, showLoading, hideLoading, requireAuth, requireAdmin, requireUser };
