/**
 * PharmPulse Pro - Inventory & Batch Management Controller
 * Handles catalog browsing, batch lot tracking, FEFO expiration alerts,
 * stock adjustments (damaged/expired/returns), and reorder thresholds.
 */

class InventoryEngine {
  constructor() {
    this.medicines = [];
    this.init();
  }

  init() {
    this.setupListeners();
  }

  setupListeners() {
    const searchInput = document.getElementById('inventory-search-input');
    const statusSelect = document.getElementById('inventory-filter-status');

    if (searchInput) {
      searchInput.addEventListener('input', () => this.loadInventory());
    }
    if (statusSelect) {
      statusSelect.addEventListener('change', () => this.loadInventory());
    }
  }

  async loadInventory() {
    const search = document.getElementById('inventory-search-input')?.value || '';
    const status = document.getElementById('inventory-filter-status')?.value || '';

    try {
      const url = `/api/inventory/medicines?search=${encodeURIComponent(search)}&status=${encodeURIComponent(status)}`;
      const res = await window.pharmApp.fetchWithAuth(url);
      const data = await res.json();

      if (data.success) {
        this.medicines = data.medicines;
        this.renderTable();
        this.updateAlertBadges();
      }
    } catch (e) {
      console.error("Error loading inventory:", e);
    }
  }

  updateAlertBadges() {
    const lowStockCount = this.medicines.filter(m => m.stock_status === 'low_stock' || m.stock_status === 'out_of_stock').length;
    const badge = document.getElementById('sidebar-low-stock-badge');
    if (badge) {
      badge.textContent = lowStockCount;
      badge.style.display = lowStockCount > 0 ? 'inline-block' : 'none';
    }
  }

