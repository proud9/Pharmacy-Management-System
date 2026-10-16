/**
 * PharmPulse Pro - Records Management Controller
 * Manages directories for Patients (with allergy profiles), Doctors, and Suppliers.
 */

class RecordsEngine {
  constructor() {
    this.patients = [];
    this.prescribers = [];
    this.suppliers = [];
    this.init();
  }

  init() {
    const patSearch = document.getElementById('patients-search-input');
    if (patSearch) {
      patSearch.addEventListener('input', () => this.loadPatients());
    }
  }

  // ==========================================
  // PATIENTS
  // ==========================================
  async loadPatients() {
    const search = document.getElementById('patients-search-input')?.value || '';
    try {
      const res = await window.pharmApp.fetchWithAuth(`/api/records/patients?search=${encodeURIComponent(search)}`);
      const data = await res.json();
      if (data.success) {
        this.patients = data.patients;
        this.renderPatients();
      }
    } catch (e) {
      console.error(e);
    }
  }

  renderPatients() {
    const tbody = document.getElementById('patients-tbody');
    if (!tbody) return;

    if (this.patients.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:2.5rem; color:var(--text-subtle);">No patients registered.</td></tr>`;
      return;
    }

    tbody.innerHTML = this.patients.map(p => {
      const hasAllergy = p.allergies && p.allergies !== 'None Known' && p.allergies !== 'None';
      const allergyBadge = hasAllergy ? 
        `<span class="badge badge-danger" title="${p.allergies}">⚠ ${p.allergies}</span>` : `<span class="badge badge-success">None Known</span>`;

      return `
        <tr>
          <td style="font-weight:700; font-family:var(--font-mono);">${p.patient_code}</td>
          <td style="font-weight:700; color:var(--text-main);">${p.full_name}</td>
          <td style="font-size:0.82rem;">${p.date_of_birth || 'N/A'} (${p.gender})</td>
          <td style="font-family:var(--font-mono); font-size:0.85rem;">${p.phone || 'N/A'}</td>
          <td>${allergyBadge}</td>
          <td style="font-size:0.82rem; color:var(--text-muted);">${p.chronic_conditions || 'None'}</td>
          <td style="font-size:0.82rem;">${p.insurance_provider ? `${p.insurance_provider} (${p.insurance_policy_number})` : 'Self Pay'}</td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="window.recordsEngine.selectForPOS(${p.id})">Select for POS</button>
          </td>
        </tr>
      `;
    }).join('');
  }

  selectForPOS(patientId) {
    window.pharmApp.switchTab('pos');
    const select = document.getElementById('pos-patient-select');
    if (select) {
      select.value = patientId;
      window.posEngine.selectedPatientId = patientId;
      window.posEngine.updatePatientAllergyBadge();
      window.posEngine.checkClinicalSafety();
    }
  }

  async submitPatient() {
    const name = document.getElementById('patient-name').value.trim();
    const dob = document.getElementById('patient-dob').value;
    const gender = document.getElementById('patient-gender').value;
    const phone = document.getElementById('patient-phone').value.trim();
    const email = document.getElementById('patient-email').value.trim();
    const allergies = document.getElementById('patient-allergies').value.trim();
    const conditions = document.getElementById('patient-conditions').value.trim();
    const insurance = document.getElementById('patient-insurance').value.trim();
    const policy = document.getElementById('patient-policy').value.trim();

    if (!name) {
      window.pharmApp.showToast('Full name is required', 'danger');
      return;
    }

    const payload = {
      full_name: name,
      date_of_birth: dob,
      gender: gender,
      phone: phone,
      email: email,
      allergies: allergies || 'None Known',
      chronic_conditions: conditions || 'None',
      insurance_provider: insurance,
      insurance_policy_number: policy
    };

    try {
      const res = await window.pharmApp.fetchWithAuth('/api/records/patients', {
        method: 'POST',
        body: payload
      });
      const data = await res.json();
      if (data.success) {
        window.pharmApp.showToast(data.message);
        window.pharmApp.closeModals();
        this.loadPatients();
        // Refresh POS patient dropdown
        if (window.posEngine) window.posEngine.loadPatientsList();
      } else {
        window.pharmApp.showToast(data.message, 'danger');
      }
    } catch (e) {
      console.error(e);
    }
  }

