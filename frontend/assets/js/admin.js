
async function initAdminDashboard() {
    if (!Utils.requireAdmin()) return;
    const user = TokenManager.getUser();
    if (user) {
        document.getElementById('adminName').textContent = user.full_name;
        document.getElementById('adminAvatar').textContent = user.full_name.charAt(0).toUpperCase();
    }
    await Promise.all([loadOverview(), loadFilterOptions()]);
    await loadGrievances(getCurrentFilters());

    setInterval(() => {
        loadOverview();
        loadGrievances(getCurrentFilters());
    }, 5000);
}

async function loadOverview() {
    try {
        const result = await API.Analytics.getOverview();
        if (result.success) {
            // Dashboard no longer shows KPI cards; overview is used by charts on dashboard and analytics page
        }
    } catch (error) { console.error(error); }
}
function setEl(id, value) {
    var el = document.getElementById(id);
    if (el) el.textContent = value;
}

async function loadGrievances(filters = {}) {
    try {
        Utils.showLoading();
        const result = await API.Admin.getGrievances(filters);
        if (result.success) renderGrievanceTable(result.data.items);
    } catch (error) { Utils.showToast(error.message, 'error'); }
    finally { Utils.hideLoading(); }
}

function renderGrievanceTable(grievances) {
    const tbody = document.getElementById('grievanceTableBody');
    if (!tbody) return;

    if (!grievances || grievances.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center p-6">No grievances found</td></tr>';
        return;
    }

    tbody.innerHTML = grievances.map(g => `
        <tr onclick="viewGrievance('${g.grievance_id}')" style="cursor:pointer">
            <td><strong>${g.grievance_id}</strong></td>
            <td>${g.user_name || 'Anonymous'}</td>
            <td>${g.category_name || '-'}</td>
            <td><span class="${Utils.getPriorityClass(g.priority_level)} priority-badge">${Utils.getPriorityLabel(g.priority_level)}</span></td>
            <td><span class="${Utils.getStatusClass(g.status)} status-badge">${Utils.getStatusLabel(g.status)}</span></td>
            <td>${g.peer_count || 0}</td>
            <td>${Utils.timeAgo(g.created_at)}</td>
        </tr>
    `).join('');
}

async function loadFilterOptions() {
    try {
        const [cats, locs] = await Promise.all([
            API.Grievance.getCategories(),
            API.Grievance.getLocations()
        ]);
        const catSelect = document.getElementById('filterCategory');
        const locSelect = document.getElementById('filterLocation');
        if (cats?.success && catSelect) {
            catSelect.innerHTML = '<option value=\"\">All Categories</option>' + cats.data.map(c => `<option value=\"${c.category_id}\">${c.category_name}</option>`).join('');
        }
        if (locs?.success && locSelect) {
            locSelect.innerHTML = '<option value=\"\">All Locations</option>' + locs.data.map(l => {
                const ward = l.ward ? `ward:${l.ward}` : 'ward:-';
                const zone = l.zone_name ? l.zone_name : '-';
                const place = l.place_name ? l.place_name + ', ' : '';
                return `<option value=\"${l.location_id}\">${place}${l.district}, ${l.state} (${ward}, ${zone})</option>`;
            }).join('');
        }
    } catch (e) {
        console.error('Failed to load filter options', e);
    }
}

function getCurrentFilters() {
    const status = document.getElementById('filterStatus')?.value || '';
    const priority_level = document.getElementById('filterPriority')?.value || '';
    const category_id = document.getElementById('filterCategory')?.value || '';
    const location_id = document.getElementById('filterLocation')?.value || '';
    const search = document.getElementById('filterSearch')?.value || '';
    const filters = { page: 1, per_page: 100 };
    if (status) filters.status = status;
    if (priority_level) filters.priority_level = priority_level;
    if (category_id) filters.category_id = category_id;
    if (location_id) filters.location_id = location_id;
    if (search) filters.search = search;
    return filters;
}

async function applyFilters() {
    await loadGrievances(getCurrentFilters());
}

let filterTimer;
function debouncedApplyFilters() {
    clearTimeout(filterTimer);
    filterTimer = setTimeout(applyFilters, 300);
}

async function viewGrievance(id) {
    window.location = `grievance_review.html?id=${id}`;
}

async function loadGrievanceReview() {
    if (!Utils.requireAdmin()) return;
    const id = new URLSearchParams(window.location.search).get('id');
    if (!id) { window.location = 'admin_dashboard.html'; return; }

    try {
        Utils.showLoading();
        const result = await API.Admin.getGrievanceDetail(id);
        if (result.success) renderReviewDetail(result.data);
        await loadDepartments();
    } catch (error) { Utils.showToast(error.message, 'error'); }
    finally { Utils.hideLoading(); }
}

