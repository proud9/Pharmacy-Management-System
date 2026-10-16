/**
 * PharmPulse Pro - Remote Security & Audit Controller
 * Manages active remote login sessions, remote lockout revocation,
 * and immutable tamper-evident audit logs.
 */

class AdminEngine {
  constructor() {
    this.sessions = [];
    this.logs = [];
    this.init();
  }

  init() {}

  async loadAdminData() {
    await Promise.all([
      this.loadSessions(),
      this.loadAuditLogs()
    ]);
  }

  async loadSessions() {
    try {
      const res = await window.pharmApp.fetchWithAuth('/api/auth/sessions');
      const data = await res.json();
      if (data.success) {
        this.sessions = data.sessions;
        this.renderSessions();
      }
    } catch (e) {
      console.error(e);
    }
  }

  renderSessions() {
    const tbody = document.getElementById('admin-sessions-tbody');
    if (!tbody) return;

    if (this.sessions.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:2rem;">No remote sessions logged.</td></tr>`;
      return;
    }

    tbody.innerHTML = this.sessions.map(s => {
      const statusBadge = s.is_active ? 
        '<span class="badge badge-success">Active Session</span>' : '<span class="badge badge-danger">Revoked</span>';

      return `
        <tr>
          <td>
            <div style="font-weight:700;">${s.full_name}</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">${s.username} (${s.role.toUpperCase()})</div>
          </td>
          <td style="font-family:var(--font-mono); font-weight:600;">${s.ip_address}</td>
          <td>${s.device_type}</td>
          <td style="font-size:0.82rem;">${s.login_time}</td>
          <td>${statusBadge}</td>
          <td>
            ${s.is_active ? `
              <button class="btn btn-secondary btn-sm" onclick="window.adminEngine.revokeSession(${s.id})" style="color:var(--danger);">
                Revoke Remote Access
              </button>
            ` : '—'}
          </td>
        </tr>
      `;
    }).join('');
  }

  async revokeSession(sessionId) {
    if (!confirm("Are you sure you want to terminate this remote session immediately?")) return;

    try {
      const res = await window.pharmApp.fetchWithAuth(`/api/auth/sessions/${sessionId}`, { method: 'DELETE' });
      const data = await res.json();
      if (data.success) {
        window.pharmApp.showToast(data.message);
        this.loadSessions();
      } else {
        window.pharmApp.showToast(data.message, 'danger');
      }
    } catch (e) {
      console.error(e);
    }
  }

  async loadAuditLogs() {
    try {
      const res = await window.pharmApp.fetchWithAuth('/api/audit/logs');
      const data = await res.json();
      if (data.success) {
        this.logs = data.logs;
        this.renderAuditLogs();
      }
    } catch (e) {
      console.error(e);
    }
  }

  renderAuditLogs() {
    const tbody = document.getElementById('admin-audit-tbody');
    if (!tbody) return;

    if (this.logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:2rem;">No audit records.</td></tr>`;
      return;
    }

    tbody.innerHTML = this.logs.map(log => `
      <tr>
        <td style="font-family:var(--font-mono); font-size:0.8rem; white-space:nowrap;">${log.created_at}</td>
        <td style="font-weight:600;">${log.user_name || 'System Auto'}</td>
        <td><span class="badge badge-info">${log.action}</span></td>
        <td style="font-size:0.82rem; font-family:var(--font-mono);">${log.entity}</td>
        <td style="font-size:0.82rem; font-family:var(--font-mono);">${log.entity_id || '—'}</td>
        <td style="font-size:0.82rem; color:var(--text-main);">${log.details}</td>
        <td style="font-family:var(--font-mono); font-size:0.78rem; color:var(--text-subtle);">${log.ip_address}</td>
      </tr>
    `).join('');
  }
}

// Global instance
window.adminEngine = new AdminEngine();