  // ==========================================
  // PRESCRIBERS
  // ==========================================
  async loadPrescribers() {
    try {
      const res = await window.pharmApp.fetchWithAuth('/api/records/prescribers');
      const data = await res.json();
      if (data.success) {
        this.prescribers = data.prescribers;
        this.renderPrescribers();
      }
    } catch (e) {
      console.error(e);
    }
  }

  renderPrescribers() {
    const tbody = document.getElementById('prescribers-tbody');
    if (!tbody) return;

    if (this.prescribers.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:2rem;">No doctors registered.</td></tr>`;
      return;
    }

    tbody.innerHTML = this.prescribers.map(d => `
      <tr>
        <td style="font-weight:700;">${d.full_name}</td>
        <td style="font-family:var(--font-mono); font-size:0.85rem;">${d.license_number}</td>
        <td>${d.hospital_clinic}</td>
        <td><span class="badge badge-info">${d.specialization}</span></td>
        <td style="font-family:var(--font-mono);">${d.phone || '—'}</td>
        <td style="font-size:0.82rem; color:var(--text-muted);">${d.email || '—'}</td>
      </tr>
    `).join('');
  }

  openNewPrescriberModal() {
    const name = prompt("Physician Full Name (e.g. Dr. Jane Smith, MD):");
    if (!name) return;
    const lic = prompt("Medical Board License Number (e.g. MD-LIC-99120):");
    if (!lic) return;
    const clinic = prompt("Hospital or Clinic Affiliation:", "Metropolitan Medical Center");
    const spec = prompt("Medical Specialty:", "General Practice");

    window.pharmApp.fetchWithAuth('/api/records/prescribers', {
      method: 'POST',
      body: { full_name: name, license_number: lic, hospital_clinic: clinic, specialization: spec }
    }).then(res => res.json()).then(data => {
      if (data.success) {
        window.pharmApp.showToast(data.message);
        this.loadPrescribers();
      } else {
        window.pharmApp.showToast(data.message, 'danger');
      }
    });
  }

  // ==========================================
  // SUPPLIERS
  // ==========================================
  async loadSuppliers() {
    try {
      const res = await window.pharmApp.fetchWithAuth('/api/records/suppliers');
      const data = await res.json();
      if (data.success) {
        this.suppliers = data.suppliers;
        this.renderSuppliers();
      }
    } catch (e) {
      console.error(e);
    }
  }

  renderSuppliers() {
    const tbody = document.getElementById('suppliers-tbody');
    if (!tbody) return;

    if (this.suppliers.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:2rem;">No suppliers registered.</td></tr>`;
      return;
    }

    tbody.innerHTML = this.suppliers.map(s => `
      <tr>
        <td>
          <div style="font-weight:700;">${s.name}</div>
          <div style="font-size:0.75rem; color:var(--text-muted); font-family:var(--font-mono);">${s.code}</div>
        </td>
        <td style="font-weight:600;">${s.contact_person || 'Logistics Desk'}</td>
        <td style="font-size:0.82rem;">${s.phone}<br><span style="color:var(--text-subtle);">${s.email}</span></td>
        <td style="font-size:0.82rem; color:var(--text-muted);">${s.address}</td>
        <td><span class="badge badge-info">${s.lead_time_days} days</span></td>
        <td><span class="badge badge-success">${s.payment_terms}</span></td>
      </tr>
    `).join('');
  }

  openNewSupplierModal() {
    const name = prompt("Enter Supplier Company Name:");
    if (!name) return;
    const contact = prompt("Contact Person Name:");
    const email = prompt("Orders Email Address:");
    const phone = prompt("Telephone / Dispatch Line:");

    window.pharmApp.fetchWithAuth('/api/records/suppliers', {
      method: 'POST',
      body: { name: name, contact_person: contact, email: email, phone: phone }
    }).then(res => res.json()).then(data => {
      if (data.success) {
        window.pharmApp.showToast(data.message);
        this.loadSuppliers();
      } else {
        window.pharmApp.showToast(data.message, 'danger');
      }
    });
  }
}

// Global instance
window.recordsEngine = new RecordsEngine();