  renderTable() {
    const tbody = document.getElementById('inventory-tbody');
    if (!tbody) return;

    if (this.medicines.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="10" style="text-align:center; padding:3rem; color:var(--text-subtle);">
            No medications found in inventory matching criteria.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = this.medicines.map(m => {
      // Expiry Badge
      let expiryBadge = `<span class="badge badge-success">Good</span>`;
      if (m.expiry_status === 'expired') {
        expiryBadge = `<span class="badge badge-danger">EXPIRED</span>`;
      } else if (m.expiry_status === 'critical') {
        expiryBadge = `<span class="badge badge-danger">${m.days_to_expiry}d (Critical)</span>`;
      } else if (m.expiry_status === 'warning') {
        expiryBadge = `<span class="badge badge-warning">${m.days_to_expiry}d left</span>`;
      } else if (m.expiry_status === 'no_stock') {
        expiryBadge = `<span class="badge badge-info">No Active Lot</span>`;
      }

      // Stock Status Badge
      let stockBadge = `<span class="badge badge-success">Healthy</span>`;
      if (m.stock_status === 'out_of_stock') {
        stockBadge = `<span class="badge badge-danger">Out of Stock</span>`;
      } else if (m.stock_status === 'low_stock') {
        stockBadge = `<span class="badge badge-warning">Low Stock (≤ ${m.reorder_level})</span>`;
      }

      return `
        <tr>
          <td>
            <div style="font-weight:700; font-family:var(--font-mono); font-size:0.8rem;">${m.sku}</div>
            <div style="font-size:0.75rem; color:var(--text-subtle);">${m.barcode}</div>
          </td>
          <td>
            <div style="font-weight:700; color:var(--text-main);">${m.brand_name}</div>
            <div style="font-size:0.78rem; color:var(--text-muted);">${m.generic_name}</div>
          </td>
          <td>
            <span class="badge badge-info">${m.category}</span>
          </td>
          <td style="font-size:0.82rem;">
            ${m.dosage_form} • ${m.strength}
          </td>
          <td>
            <strong style="font-size:1.05rem; font-family:var(--font-mono); color:${m.total_stock <= m.reorder_level ? 'var(--warning)' : 'var(--text-main)'};">
              ${m.total_stock}
            </strong>
            <span style="font-size:0.75rem; color:var(--text-subtle);">units (${m.active_batches_count || 0} lots)</span>
          </td>
          <td>
            <div>${m.nearest_expiry || 'N/A'}</div>
            <div style="margin-top:2px;">${expiryBadge}</div>
          </td>
          <td style="font-family:var(--font-mono);">ZK ${m.unit_cost.toFixed(2)}</td>
          <td style="font-family:var(--font-mono); font-weight:700; color:var(--primary);">ZK ${m.unit_price.toFixed(2)}</td>
          <td>${stockBadge}</td>
          <td>
            <div style="display:flex; gap:0.4rem;">
              <button class="btn btn-secondary btn-sm" onclick="window.inventoryEngine.openBatchDetail(${m.id})" title="View Batch Lots">Lots</button>
              <button class="btn btn-secondary btn-sm" onclick="window.inventoryEngine.openQuickAdjust(${m.id}, '${m.brand_name}')" title="Adjust / Write-off Stock">Adjust</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }

  async openBatchDetail(medId) {
    try {
      const res = await window.pharmApp.fetchWithAuth(`/api/inventory/medicines/${medId}`);
      const data = await res.json();
      if (data.success) {
        const med = data.medicine;
        let batchRows = (med.batches || []).map(b => `
          <tr>
            <td style="font-weight:700; font-family:var(--font-mono);">${b.batch_number}</td>
            <td>${b.expiry_date}</td>
            <td><strong>${b.current_quantity}</strong> / ${b.initial_quantity}</td>
            <td>ZK ${b.unit_cost.toFixed(2)}</td>
            <td>ZK ${b.unit_price.toFixed(2)}</td>
            <td><span class="badge ${b.status === 'active' ? 'badge-success' : 'badge-danger'}">${b.status}</span></td>
            <td>
              <button class="btn btn-secondary btn-sm" onclick="window.inventoryEngine.openSpecificBatchAdjust(${b.id}, '${med.brand_name}', '${b.batch_number}', ${b.current_quantity})">Adjust</button>
            </td>
          </tr>
        `).join('');

        if (!batchRows) {
          batchRows = `<tr><td colspan="7" style="text-align:center;">No batches found for this product.</td></tr>`;
        }

        // Show batch detail modal
        const modalHtml = `
          <div class="modal-overlay active" id="modal-batch-detail">
            <div class="modal-card" style="max-width:750px;">
              <div class="modal-header">
                <h3>Batch Lots for ${med.brand_name} (${med.generic_name})</h3>
                <button class="btn btn-secondary btn-icon" onclick="document.getElementById('modal-batch-detail').remove()">✕</button>
              </div>
              <div class="modal-body">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Batch #</th>
                      <th>Expiry Date</th>
                      <th>Current / Initial Qty</th>
                      <th>Cost (ZK)</th>
                      <th>Price (ZK)</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>${batchRows}</tbody>
                </table>
              </div>
              <div class="modal-footer">
                <button class="btn btn-secondary" onclick="document.getElementById('modal-batch-detail').remove()">Close</button>
                <button class="btn btn-primary" onclick="document.getElementById('modal-batch-detail').remove(); window.pharmApp.openNewBatchModal();">Receive New Lot</button>
              </div>
            </div>
          </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
      }
    } catch (e) {
      console.error(e);
    }
  }

  async openQuickAdjust(medId, brandName) {
    // Find active batch for this med
    try {
      const res = await window.pharmApp.fetchWithAuth(`/api/inventory/medicines/${medId}`);
      const data = await res.json();
      if (data.success && data.medicine.batches.length > 0) {
        const b = data.medicine.batches[0];
        this.openSpecificBatchAdjust(b.id, brandName, b.batch_number, b.current_quantity);
      } else {
        window.pharmApp.showToast(`No active batches to adjust for ${brandName}`, 'warning');
      }
    } catch (e) {
      console.error(e);
    }
  }

  openSpecificBatchAdjust(batchId, brandName, batchNum, currentQty) {
    document.getElementById('adjust-batch-id').value = batchId;
    document.getElementById('adjust-batch-desc').textContent = `Adjusting: ${brandName} (Batch: ${batchNum}, Available: ${currentQty} units)`;
    document.getElementById('adjust-qty').value = '';
    document.getElementById('adjust-reason').value = '';
    window.pharmApp.openModal('modal-adjust');
  }

  async submitNewMedicine() {
    const brand = document.getElementById('med-brand-name').value.trim();
    const generic = document.getElementById('med-generic-name').value.trim();
    const category = document.getElementById('med-category').value;
    const dosage = document.getElementById('med-dosage-form').value;
    const strength = document.getElementById('med-strength').value;
    const cost = parseFloat(document.getElementById('med-unit-cost').value) || 0;
    const price = parseFloat(document.getElementById('med-unit-price').value) || 0;
    const reorder = parseInt(document.getElementById('med-reorder-level').value) || 20;
    const requiresRx = document.getElementById('med-requires-rx').checked;
    const isControlled = document.getElementById('med-is-controlled').checked;
    const instructions = document.getElementById('med-instructions').value;

    if (!brand || !generic) {
      window.pharmApp.showToast('Brand and Generic names required', 'danger');
      return;
    }

    const payload = {
      brand_name: brand,
      generic_name: generic,
      category: category,
      dosage_form: dosage,
      strength: strength,
      unit_cost: cost,
      unit_price: price,
      reorder_level: reorder,
      requires_prescription: requiresRx,
      is_controlled: isControlled,
      instructions: instructions
    };

    try {
      const res = await window.pharmApp.fetchWithAuth('/api/inventory/medicines', {
        method: 'POST',
        body: payload
      });
      const data = await res.json();
      if (data.success) {
        window.pharmApp.showToast(data.message);
        window.pharmApp.closeModals();
        this.loadInventory();
      } else {
        window.pharmApp.showToast(data.message || 'Failed to register medication', 'danger');
      }
    } catch (e) {
      console.error(e);
    }
  }

  async submitNewBatch() {
    const medId = document.getElementById('batch-med-select').value;
    const batchNum = document.getElementById('batch-number-input').value.trim();
    const qty = parseInt(document.getElementById('batch-quantity-input').value) || 0;
    const mfg = document.getElementById('batch-mfg-date').value;
    const expiry = document.getElementById('batch-expiry-date').value;
    const cost = parseFloat(document.getElementById('batch-cost-input').value) || 0;
    const supplierId = document.getElementById('batch-supplier-select').value || null;

    if (!medId || !batchNum || qty <= 0 || !expiry) {
      window.pharmApp.showToast('Please fill all required batch fields (Qty > 0, Expiry date)', 'danger');
      return;
    }

    const payload = {
      medicine_id: medId,
      batch_number: batchNum,
      quantity: qty,
      manufacture_date: mfg,
      expiry_date: expiry,
      unit_cost: cost,
      supplier_id: supplierId
    };

    try {
      const res = await window.pharmApp.fetchWithAuth('/api/inventory/batches', {
        method: 'POST',
        body: payload
      });
      const data = await res.json();
      if (data.success) {
        window.pharmApp.showToast(data.message);
        window.pharmApp.closeModals();
        this.loadInventory();
      } else {
        window.pharmApp.showToast(data.message, 'danger');
      }
    } catch (e) {
      console.error(e);
    }
  }

  async submitStockAdjustment() {
    const batchId = document.getElementById('adjust-batch-id').value;
    const adjType = document.getElementById('adjust-type').value;
    const qty = parseInt(document.getElementById('adjust-qty').value) || 0;
    const reason = document.getElementById('adjust-reason').value.trim();

    if (!batchId || qty === 0 || !reason) {
      window.pharmApp.showToast('Non-zero quantity and justification reason required', 'danger');
      return;
    }

    const payload = {
      batch_id: batchId,
      adjustment_type: adjType,
      quantity_changed: qty,
      reason: reason
    };

    try {
      const res = await window.pharmApp.fetchWithAuth('/api/inventory/adjust', {
        method: 'POST',
        body: payload
      });
      const data = await res.json();
      if (data.success) {
        window.pharmApp.showToast(data.message);
        window.pharmApp.closeModals();
        this.loadInventory();
      } else {
        window.pharmApp.showToast(data.message, 'danger');
      }
    } catch (e) {
      console.error(e);
    }
  }
}

// Global instance
window.inventoryEngine = new InventoryEngine();
