/**
 * PharmPulse Pro - Core Application Controller
 * Handles SPA tab routing, JWT authentication state, demo persona switcher,
 * modal triggers, theme switching, keyboard shortcuts, and UI toasts.
 */

class PharmApp {
  constructor() {
    this.token = localStorage.getItem('pharmpulse_token') || null;
    this.currentUser = JSON.parse(localStorage.getItem('pharmpulse_user') || 'null');
    this.currentTab = 'dashboard';
    this.currency = 'ZK';
    this.init();
  }

  formatCurrency(amount) {
    const val = Number(amount || 0);
    return `ZK ${val.toFixed(2)}`;
  }

  async init() {
    this.setupTheme();
    this.setupNavigation();
    this.setupKeyboardShortcuts();
    this.setupRoleSwitcher();

    // If no token or user, automatically switch to admin demo persona
    if (!this.token || !this.currentUser) {
      await this.switchPersona('admin');
    } else {
      this.updateUserUI();
    }

    // Load initial view
    this.switchTab('dashboard');
  }

  // ==========================================
  // THEME MANAGEMENT
  // ==========================================
  setupTheme() {
    const savedTheme = localStorage.getItem('pharmpulse_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    this.updateThemeIcons(savedTheme);

    const toggleBtn = document.getElementById('theme-toggle-btn');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('pharmpulse_theme', next);
        this.updateThemeIcons(next);
      });
    }
  }

  updateThemeIcons(theme) {
    const moon = document.getElementById('theme-moon-icon');
    const sun = document.getElementById('theme-sun-icon');
    if (moon && sun) {
      if (theme === 'dark') {
        moon.style.display = 'block';
        sun.style.display = 'none';
      } else {
        moon.style.display = 'none';
        sun.style.display = 'block';
      }
    }
  }

  // ==========================================
  // SPA ROUTING & NAVIGATION
  // ==========================================
  setupNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        const tab = item.getAttribute('data-tab');
        if (tab) this.switchTab(tab);
      });
    });
  }

  switchTab(tabName) {
    this.currentTab = tabName;

    // Update sidebar active link
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    const activeNav = document.getElementById(`nav-${tabName}`);
    if (activeNav) activeNav.classList.add('active');

    // Update tab panes
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    const targetPane = document.getElementById(`view-${tabName}`);
    if (targetPane) targetPane.classList.add('active');

    // Update View Title
    const titleEl = document.getElementById('view-title');
    const subtitleEl = document.getElementById('view-subtitle');

    const headers = {
      dashboard: { title: 'Dashboard Overview', sub: 'Real-time commercial pharmacy performance & clinical alerts' },
      pos: { title: 'Point of Sale & Dispensing Terminal', sub: 'First-Expired-First-Out dispensing & automated clinical safety check' },
      inventory: { title: 'Pharmaceutical Catalog & Batches', sub: 'Batch tracking, expiry radar, and automated stock alerts' },
      stocktake: { title: 'Physical Inventory Cycle Audit', sub: 'Barcode count reconciliation and instant variance adjustment' },
      prescriptions: { title: 'Digital E-Prescription Queue', sub: 'Pharmacist clinical verification & direct-to-cart dispensing' },
      patients: { title: 'Patient Medical Database', sub: 'Allergy contraindications, chronic condition profiles, and insurance' },
      prescribers: { title: 'Prescribing Doctors Directory', sub: 'Medical licenses, clinic affiliations, and prescription history' },
      suppliers: { title: 'Pharmaceutical Supply Vendors', sub: 'Distributor lead times, contacts, and purchase orders' },
      analytics: { title: 'Financial Intelligence & BI', sub: 'Revenue forecasting, gross profit margins, and dead stock reports' },
      admin: { title: 'Remote Access & Security Audit', sub: 'Active remote terminal sessions and tamper-evident audit trail' }
    };

    if (headers[tabName]) {
      if (titleEl) titleEl.textContent = headers[tabName].title;
      if (subtitleEl) subtitleEl.textContent = headers[tabName].sub;
    }

    // Refresh view data
    this.refreshCurrentView(tabName);
  }

  refreshCurrentView(tabName) {
    if (tabName === 'dashboard') {
      if (window.analyticsEngine) window.analyticsEngine.loadDashboardKPIs();
    } else if (tabName === 'pos') {
      if (window.posEngine) window.posEngine.loadCatalog();
    } else if (tabName === 'inventory') {
      if (window.inventoryEngine) window.inventoryEngine.loadInventory();
    } else if (tabName === 'stocktake') {
      if (window.stocktakeEngine) window.stocktakeEngine.loadAudits();
    } else if (tabName === 'prescriptions') {
      if (window.prescriptionEngine) window.prescriptionEngine.loadPrescriptions();
    } else if (tabName === 'patients') {
      if (window.recordsEngine) window.recordsEngine.loadPatients();
    } else if (tabName === 'prescribers') {
      if (window.recordsEngine) window.recordsEngine.loadPrescribers();
    } else if (tabName === 'suppliers') {
      if (window.recordsEngine) window.recordsEngine.loadSuppliers();
    } else if (tabName === 'analytics') {
      if (window.analyticsEngine) window.analyticsEngine.loadCharts();
    } else if (tabName === 'admin') {
      if (window.adminEngine) window.adminEngine.loadAdminData();
    }
  }

  // ==========================================
  // PERSONA & ROLE SWITCHER
  // ==========================================
  setupRoleSwitcher() {
    const select = document.getElementById('demo-role-select');
    if (!select) return;

    if (this.currentUser) {
      select.value = this.currentUser.username;
    }

    select.addEventListener('change', async (e) => {
      const username = e.target.value;
      await this.switchPersona(username);
    });
  }

  async switchPersona(username) {
    try {
      const res = await fetch(`/api/auth/switch-demo-user/${username}`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        this.token = data.token;
        this.currentUser = data.user;
        localStorage.setItem('pharmpulse_token', data.token);
        localStorage.setItem('pharmpulse_user', JSON.stringify(data.user));
        this.updateUserUI();
        this.showToast(`Switched persona to ${data.user.full_name} (${data.user.role.toUpperCase()})`, 'info');
        this.refreshCurrentView(this.currentTab);
      }
    } catch (err) {
      console.error("Failed to switch persona:", err);
    }
  }

  updateUserUI() {
    if (!this.currentUser) return;
    const nameEl = document.getElementById('sidebar-user-name');
    const roleEl = document.getElementById('sidebar-user-role');
    const avatarEl = document.getElementById('sidebar-avatar');

    if (nameEl) nameEl.textContent = this.currentUser.full_name;
    if (roleEl) roleEl.textContent = this.currentUser.role.replace('_', ' ');
    if (avatarEl) {
      const initials = this.currentUser.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
      avatarEl.textContent = initials;
    }
  }

  // ==========================================
  // HTTP FETCH HELPER (With Auth Header)
  // ==========================================
  async fetchWithAuth(url, options = {}) {
    options.headers = options.headers || {};
    if (this.token) {
      options.headers['Authorization'] = `Bearer ${this.token}`;
    }
    if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(options.body);
    }
    const res = await fetch(url, options);
    return res;
  }

  // ==========================================
  // KEYBOARD SHORTCUTS
  // ==========================================
  setupKeyboardShortcuts() {
    window.addEventListener('keydown', (e) => {
      // F2 -> Open POS
      if (e.key === 'F2') {
        e.preventDefault();
        this.switchTab('pos');
      }
      // F3 -> Focus Search
      if (e.key === 'F3') {
        e.preventDefault();
        const searchInput = document.getElementById('pos-search-input') || document.getElementById('inventory-search-input');
        if (searchInput) searchInput.focus();
      }
      // Escape -> Close Modals
      if (e.key === 'Escape') {
        this.closeModals();
      }
    });
  }

  // ==========================================
  // MODAL CONTROLLERS
  // ==========================================
  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('active');
  }

  closeModals() {
    document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
  }

  openNewMedicineModal() {
    this.openModal('modal-medicine');
  }

  async openNewBatchModal() {
    // Populate medication and supplier selects
    const medSelect = document.getElementById('batch-med-select');
    const supSelect = document.getElementById('batch-supplier-select');

    try {
      const [medRes, supRes] = await Promise.all([
        this.fetchWithAuth('/api/inventory/medicines'),
        this.fetchWithAuth('/api/records/suppliers')
      ]);
      const medData = await medRes.json();
      const supData = await supRes.json();

      if (medSelect && medData.medicines) {
        medSelect.innerHTML = medData.medicines.map(m => `
          <option value="${m.id}">${m.brand_name} (${m.generic_name}) - SKU: ${m.sku}</option>
        `).join('');
      }

      if (supSelect && supData.suppliers) {
        supSelect.innerHTML = supData.suppliers.map(s => `
          <option value="${s.id}">${s.name} (${s.code})</option>
        `).join('');
      }
    } catch (e) {
      console.error("Error loading batch selects:", e);
    }

    this.openModal('modal-batch');
  }

  async openNewPrescriptionModal() {
    const patSelect = document.getElementById('rx-patient-select');
    const docSelect = document.getElementById('rx-prescriber-select');

    try {
      const [patRes, docRes] = await Promise.all([
        this.fetchWithAuth('/api/records/patients'),
        this.fetchWithAuth('/api/records/prescribers')
      ]);
      const patData = await patRes.json();
      const docData = await docRes.json();

      if (patSelect && patData.patients) {
        patSelect.innerHTML = patData.patients.map(p => `
          <option value="${p.id}">${p.full_name} (${p.patient_code}) - Allergies: ${p.allergies || 'None'}</option>
        `).join('');
      }

      if (docSelect && docData.prescribers) {
        docSelect.innerHTML = docData.prescribers.map(d => `
          <option value="${d.id}">${d.full_name} (${d.hospital_clinic || 'Private Practice'})</option>
        `).join('');
      }

      // Add first medication row
      if (window.prescriptionEngine) {
        window.prescriptionEngine.resetForm();
        window.prescriptionEngine.addRxRow();
      }
    } catch (e) {
      console.error(e);
    }

    this.openModal('modal-prescription');
  }

  openNewPatientModal() {
    this.openModal('modal-patient');
  }

  // ==========================================
  // TOAST NOTIFICATIONS
  // ==========================================
  showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.style.cssText = 'position:fixed; bottom:20px; right:20px; z-index:9999; display:flex; flex-direction:column; gap:8px;';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bg = type === 'danger' ? 'var(--danger)' : (type === 'warning' ? 'var(--warning)' : 'var(--primary)');
    toast.style.cssText = `background:${bg}; color:white; padding:10px 18px; border-radius:8px; font-weight:700; font-size:13px; box-shadow:0 4px 15px rgba(0,0,0,0.3); animation:fadeIn 0.2s ease-out;`;
    toast.textContent = message;

    container.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 3800);
  }

  exportCsv(type) {
    window.location.href = `/api/reports/export-csv?type=${type}&token=${this.token}`;
  }
}

// Global instance
window.pharmApp = new PharmApp();
