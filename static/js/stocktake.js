/**
 * PharmPulse Pro - Physical Stock Take & Audit Controller
 * Manages physical inventory count sessions, live variance detection,
 * discrepancy financial valuation, and one-click reconciliation.
 */

class StockTakeEngine {
  constructor() {
    this.audits = [];
    this.activeAuditId = null;
    this.init();
  }

  init() {}

  async loadAudits() {
    try {
      const res = await window.pharmApp.fetchWithAuth('/api/stock-takes');
      const data = await res.json();
      if (data.success) {
        this.audits = data.audits;
        this.renderAuditsList();
      }
    } catch (e) {
      console.error("Error loading stock takes:", e);
    }
  }

  renderAuditsList() {
    const tbody = document.getElementById('stocktake-list-tbody');
    if (!tbody) return;

    if (this.audits.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" style="text-align:center; padding:2.5rem; color:var(--text-subtle);">
            No stock take audits logged. Click "Initiate New Stock Take" to begin cycle count.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = this.audits.map(a => {
      const statusBadge = a.status === 'Reconciled' ? 
        '<span class="badge badge-success">Reconciled</span>' : '<span class="badge badge-warning">In Progress</span>';
      
      const varColor = a.net_variance_value < 0 ? 'var(--danger)' : (a.net_variance_value > 0 ? 'var(--primary)' : 'var(--text-main)');

      return `
        <tr>
          <td style="font-weight:700; font-family:var(--font-mono);">${a.audit_code}</td>
          <td style="font-weight:600;">${a.title}</td>
          <td>${a.conducted_by_name}</td>
          <td>${a.started_at.split(' ')[0]}</td>
          <td>${statusBadge}</td>
          <td>${a.total_items_counted || 'In Progress'}</td>
          <td style="font-family:var(--font-mono); font-weight:700; color:${varColor};">
            ZK ${(a.net_variance_value || 0).toFixed(2)}
          </td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="window.stocktakeEngine.openAuditSheet(${a.id})">
              ${a.status === 'Open' ? 'Count / Audit' : 'View Sheet'}
            </button>
          </td>
        </tr>
      `;
    }).join('');
  }

  async startNewAudit() {
    const title = prompt("Enter Title for this Physical Stock Audit:", `Cycle Count ${new Date().toLocaleDateString()}`);
    if (!title) return;

    try {
      const res = await window.pharmApp.fetchWithAuth('/api/stock-takes', {
        method: 'POST',
        body: { title: title, notes: 'Initiated from Web Terminal' }
      });
      const data = await res.json();
      if (data.success) {
        window.pharmApp.showToast(`Stock audit ${data.audit_code} started!`);
        await this.loadAudits();
        this.openAuditSheet(data.audit_id);
      } else {
        window.pharmApp.showToast(data.message, 'danger');
      }
    } catch (e) {
      console.error(e);
    }
  }

  async openAuditSheet(auditId) {
    this.activeAuditId = auditId;
    try {
      const res = await window.pharmApp.fetchWithAuth(`/api/stock-takes/${auditId}`);
      const data = await res.json();
      if (data.success) {
        const audit = data.audit;
        const sheetContainer = document.getElementById('stocktake-active-sheet');
        const titleEl = document.getElementById('active-audit-title');
        const metaEl = document.getElementById('active-audit-meta');
        const tbody = document.getElementById('stocktake-sheet-tbody');
        const reconcileBtn = document.getElementById('reconcile-audit-btn');

        if (sheetContainer) sheetContainer.style.display = 'block';
        if (titleEl) titleEl.textContent = `${audit.title} (${audit.audit_code})`;
        if (metaEl) metaEl.textContent = `Auditor: ${audit.conducted_by_name} • Started: ${audit.started_at} • Status: ${audit.status}`;

        if (reconcileBtn) {
          reconcileBtn.style.display = audit.status === 'Open' ? 'inline-flex' : 'none';
        }

        if (tbody) {
          tbody.innerHTML = (audit.items || []).map(item => {
            const isDiscrepancy = item.variance !== 0;
            const rowClass = isDiscrepancy ? 'style="background:rgba(244, 63, 94, 0.08);"' : '';
            return `
              <tr ${rowClass}>
                <td>
                  <div style="font-weight:700;">${item.brand_name}</div>
                  <div style="font-size:0.75rem; color:var(--text-muted); font-family:var(--font-mono);">Batch: ${item.batch_number}</div>
                </td>
                <td>${item.expiry_date}</td>
                <td style="font-weight:700; font-family:var(--font-mono);">${item.system_quantity}</td>
                <td>
                  ${audit.status === 'Open' ? `
                    <input type="number" class="form-input" value="${item.physical_count}" min="0" style="width:90px; padding:4px 8px; font-weight:700; font-family:var(--font-mono);"
                           onchange="window.stocktakeEngine.saveItemCount(${audit.id}, ${item.id}, this.value)">
                  ` : `<span style="font-weight:700; font-family:var(--font-mono);">${item.physical_count}</span>`}
                </td>
                <td style="font-weight:800; font-family:var(--font-mono); color:${item.variance < 0 ? 'var(--danger)' : (item.variance > 0 ? 'var(--primary)' : 'var(--text-subtle)')};">
                  ${item.variance > 0 ? '+' : ''}${item.variance}
                </td>
                <td style="font-family:var(--font-mono);">ZK ${item.unit_cost.toFixed(2)}</td>
                <td style="font-weight:700; font-family:var(--font-mono); color:${item.variance_value < 0 ? 'var(--danger)' : (item.variance_value > 0 ? 'var(--primary)' : 'var(--text-main)')};">
                  ZK ${item.variance_value.toFixed(2)}
                </td>
                <td style="font-size:0.8rem; color:var(--text-muted);">${item.notes || '—'}</td>
              </tr>
            `;
          }).join('');
        }

        // Scroll to sheet
        sheetContainer.scrollIntoView({ behavior: 'smooth' });
      }
    } catch (e) {
      console.error(e);
    }
  }

  async saveItemCount(auditId, itemId, physicalCount) {
    try {
      const res = await window.pharmApp.fetchWithAuth(`/api/stock-takes/${auditId}/count`, {
        method: 'POST',
        body: { item_id: itemId, physical_count: parseInt(physicalCount) || 0 }
      });
      const data = await res.json();
      if (data.success) {
        window.pharmApp.showToast(`Count saved. Variance: ${data.variance}`);
        this.openAuditSheet(auditId);
      }
    } catch (e) {
      console.error(e);
    }
  }

  async reconcileActiveAudit() {
    if (!this.activeAuditId) return;

    if (!confirm("Are you sure you want to COMMIT and RECONCILE this stock take? System inventory will be automatically updated to match physical counts with an immutable audit log.")) {
      return;
    }

    try {
      const res = await window.pharmApp.fetchWithAuth(`/api/stock-takes/${this.activeAuditId}/reconcile`, {
        method: 'POST'
      });
      const data = await res.json();
      if (data.success) {
        window.pharmApp.showToast(data.message);
        this.loadAudits();
        this.openAuditSheet(this.activeAuditId);
      } else {
        window.pharmApp.showToast(data.message, 'danger');
      }
    } catch (e) {
      console.error(e);
    }
  }
}

// Global instance
window.stocktakeEngine = new StockTakeEngine();
