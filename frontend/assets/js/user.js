// =====================
// USER DASHBOARD JS (FIXED)
// =====================

async function initDashboard() {
    if (!Utils.requireUser()) return;

    const user = TokenManager.getUser();
    if (user) {
        document.getElementById('userName').textContent = user.full_name;
        document.getElementById('userAvatar').textContent =
            user.full_name.charAt(0).toUpperCase();
    }

    await loadUserDashboardData();
    await loadNotificationCount();
}

// =====================
// DASHBOARD DATA
// =====================

async function loadUserDashboardData() {
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

// =====================
// RECENT GRIEVANCES
// =====================

function renderRecentGrievances(grievances) {
    const container = document.getElementById('recentGrievances');
    if (!container) return;

    if (!grievances || grievances.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No grievances submitted yet</p>
                <a href="submit_grievance.html" class="btn btn-primary mt-4">
                    Submit Your First Grievance
                </a>
            </div>
        `;
        return;
    }

    container.innerHTML = grievances.map(g => `
        <div class="grievance-item"
             onclick="window.location='grievance_detail.html?id=${g.grievance_id}'">

            <div class="grievance-header">
                <span class="grievance-id">${g.grievance_id}</span>
                <span class="${Utils.getPriorityClass(g.priority_level)} priority-badge">
                    ${Utils.getPriorityLabel(g.priority_level)}
                </span>
            </div>

            <div class="grievance-meta">
                <span class="grievance-category">
                    ${g.category_name || 'General'}
                </span>
                <span class="${Utils.getStatusClass(g.status)} status-badge">
                    ${Utils.getStatusLabel(g.status)}
                </span>
            </div>

            <p class="grievance-text">${g.complaint_text}</p>

            <div class="grievance-footer">
                <span class="grievance-date">
                    ${Utils.timeAgo(g.created_at)}
                </span>
                <span class="grievance-stat">
                    ${g.peer_count || 0} supporters
                </span>
            </div>
        </div>
    `).join('');
}

// =====================
// STATS
// =====================

function updateStats(data) {
    const total = data.total || 0;
    document.getElementById('totalGrievances').textContent = total;

    const items = data.items || [];

    const resolved = items.filter(i => i.status === 'RESOLVED').length;
    const pending = items.filter(i => i.status === 'SUBMITTED').length;

    document.getElementById('resolvedCount').textContent = resolved;
    document.getElementById('pendingCount').textContent = pending;
}

// =====================
// NOTIFICATIONS
// =====================

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
    } catch (error) {
        console.error(error);
    }
}

// =====================
// GRIEVANCE LIST PAGE (FIXED NAME)
// =====================

// 🔥 IMPORTANT FIX: renamed to avoid collision with admin
async function loadUserGrievances() {
    if (!Utils.requireUser()) return;

    try {
        Utils.showLoading();

        const result = await API.Grievance.getMyGrievances();

        if (result.success) {
            renderUserGrievanceList(result.data.items);
        }
    } catch (error) {
        Utils.showToast(error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

function renderUserGrievanceList(grievances) {
    const container = document.getElementById('grievanceList');
    if (!container) return;

    if (!grievances || grievances.length === 0) {
        container.innerHTML = `<div class="empty-state"><p>No grievances found</p></div>`;
        return;
    }

    container.innerHTML = grievances.map(g => `
        <div class="grievance-item"
             onclick="window.location='grievance_detail.html?id=${g.grievance_id}'">

            <div class="grievance-header">
                <span class="grievance-id">${g.grievance_id}</span>
                <span class="${Utils.getPriorityClass(g.priority_level)} priority-badge">
                    ${Utils.getPriorityLabel(g.priority_level)}
                </span>
            </div>

            <div class="grievance-meta">
                <span>${g.category_name || 'General'}</span>
                <span class="${Utils.getStatusClass(g.status)} status-badge">
                    ${Utils.getStatusLabel(g.status)}
                </span>
            </div>

            <p class="grievance-text">${g.complaint_text}</p>

            <div class="grievance-footer">
                <span>${Utils.formatDate(g.created_at)}</span>
                <span>${g.peer_count || 0}</span>
            </div>
        </div>
    `).join('');
}

// =====================
// GRIEVANCE DETAIL
// =====================

async function loadGrievanceDetail() {
    if (!Utils.requireUser()) return;

    const id = new URLSearchParams(window.location.search).get('id');
    if (!id) {
        window.location = 'track_grievance.html';
        return;
    }

    try {
        Utils.showLoading();

        const result = await API.Grievance.getById(id);

        if (result.success) {
            renderGrievanceDetail(result.data);
        }
    } catch (error) {
        Utils.showToast(error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

function renderGrievanceDetail(g) {
    document.getElementById('grievanceId').textContent = g.grievance_id;

    document.getElementById('grievanceStatus').innerHTML =
        `<span class="${Utils.getStatusClass(g.status)} status-badge">
            ${Utils.getStatusLabel(g.status)}
        </span>`;

    document.getElementById('grievancePriority').innerHTML =
        `<span class="${Utils.getPriorityClass(g.priority_level)} priority-badge">
            ${Utils.getPriorityLabel(g.priority_level)}
        </span>`;

    document.getElementById('grievanceCategory').textContent = g.category_name || '-';
    document.getElementById('grievanceLocation').textContent = g.location_details || '-';
    document.getElementById('grievanceText').textContent = g.complaint_text;
    document.getElementById('grievanceDate').textContent =
        Utils.formatDateTime(g.created_at);

    document.getElementById('peerCount').textContent = g.peer_count || 0;

    if (g.status === 'RESOLVED') {
        document.getElementById('feedbackSection').style.display = 'block';
    }
}

// =====================
// FEEDBACK
// =====================

async function submitFeedback(e) {
    e.preventDefault();

    const id = new URLSearchParams(window.location.search).get('id');
    const rating = document.querySelector('input[name="rating"]:checked')?.value;
    const comments = document.getElementById('feedbackComments').value;

    if (!rating) {
        Utils.showToast('Please select a rating', 'error');
        return;
    }

    try {
        Utils.showLoading();

        await API.Feedback.submit(id, parseInt(rating), comments);

        Utils.showToast('Feedback submitted!', 'success');

        document.getElementById('feedbackSection').innerHTML =
            '<p class="text-center">Thank you for your feedback!</p>';

    } catch (error) {
        Utils.showToast(error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

// =====================
// LOGOUT
// =====================

async function logout() {
    try {
        await API.Auth.logout();
    } catch (e) {}

    TokenManager.clear();
    window.location = 'user_login.html';
}