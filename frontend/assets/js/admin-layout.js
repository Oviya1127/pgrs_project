/**
 * Admin layout – single source of truth for sidebar navigation.
 * Production-grade civic dashboard: fixed order, grouped sections, stable nav.
 */
(function () {
    'use strict';

    var ADMIN_BRAND_ICON = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 15.5A3.5 3.5 0 1 0 12 8.5a3.5 3.5 0 0 0 0 7z" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06A2 2 0 1 1 2.3 16.88l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09c.7 0 1.3-.39 1.51-1a1.65 1.65 0 0 0-.33-1.82l-.06-.06A2 2 0 1 1 6.59 2.3l.06.06c.44.44 1.02.69 1.64.69.28 0 .55-.04.8-.12A1.65 1.65 0 0 0 10 2.3H14a1.65 1.65 0 0 0 .91.37c.25.08.52.12.8.12.62 0 1.2-.25 1.64-.69l.06-.06A2 2 0 1 1 21.7 7.12l-.06.06a1.65 1.65 0 0 0-.33 1.82c.14.5.5.92.98 1.19.5.28.98.63 1.43 1.08z" stroke="#fff" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>';

    /** Lean nav: 7 items, 3 groups. Locations in Analytics; Feedback via Departments; Duplicates via Grievances tab; Alerts on Dashboard. */
    var NAV_SECTIONS = [
        {
            group: 'Operations',
            items: [
                { href: 'admin_dashboard.html', label: 'Dashboard', icon: 'fa-solid fa-gauge-high' },
                { href: 'grievances.html', label: 'Grievances', icon: 'fa-solid fa-list-check' },
                { href: 'assign_grievance.html', label: 'Assignments', icon: 'fa-solid fa-share-nodes' }
            ]
        },
        {
            group: 'Monitoring & Reports',
            items: [
                { href: 'department_performance.html', label: 'Departments', icon: 'fa-solid fa-building-user' },
                { href: 'analytics_dashboard.html', label: 'Analytics', icon: 'fa-solid fa-chart-pie' }
            ]
        },
        {
            group: 'Administration',
            items: [
                { href: 'users.html', label: 'User Management', icon: 'fa-solid fa-users' },
                { href: 'system_settings.html', label: 'System Settings', icon: 'fa-solid fa-gear' }
            ]
        }
    ];

    function getCurrentPageHref() {
        var path = typeof window !== 'undefined' && window.location.pathname;
        var name = path ? path.split('/').pop() : '';
        if (!name && typeof window !== 'undefined' && window.location.href) {
            var parts = window.location.href.split('/');
            name = parts[parts.length - 1].split('?')[0];
        }
        return name || 'admin_dashboard.html';
    }

    function isPageActive(itemHref) {
        var current = getCurrentPageHref();
        if (current === itemHref) return true;
        if (itemHref === 'grievance_review.html' && current.indexOf('grievance_review') !== -1) return true;
        return false;
    }

    function buildNavHtml() {
        var currentHref = getCurrentPageHref();
        var html = '';
        NAV_SECTIONS.forEach(function (section) {
            html += '<div class="nav-section"><div class="nav-section-title">' + section.group + '</div>';
            section.items.forEach(function (item) {
                var active = (item.href === currentHref) || (item.href === 'grievances.html' && currentHref.indexOf('grievance_review') !== -1);
                var activeClass = active ? ' active' : '';
                html += '<a href="' + item.href + '" class="nav-item' + activeClass + '">' +
                    '<span class="nav-item-icon"><i class="' + item.icon + '"></i></span>' + item.label + '</a>';
            });
            html += '</div>';
        });
        return html;
    }

    function getAdminDisplay() {
        if (typeof TokenManager !== 'undefined' && TokenManager.getUser) {
            var user = TokenManager.getUser();
            if (user && user.full_name) {
                return { name: user.full_name, initial: user.full_name.charAt(0).toUpperCase() };
            }
        }
        return { name: 'Admin', initial: 'A' };
    }

    function renderSidebar() {
        var el = document.getElementById('admin-sidebar');
        if (!el) return;

        var admin = getAdminDisplay();
        el.innerHTML =
            '<div class="sidebar-header">' +
                '<button type="button" class="sidebar-close-mobile" id="adminSidebarClose" aria-label="Close menu"></button>' +
                '<div class="sidebar-brand">' +
                    '<div class="sidebar-brand-icon" style="background: linear-gradient(135deg, #c53030, #9b2c2c);">' + ADMIN_BRAND_ICON + '</div>' +
                    '<div><div class="sidebar-brand-text">SPGRS</div><div class="sidebar-brand-subtitle">Admin Portal</div></div>' +
                '</div>' +
            '</div>' +
            '<nav class="sidebar-nav" id="adminSidebarNav">' + buildNavHtml() + '</nav>' +
            '<div class="sidebar-footer">' +
                '<a href="#" class="nav-item nav-item-logout" onclick="adminLogout(); return false;"><span class="nav-item-icon"><i class="fa-solid fa-right-from-bracket"></i></span> Logout</a>' +
                '<div class="user-profile">' +
                    '<div id="adminAvatar" class="user-avatar" style="background: linear-gradient(135deg, #c53030, #9b2c2c);">' + (admin.initial || 'A') + '</div>' +
                    '<div class="user-info"><div id="adminName" class="user-name">' + (admin.name || 'Admin') + '</div><div class="user-role">Administrator</div></div>' +
                '</div>' +
            '</div>';

        function closeSidebar() {
            el.classList.remove('open');
            var overlay = document.getElementById('adminSidebarOverlay');
            if (overlay) overlay.remove();
        }

        var closeBtn = document.getElementById('adminSidebarClose');
        if (closeBtn) closeBtn.addEventListener('click', closeSidebar);

        var main = document.querySelector('.main-content');
        if (main && !document.getElementById('adminMenuToggle')) {
            var toggle = document.createElement('button');
            toggle.type = 'button';
            toggle.id = 'adminMenuToggle';
            toggle.className = 'admin-menu-toggle';
            toggle.setAttribute('aria-label', 'Open menu');
            toggle.innerHTML = '<i class="fa-solid fa-bars"></i>';
            toggle.addEventListener('click', function () {
                if (el.classList.contains('open')) {
                    closeSidebar();
                } else {
                    el.classList.add('open');
                    var overlay = document.createElement('div');
                    overlay.id = 'adminSidebarOverlay';
                    overlay.className = 'admin-sidebar-overlay';
                    overlay.addEventListener('click', closeSidebar);
                    document.body.appendChild(overlay);
                }
            });
            main.insertBefore(toggle, main.firstChild);
        }
    }

    function init() {
        if (typeof Utils !== 'undefined' && Utils.requireAdmin && !Utils.requireAdmin()) return;
        renderSidebar();
    }

    window.AdminLayout = {
        init: init,
        renderSidebar: renderSidebar,
        getNavSections: function () { return NAV_SECTIONS; }
    };

    if (document.getElementById('admin-sidebar')) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
        } else {
            init();
        }
    }
})();
