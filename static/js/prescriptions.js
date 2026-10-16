/**
 * PharmPulse Pro - Digital Prescriptions Controller
 * Manages e-prescriptions, clinical verification by pharmacist,
 * and direct dispatching of verified prescriptions into the POS cart.
 */

class PrescriptionEngine {
  constructor() {
    this.prescriptions = [];
    this.allMedicines = [];
    this.init();
  }

  init() {
    const filter = document.getElementById('rx-status-filter');
    if (filter) {
      filter.addEventListener('change', () => this.loadPrescriptions());
    }
  }

  async loadPrescriptions() {
    const status = document.getElementById('rx-status-filter')?.value || 'All';
    try {
      const url = `/api/prescriptions?status=${encodeURIComponent(status)}`;
      const res = await window.pharmApp.fetchWithAuth(url);
      const data = await res.json();
      if (data.success) {
        this.prescriptions = data.prescriptions;
        this.renderPrescriptions();
        this.updatePendingBadge();
      }
    } catch (e) {
      console.error("Error loading prescriptions:", e);
    }
  }

  updatePendingBadge() {
    const pendingCount = this.prescriptions.filter(r => r.status === 'Pending').length;
    const badge = document.getElementById('sidebar-pending-rx-badge');
    if (badge) {
      badge.textContent = pendingCount;
      badge.style.display = pendingCount > 0 ? 'inline-block' : 'none';
    }
  }

