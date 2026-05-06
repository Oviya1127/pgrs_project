
async function initDashboard() {
    if (!Utils.requireUser()) return;

    const user = TokenManager.getUser();
    if (user) {
        document.getElementById('userName').textContent = user.full_name;
        document.getElementById('userAvatar').textContent = user.full_name.charAt(0).toUpperCase();
    }

    await loadDashboardData();
    await loadNotificationCount();
}

async function loadDashboardData() {
    try {
        Utils.showLoading();
        const result = await API.Grievance.getMyGrievances(1, 5);
        if (result.success) {
            renderRecentGrievances(result.data.items);
            updateStats(result.data);
        }
    } catch (error) {
        Utils.showToast(error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

function renderRecentGrievances(grievances) {
    const container = document.getElementById('recentGrievances');
    if (!container) return;

    if (!grievances || grievances.length === 0) {
        container.innerHTML = `<div class="empty-state"><p>No grievances submitted yet</p><a href="submit_grievance.html" class="btn btn-primary mt-4">Submit Your First Grievance</a></div>`;
        return;
    }

    container.innerHTML = grievances.map(g => `
        <div class="grievance-item" onclick="window.location='grievance_detail.html?id=${g.grievance_id}'">
            <div class="grievance-header">
                <span class="grievance-id">${g.grievance_id}</span>
                <span class="${Utils.getPriorityClass(g.priority_level)} priority-badge">${Utils.getPriorityLabel(g.priority_level)}</span>
            </div>
            <div class="grievance-meta">
                <span class="grievance-category"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="vertical-align:middle;margin-right:6px"><path d="M3 7h5l2 3h11v9a1 1 0 0 1-1 1H3V7z" stroke="#1a202c" stroke-width="0.8" stroke-linecap="round" stroke-linejoin="round"/></svg> ${g.category_name || 'General'}</span>
                <span class="${Utils.getStatusClass(g.status)} status-badge">${Utils.getStatusLabel(g.status)}</span>
            </div>
            <p class="grievance-text">${g.complaint_text}</p>
            <div class="grievance-footer">
                <span class="grievance-date">${Utils.timeAgo(g.created_at)}</span>
                <span class="grievance-stat"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="vertical-align:middle;margin-right:6px"><path d="M17 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" stroke="#1a202c" stroke-width="0.9" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="7" r="3" stroke="#1a202c" stroke-width="0.9"/></svg> ${g.peer_count || 0} supporters</span>
            </div>
        </div>
    `).join('');
}

function updateStats(data) {
    const total = data.total || 0;
    document.getElementById('totalGrievances').textContent = total;

    const items = data.items || [];
    const resolved = items.filter(i => i.status === 'RESOLVED').length;
    const pending = items.filter(i => i.status === 'SUBMITTED').length;
    document.getElementById('resolvedCount').textContent = resolved;
    document.getElementById('pendingCount').textContent = pending;
}

async function loadNotificationCount() {
    try {
        const result = await API.User.getNotifications(true);
        if (result.success) {
            const count = result.data.unread_count || 0;
            const badge = document.getElementById('notificationBadge');
            if (badge) {
                badge.textContent = count;
                badge.style.display = count > 0 ? 'inline' : 'none';
            }
        }
    } catch { }
}

async function loadGrievances() {
    if (!Utils.requireUser()) return;
    try {
        Utils.showLoading();
        const result = await API.Grievance.getMyGrievances();
        if (result.success) {
            renderGrievanceList(result.data.items);
        }
    } catch (error) {
        Utils.showToast(error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

function renderGrievanceList(grievances) {
    const container = document.getElementById('grievanceList');
    if (!container) return;

    if (!grievances || grievances.length === 0) {
        container.innerHTML = `<div class="empty-state"><p>No grievances found</p></div>`;
        return;
    }

    container.innerHTML = grievances.map(g => `
        <div class="grievance-item" onclick="window.location='grievance_detail.html?id=${g.grievance_id}'">
            <div class="grievance-header">
                <span class="grievance-id">${g.grievance_id}</span>
                <span class="${Utils.getPriorityClass(g.priority_level)} priority-badge">${Utils.getPriorityLabel(g.priority_level)}</span>
            </div>
            <div class="grievance-meta">
                <span class="grievance-category"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="vertical-align:middle;margin-right:6px"><path d="M3 7h5l2 3h11v9a1 1 0 0 1-1 1H3V7z" stroke="#1a202c" stroke-width="0.8" stroke-linecap="round" stroke-linejoin="round"/></svg> ${g.category_name || 'General'}</span>
                <span class="${Utils.getStatusClass(g.status)} status-badge">${Utils.getStatusLabel(g.status)}</span>
            </div>
            <p class="grievance-text">${g.complaint_text}</p>
            <div class="grievance-footer">
                <span class="grievance-date">${Utils.formatDate(g.created_at)}</span>
                <span class="grievance-stat"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="vertical-align:middle;margin-right:6px"><path d="M17 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" stroke="#1a202c" stroke-width="0.9" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="7" r="3" stroke="#1a202c" stroke-width="0.9"/></svg> ${g.peer_count || 0}</span>
            </div>
        </div>
    `).join('');
}

async function loadGrievanceDetail() {
    if (!Utils.requireUser()) return;
    const id = new URLSearchParams(window.location.search).get('id');
    if (!id) { window.location = 'track_grievance.html'; return; }

    try {
        Utils.showLoading();
        const result = await API.Grievance.getById(id);
        if (result.success) renderGrievanceDetail(result.data);
    } catch (error) {
        Utils.showToast(error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

function renderGrievanceDetail(g) {
    document.getElementById('grievanceId').textContent = g.grievance_id;
    document.getElementById('grievanceStatus').innerHTML = `<span class="${Utils.getStatusClass(g.status)} status-badge">${Utils.getStatusLabel(g.status)}</span>`;
    document.getElementById('grievancePriority').innerHTML = `<span class="${Utils.getPriorityClass(g.priority_level)} priority-badge">${Utils.getPriorityLabel(g.priority_level)}</span>`;
    document.getElementById('grievanceCategory').textContent = g.category_name || '-';
    document.getElementById('grievanceLocation').textContent = g.location_details || '-';
    document.getElementById('grievanceText').textContent = g.complaint_text;
    document.getElementById('grievanceDate').textContent = Utils.formatDateTime(g.created_at);
    document.getElementById('peerCount').textContent = g.peer_count || 0;

    if (g.status === 'RESOLVED') document.getElementById('feedbackSection').style.display = 'block';
}

async function submitFeedback(e) {
    e.preventDefault();
    const id = new URLSearchParams(window.location.search).get('id');
    const rating = document.querySelector('input[name="rating"]:checked')?.value;
    const comments = document.getElementById('feedbackComments').value;

    if (!rating) { Utils.showToast('Please select a rating', 'error'); return; }

    try {
        Utils.showLoading();
        await API.Feedback.submit(id, parseInt(rating), comments);
        Utils.showToast('Feedback submitted!', 'success');
        document.getElementById('feedbackSection').innerHTML = '<p class="text-center">Thank you for your feedback!</p>';
    } catch (error) {
        Utils.showToast(error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

async function logout() {
    await API.Auth.logout();
    window.location = 'user_login.html';
}