function renderReviewDetail(g) {
    document.getElementById('grievanceId').textContent = g.grievance_id;
    document.getElementById('userName').textContent = g.user_name || 'Anonymous';
    document.getElementById('grievanceStatus').innerHTML = `<span class="${Utils.getStatusClass(g.status)} status-badge">${Utils.getStatusLabel(g.status)}</span>`;
    document.getElementById('grievancePriority').innerHTML = `<span class="${Utils.getPriorityClass(g.priority_level)} priority-badge">${Utils.getPriorityLabel(g.priority_level)}</span>`;
    document.getElementById('grievanceCategory').textContent = g.category_name || '-';
    document.getElementById('grievanceLocation').textContent = g.location_details || '-';
    document.getElementById('grievanceText').textContent = g.complaint_text;
    document.getElementById('grievanceDate').textContent = Utils.formatDateTime(g.created_at);
    document.getElementById('peerCount').textContent = g.peer_count || 0;
    document.getElementById('sentimentScore').textContent = g.compound_score?.toFixed(2) || 'N/A';
    const statusRadio = document.querySelector(`input[name="statusChoice"][value="${g.status}"]`);
    if (statusRadio) statusRadio.checked = true;
}

async function loadDepartments() {
    try {
        const result = await API.Admin.getDepartments();
        if (result.success) {
            const select = document.getElementById('departmentSelect');
            if (!select) return;
            select.innerHTML = '<option value="">Select department</option>' +
                result.data.map(d => `<option value="${d.department_id}">${d.department_name}</option>`).join('');
        }
    } catch { }
}

async function updateStatus(status) {
    const id = new URLSearchParams(window.location.search).get('id');
    if (status === undefined) status = document.querySelector('input[name="statusChoice"]:checked')?.value;
    if (!status) return;
    try {
        Utils.showLoading();
        await API.Admin.updateStatus(id, status);
        Utils.showToast('Status updated!', 'success');
        loadGrievanceReview();
    } catch (error) { Utils.showToast(error.message, 'error'); }
    finally { Utils.hideLoading(); }
}

async function assignGrievance() {
    const id = new URLSearchParams(window.location.search).get('id');
    const deptId = document.getElementById('departmentSelect').value;
    if (!deptId) { Utils.showToast('Select a department', 'error'); return; }
    try {
        Utils.showLoading();
        await API.Admin.assignGrievance(id, parseInt(deptId));
        Utils.showToast('Assigned successfully!', 'success');
    } catch (error) { Utils.showToast(error.message, 'error'); }
    finally { Utils.hideLoading(); }
}

async function loadAnalytics() {
    if (!Utils.requireAdmin()) return;
    try {
        Utils.showLoading();
        const [overview, categories, departments] = await Promise.all([
            API.Analytics.getOverview(),
            API.Analytics.getCategories(),
            API.Analytics.getDepartments()
        ]);
        if (overview.success) renderOverviewCharts(overview.data);
        if (categories.success) renderCategoryTable(categories.data);
        if (departments.success) renderDepartmentTable(departments.data);
    } catch (error) { console.error(error); }
    finally { Utils.hideLoading(); }
}

function renderOverviewCharts(data) {
    const s = data && data.status_distribution ? data.status_distribution : {};
    // Draw status chart if canvas exists (analytics page)
    try {
        const ctx = document.getElementById('statusChartCanvas');
        if (ctx && window.Chart) {
            const labels = ['Submitted', 'In Progress', 'Resolved'];
            const values = [s.SUBMITTED || 0, s.IN_PROGRESS || 0, s.RESOLVED || 0];
            if (ctx._chart) ctx._chart.destroy();
            ctx._chart = new Chart(ctx.getContext('2d'), {
                type: 'doughnut',
                data: { labels, datasets: [{ data: values, backgroundColor: ['#3182ce','#dd6b20','#38a169'] }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
            });
        }
    } catch (e) { /* ignore */ }
}

function renderCategoryTable(categories) {
    const tbody = document.getElementById('categoryTableBody');
    if (!tbody) return;
    if (!categories || categories.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center p-6">No category data yet</td></tr>';
        return;
    }
    tbody.innerHTML = categories.map(c => `
        <tr>
            <td>${c.category_name || '—'}</td>
            <td>${c.total_grievances ?? 0}</td>
            <td>${c.resolved ?? 0}</td>
            <td>${c.in_progress ?? 0}</td>
            <td>${c.pending ?? 0}</td>
        </tr>
    `).join('');
}

function renderDepartmentTable(departments) {
    const tbody = document.getElementById('deptTableBody');
    if (!tbody) return;
    if (!departments || departments.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center p-6">No department data yet</td></tr>';
        return;
    }
    tbody.innerHTML = departments.map(d => {
        const rate = d.resolution_rate != null ? d.resolution_rate : 0;
        const trust = (d.trust_score != null ? Number(d.trust_score) * 100 : 0).toFixed(0);
        return `<tr>
            <td>${d.department_name || '—'}</td>
            <td>${d.total_assigned ?? 0}</td>
            <td>${d.total_resolved ?? 0}</td>
            <td>${rate}%</td>
            <td><strong>${trust}%</strong></td>
        </tr>`;
    }).join('');
}

async function adminLogout() {
    try { await API.Auth.logout(); } catch(e) { /* ignore */ }
    TokenManager.clear();
    window.location = '../admin/admin_login.html';
}