  renderPrescriptions() {
    const tbody = document.getElementById('prescriptions-tbody');
    if (!tbody) return;

    if (this.prescriptions.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" style="text-align:center; padding:3rem; color:var(--text-subtle);">
            No prescriptions found matching selected status.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = this.prescriptions.map(rx => {
      let statusBadge = '<span class="badge badge-warning">Pending Review</span>';
      if (rx.status === 'Verified') {
        statusBadge = '<span class="badge badge-info">Verified & Ready</span>';
      } else if (rx.status === 'Dispensed') {
        statusBadge = '<span class="badge badge-success">Dispensed</span>';
      }

      return `
        <tr>
          <td>
            <div style="font-weight:700; font-family:var(--font-mono);">${rx.rx_number}</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">${rx.diagnosis || 'Clinical Rx'}</div>
          </td>
          <td>
            <div style="font-weight:700;">${rx.patient_name}</div>
            <div style="font-size:0.75rem; color:var(--danger); font-weight:600;">
              ${rx.patient_allergies && rx.patient_allergies !== 'None Known' ? `⚠ Allergies: ${rx.patient_allergies}` : 'Allergies: None'}
            </div>
          </td>
          <td>
            <div style="font-weight:600;">${rx.prescriber_name}</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">${rx.hospital_clinic} (${rx.prescriber_license})</div>
          </td>
          <td style="font-size:0.85rem;">${rx.rx_date}</td>
          <td>
            <span class="badge badge-info">${rx.item_count} items</span>
          </td>
          <td>${statusBadge}</td>
          <td style="font-size:0.8rem;">
            ${rx.verified_by_name ? `Approved: ${rx.verified_by_name}` : '<span style="color:var(--text-subtle);">Unverified</span>'}
          </td>
          <td>
            <div style="display:flex; gap:0.4rem;">
              <button class="btn btn-secondary btn-sm" onclick="window.prescriptionEngine.viewDetail(${rx.id})">Details</button>
              ${rx.status === 'Pending' ? `
                <button class="btn btn-primary btn-sm" onclick="window.prescriptionEngine.verifyRx(${rx.id})">Verify</button>
              ` : ''}
              ${rx.status === 'Verified' ? `
                <button class="btn btn-primary btn-sm" onclick="window.prescriptionEngine.dispatchToPOS(${rx.id})">Dispense (POS)</button>
              ` : ''}
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }

  async viewDetail(rxId) {
    try {
      const res = await window.pharmApp.fetchWithAuth(`/api/prescriptions/${rxId}`);
      const data = await res.json();
      if (data.success) {
        const rx = data.prescription;
        const itemsList = rx.items.map(it => `
          <div style="padding:0.75rem; background:var(--bg-surface); border:1px solid var(--border-subtle); border-radius:var(--radius-md); margin-bottom:0.5rem;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <div>
                <strong style="font-size:0.95rem;">${it.brand_name}</strong>
                <span style="font-size:0.8rem; color:var(--text-muted);">(${it.generic_name}) - ${it.dosage_form} ${it.strength}</span>
              </div>
              <span class="badge ${it.available_stock >= it.quantity_prescribed ? 'badge-success' : 'badge-danger'}">
                ${it.available_stock} in stock
              </span>
            </div>
            <div style="font-size:0.82rem; margin-top:0.35rem; color:var(--text-main);">
              <strong>Instructions:</strong> ${it.dosage_instructions}
            </div>
            <div style="font-size:0.78rem; color:var(--text-muted); margin-top:0.25rem;">
              Prescribed: ${it.quantity_prescribed} units • Dispensed: ${it.quantity_dispensed} • Refills: ${it.refills_remaining}/${it.refills_allowed}
            </div>
          </div>
        `).join('');

        const modalHtml = `
          <div class="modal-overlay active" id="modal-rx-detail">
            <div class="modal-card" style="max-width:700px;">
              <div class="modal-header">
                <h3>Digital Prescription ${rx.rx_number}</h3>
                <button class="btn btn-secondary btn-icon" onclick="document.getElementById('modal-rx-detail').remove()">✕</button>
              </div>
              <div class="modal-body">
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:1rem; padding:1rem; background:var(--bg-surface-elevated); border-radius:var(--radius-md);">
                  <div>
                    <div style="font-size:0.75rem; color:var(--text-muted);">PATIENT</div>
                    <div style="font-weight:700; font-size:1.05rem;">${rx.patient_name}</div>
                    <div style="font-size:0.8rem; color:var(--danger); font-weight:700;">Allergies: ${rx.allergies || 'None'}</div>
                    <div style="font-size:0.8rem; color:var(--text-muted);">Conditions: ${rx.chronic_conditions || 'None'}</div>
                  </div>
                  <div>
                    <div style="font-size:0.75rem; color:var(--text-muted);">PRESCRIBER</div>
                    <div style="font-weight:700; font-size:1.05rem;">${rx.prescriber_name}</div>
                    <div style="font-size:0.8rem; color:var(--text-muted);">${rx.hospital_clinic} (Lic: ${rx.prescriber_license})</div>
                    <div style="font-size:0.8rem; color:var(--text-muted);">Specialty: ${rx.specialization}</div>
                  </div>
                </div>

                <div style="margin-bottom:1rem;">
                  <strong style="font-size:0.9rem;">Clinical Instructions & Rx Items:</strong>
                  <div style="margin-top:0.5rem;">${itemsList}</div>
                </div>

                ${rx.notes ? `<div style="font-size:0.8rem; color:var(--text-subtle);">Notes: ${rx.notes}</div>` : ''}
              </div>
              <div class="modal-footer">
                <button class="btn btn-secondary" onclick="document.getElementById('modal-rx-detail').remove()">Close</button>
                ${rx.status === 'Pending' ? `
                  <button class="btn btn-primary" onclick="document.getElementById('modal-rx-detail').remove(); window.prescriptionEngine.verifyRx(${rx.id});">
                    Approve & Verify (RPh Sign-off)
                  </button>
                ` : ''}
                ${rx.status === 'Verified' ? `
                  <button class="btn btn-primary" onclick="document.getElementById('modal-rx-detail').remove(); window.prescriptionEngine.dispatchToPOS(${rx.id});">
                    Load into POS Cart
                  </button>
                ` : ''}
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

  async verifyRx(rxId) {
    try {
      const res = await window.pharmApp.fetchWithAuth(`/api/prescriptions/${rxId}/verify`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        window.pharmApp.showToast(data.message);
        this.loadPrescriptions();
      } else {
        window.pharmApp.showToast(data.message, 'danger');
      }
    } catch (e) {
      console.error(e);
    }
  }

  async dispatchToPOS(rxId) {
    try {
      const res = await window.pharmApp.fetchWithAuth(`/api/prescriptions/${rxId}`);
      const data = await res.json();
      if (data.success) {
        const rx = data.prescription;
        // Clear cart first
        window.posEngine.clearCart();
        window.posEngine.selectedPatientId = rx.patient_id;

        // Set patient dropdown in POS
        const patSelect = document.getElementById('pos-patient-select');
        if (patSelect) patSelect.value = rx.patient_id;
        window.posEngine.updatePatientAllergyBadge();

        // Add each medication to cart
        for (const item of rx.items) {
          window.posEngine.addToCart(item.medicine_id, item.quantity_prescribed);
        }

        // Switch to POS tab
        window.pharmApp.switchTab('pos');
        window.pharmApp.showToast(`Loaded Rx ${rx.rx_number} into POS cart for dispensing!`);
      }
    } catch (e) {
      console.error(e);
    }
  }

  resetForm() {
    const container = document.getElementById('rx-items-container');
    if (container) container.innerHTML = '';
  }

  async addRxRow() {
    const container = document.getElementById('rx-items-container');
    if (!container) return;

    if (this.allMedicines.length === 0) {
      const res = await window.pharmApp.fetchWithAuth('/api/inventory/medicines');
      const data = await res.json();
      if (data.success) this.allMedicines = data.medicines;
    }

    const medOptions = this.allMedicines.map(m => `
      <option value="${m.id}">${m.brand_name} (${m.generic_name}) - ${m.strength}</option>
    `).join('');

    const rowId = `rx-row-${Date.now()}`;
    const rowHtml = `
      <div id="${rowId}" style="display:grid; grid-template-columns: 2fr 2fr 1fr 1fr auto; gap:0.5rem; align-items:center; background:var(--bg-surface); padding:0.5rem; border-radius:var(--radius-md); border:1px solid var(--border-subtle);">
        <select class="form-select rx-item-med" style="font-size:0.85rem;">${medOptions}</select>
        <input type="text" class="form-input rx-item-instr" placeholder="Dosage (e.g. 1 tab bid pc)" style="font-size:0.85rem;">
        <input type="number" class="form-input rx-item-qty" placeholder="Qty" value="30" min="1" style="font-size:0.85rem;">
        <input type="number" class="form-input rx-item-refill" placeholder="Refills" value="1" min="0" style="font-size:0.85rem;">
        <button type="button" class="btn btn-secondary btn-icon btn-sm" onclick="document.getElementById('${rowId}').remove()" style="color:var(--danger);">✕</button>
      </div>
    `;
    container.insertAdjacentHTML('beforeend', rowHtml);
  }

  async submitPrescription() {
    const patientId = document.getElementById('rx-patient-select').value;
    const prescriberId = document.getElementById('rx-prescriber-select').value;
    const diagnosis = document.getElementById('rx-diagnosis-input').value.trim();

    const rows = document.querySelectorAll('#rx-items-container > div');
    const items = [];

    rows.forEach(r => {
      const medId = r.querySelector('.rx-item-med')?.value;
      const instr = r.querySelector('.rx-item-instr')?.value || 'As directed';
      const qty = parseInt(r.querySelector('.rx-item-qty')?.value) || 1;
      const refills = parseInt(r.querySelector('.rx-item-refill')?.value) || 0;
      if (medId) {
        items.push({
          medicine_id: parseInt(medId),
          dosage_instructions: instr,
          quantity_prescribed: qty,
          refills_allowed: refills
        });
      }
    });

    if (!patientId || !prescriberId || items.length === 0) {
      window.pharmApp.showToast('Please select patient, prescriber, and at least one medication', 'danger');
      return;
    }

    const payload = {
      patient_id: parseInt(patientId),
      prescriber_id: parseInt(prescriberId),
      diagnosis: diagnosis,
      items: items
    };

    try {
      const res = await window.pharmApp.fetchWithAuth('/api/prescriptions', {
        method: 'POST',
        body: payload
      });
      const data = await res.json();
      if (data.success) {
        window.pharmApp.showToast(data.message);
        window.pharmApp.closeModals();
        this.loadPrescriptions();
      } else {
        window.pharmApp.showToast(data.message, 'danger');
      }
    } catch (e) {
      console.error(e);
    }
  }
}

// Global instance
window.prescriptionEngine = new PrescriptionEngine();
