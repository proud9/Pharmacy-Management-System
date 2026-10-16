/**
 * PharmPulse Pro - Point of Sale (POS) & FEFO Dispensing Engine
 * Includes Live Barcode Scan, Automated Clinical Safety Checker (Interactions & Allergies),
 * Cart Calculation, Multi-Payment, and Thermal 80mm Receipt Generator.
 */

class POSEngine {
  constructor() {
    this.cart = [];
    this.catalog = [];
    this.selectedPatientId = null;
    this.selectedCategory = 'All';
    this.paymentMethod = 'Cash';
    this.audioContext = null;
    this.init();
  }

  init() {
    this.setupListeners();
    this.loadPatientsList();
  }

  // Audio synthesis feedback for barcode scan & checkout
  beep(frequency = 880, duration = 0.08) {
    try {
      if (!this.audioContext) {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      }
      const osc = this.audioContext.createOscillator();
      const gain = this.audioContext.createGain();
      osc.connect(gain);
      gain.connect(this.audioContext.destination);
      osc.frequency.value = frequency;
      gain.gain.setValueAtTime(0.15, this.audioContext.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + duration);
      osc.start();
      osc.stop(this.audioContext.currentTime + duration);
    } catch (e) {
      // Audio not permitted without interaction
    }
  }

  setupListeners() {
    // Search input (live search & barcode scanner support)
    const searchInput = document.getElementById('pos-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.renderCatalog();
      });

      // Barcode scanner hit 'Enter'
      searchInput.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          const query = searchInput.value.trim();
          if (query) {
            await this.handleBarcodeScan(query);
            searchInput.value = '';
          }
        }
      });
    }

    // Category pills
    document.querySelectorAll('.cat-pill').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.cat-pill').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.selectedCategory = btn.getAttribute('data-cat');
        this.renderCatalog();
      });
    });

    // Patient select change
    const patientSelect = document.getElementById('pos-patient-select');
    if (patientSelect) {
      patientSelect.addEventListener('change', (e) => {
        this.selectedPatientId = e.target.value ? parseInt(e.target.value) : null;
        this.updatePatientAllergyBadge();
        this.checkClinicalSafety();
      });
    }

    // Payment method buttons
    document.querySelectorAll('.pay-method-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.pay-method-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.paymentMethod = btn.getAttribute('data-method');

        const tenderWrap = document.getElementById('cash-tender-wrap');
        if (tenderWrap) {
          tenderWrap.style.display = this.paymentMethod === 'Cash' ? 'flex' : 'none';
        }
        this.calculateTotals();
      });
    });

    // Cash tendered input
    const tenderInput = document.getElementById('pos-amount-tendered');
    if (tenderInput) {
      tenderInput.addEventListener('input', () => {
        this.calculateTotals();
      });
    }
  }

  async loadCatalog() {
    try {
      const res = await window.pharmApp.fetchWithAuth('/api/inventory/medicines');
      const data = await res.json();
      if (data.success) {
        this.catalog = data.medicines;
        this.renderCatalog();
      }
    } catch (e) {
      console.error("Error loading POS catalog:", e);
    }
  }

  async loadPatientsList() {
    const select = document.getElementById('pos-patient-select');
    if (!select) return;
    try {
      const res = await window.pharmApp.fetchWithAuth('/api/records/patients');
      const data = await res.json();
      if (data.success) {
        this.patients = data.patients;
        select.innerHTML = '<option value="">-- Walk-in Outpatient (No Profile) --</option>' +
          data.patients.map(p => `
            <option value="${p.id}" data-allergies="${p.allergies || ''}">${p.full_name} (${p.patient_code})</option>
          `).join('');
      }
    } catch (e) {
      console.error(e);
    }
  }

  updatePatientAllergyBadge() {
    const badge = document.getElementById('pos-patient-allergy-summary');
    if (!badge) return;
    if (!this.selectedPatientId) {
      badge.style.display = 'none';
      return;
    }
    const pat = (this.patients || []).find(p => p.id === this.selectedPatientId);
    if (pat && pat.allergies && pat.allergies !== 'None Known') {
      badge.style.display = 'block';
      badge.textContent = `⚠ Documented Allergies: ${pat.allergies}`;
    } else {
      badge.style.display = 'none';
    }
  }

  renderCatalog() {
    const container = document.getElementById('pos-products-grid');
    if (!container) return;

    const searchTerm = (document.getElementById('pos-search-input')?.value || '').toLowerCase().trim();

    const filtered = this.catalog.filter(m => {
      const matchesCat = (this.selectedCategory === 'All') || (m.category === this.selectedCategory);
      const matchesSearch = !searchTerm ||
        m.brand_name.toLowerCase().includes(searchTerm) ||
        m.generic_name.toLowerCase().includes(searchTerm) ||
        m.sku.toLowerCase().includes(searchTerm) ||
        m.barcode.includes(searchTerm);
      return matchesCat && matchesSearch;
    });

    if (filtered.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1/-1; text-align:center; padding:3rem; color:var(--text-subtle);">
          <p style="font-weight:700;">No medications found matching filter.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = filtered.map(m => {
      const isRx = m.requires_prescription ? 'rx-required' : '';
      const inStock = m.total_stock > 0;
      return `
        <div class="pos-item-card ${isRx}" onclick="window.posEngine.addToCart(${m.id})" style="${!inStock ? 'opacity:0.55; pointer-events:none;' : ''}">
          <div class="pos-item-brand">${m.brand_name}</div>
          <div class="pos-item-generic">${m.generic_name} • ${m.strength}</div>
          <div class="pos-item-footer">
            <span class="pos-item-price">ZK ${m.unit_price.toFixed(2)}</span>
            <span class="pos-item-stock-tag">${m.total_stock} in stock</span>
          </div>
        </div>
      `;
    }).join('');
  }

  async handleBarcodeScan(barcode) {
    try {
      const res = await window.pharmApp.fetchWithAuth(`/api/inventory/barcode/${barcode}`);
      const data = await res.json();
      if (data.success && data.medicine) {
        this.beep(1200, 0.1);
        this.addToCart(data.medicine.id);
        window.pharmApp.showToast(`Scanned: ${data.medicine.brand_name}`);
      } else {
        this.beep(300, 0.2);
        window.pharmApp.showToast(`Barcode ${barcode} not found`, 'danger');
      }
    } catch (e) {
      console.error(e);
    }
  }

  addToCart(medId, requestedQty = 1) {
    const med = this.catalog.find(m => m.id === medId);
    if (!med) return;

    if (med.total_stock <= 0) {
      window.pharmApp.showToast(`${med.brand_name} is out of stock!`, 'danger');
      return;
    }

    const existing = this.cart.find(c => c.medicine.id === medId);
    if (existing) {
      if (existing.quantity + requestedQty > med.total_stock) {
        window.pharmApp.showToast(`Cannot exceed total available stock (${med.total_stock} units)`, 'warning');
        return;
      }
      existing.quantity += requestedQty;
    } else {
      this.cart.push({
        medicine: med,
        quantity: requestedQty
      });
    }

    this.beep(880, 0.05);
    this.renderCart();
    this.checkClinicalSafety();
  }

  updateQuantity(medId, delta) {
    const item = this.cart.find(c => c.medicine.id === medId);
    if (!item) return;

    const newQty = item.quantity + delta;
    if (newQty <= 0) {
      this.removeFromCart(medId);
      return;
    }

    if (newQty > item.medicine.total_stock) {
      window.pharmApp.showToast(`Only ${item.medicine.total_stock} units available in stock`, 'warning');
      return;
    }

    item.quantity = newQty;
    this.renderCart();
  }

  removeFromCart(medId) {
    this.cart = this.cart.filter(c => c.medicine.id !== medId);
    this.renderCart();
    this.checkClinicalSafety();
  }

  clearCart() {
    this.cart = [];
    this.renderCart();
    this.clearSafetyAlerts();
  }

  renderCart() {
    const container = document.getElementById('pos-cart-items-list');
    const countBadge = document.getElementById('pos-cart-item-count');
    if (!container) return;

    const totalItems = this.cart.reduce((sum, item) => sum + item.quantity, 0);
    if (countBadge) countBadge.textContent = `${totalItems} items (${this.cart.length} lines)`;

    if (this.cart.length === 0) {
      container.innerHTML = `
        <div style="text-align:center; padding:3rem 1rem; color:var(--text-subtle);">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom:0.75rem; opacity:0.5;"><circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"/></svg>
          <p style="font-weight:600; font-size:0.9rem;">Cart is currently empty</p>
          <p style="font-size:0.78rem;">Click medications on the left or scan barcode to add to dispense queue.</p>
        </div>
      `;
      this.calculateTotals();
      return;
    }

    container.innerHTML = this.cart.map(item => {
      const lineTotal = item.medicine.unit_price * item.quantity;
      return `
        <div class="pos-cart-item">
          <div class="cart-item-details">
            <div class="cart-item-name">${item.medicine.brand_name}</div>
            <div class="cart-item-sub">${item.medicine.generic_name} • ZK ${item.medicine.unit_price.toFixed(2)}/ea</div>
          </div>
          <div class="cart-qty-control">
            <button class="cart-qty-btn" onclick="window.posEngine.updateQuantity(${item.medicine.id}, -1)">-</button>
            <span class="cart-qty-num">${item.quantity}</span>
            <button class="cart-qty-btn" onclick="window.posEngine.updateQuantity(${item.medicine.id}, 1)">+</button>
          </div>
          <div class="cart-item-total">ZK ${lineTotal.toFixed(2)}</div>
          <button class="btn btn-secondary btn-icon btn-sm" onclick="window.posEngine.removeFromCart(${item.medicine.id})" title="Remove item" style="color:var(--danger);">✕</button>
        </div>
      `;
    }).join('');

    this.calculateTotals();
  }

  calculateTotals() {
    const subtotal = this.cart.reduce((sum, item) => sum + (item.medicine.unit_price * item.quantity), 0);
    const discount = 0.0;
    const tax = Math.round((subtotal - discount) * 0.04 * 100) / 100;
    const total = subtotal - discount + tax;

    const subEl = document.getElementById('pos-subtotal');
    const discEl = document.getElementById('pos-discount');
    const taxEl = document.getElementById('pos-tax');
    const grandEl = document.getElementById('pos-grand-total');

    if (subEl) subEl.textContent = `ZK ${subtotal.toFixed(2)}`;
    if (discEl) discEl.textContent = `ZK ${discount.toFixed(2)}`;
    if (taxEl) taxEl.textContent = `ZK ${tax.toFixed(2)}`;
    if (grandEl) grandEl.textContent = `ZK ${total.toFixed(2)}`;

    // Calculate Cash Change Due
    const tenderInput = document.getElementById('pos-amount-tendered');
    const changeDueEl = document.getElementById('pos-change-due');
    if (tenderInput && changeDueEl) {
      const tendered = parseFloat(tenderInput.value) || 0;
      const change = Math.max(0, tendered - total);
      changeDueEl.textContent = `ZK ${change.toFixed(2)}`;
    }
  }

  // ==========================================
  // CLINICAL DRUG SAFETY CHECKER
  // ==========================================
  async checkClinicalSafety() {
    if (this.cart.length === 0) {
      this.clearSafetyAlerts();
      return;
    }

    const payload = {
      items: this.cart.map(c => ({ medicine_id: c.medicine.id })),
      patient_id: this.selectedPatientId
    };

    try {
      const res = await window.pharmApp.fetchWithAuth('/api/pos/check-safety', {
        method: 'POST',
        body: payload
      });
      const data = await res.json();
      if (data.success && data.has_warnings) {
        this.renderSafetyAlerts(data.warnings);
        this.beep(400, 0.25);
      } else {
        this.clearSafetyAlerts();
      }
    } catch (e) {
      console.error("Clinical safety check error:", e);
    }
  }

  renderSafetyAlerts(warnings) {
    const container = document.getElementById('clinical-safety-alert-container');
    if (!container) return;

    container.innerHTML = warnings.map(w => `
      <div class="clinical-alert-box">
        <div class="clinical-alert-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>
          <span>${w.title}</span>
        </div>
        <div class="clinical-alert-body">${w.message}</div>
        ${w.recommendation ? `<div style="font-size:0.75rem; color:var(--text-muted); font-style:italic;">Recommendation: ${w.recommendation}</div>` : ''}
      </div>
    `).join('');
  }

  clearSafetyAlerts() {
    const container = document.getElementById('clinical-safety-alert-container');
    if (container) container.innerHTML = '';
  }

  // ==========================================
  // CHECKOUT & RECEIPT PRINTING
  // ==========================================
  async processCheckout() {
    if (this.cart.length === 0) {
      window.pharmApp.showToast('Please add items to cart before checkout', 'warning');
      return;
    }

    const subtotal = this.cart.reduce((sum, item) => sum + (item.medicine.unit_price * item.quantity), 0);
    const tax = Math.round(subtotal * 0.04 * 100) / 100;
    const total = subtotal + tax;

    const tenderInput = document.getElementById('pos-amount-tendered');
    const tendered = this.paymentMethod === 'Cash' ? (parseFloat(tenderInput?.value) || total) : total;

    if (this.paymentMethod === 'Cash' && tendered < total) {
      window.pharmApp.showToast(`Amount tendered (ZK ${tendered.toFixed(2)}) is less than total (ZK ${total.toFixed(2)})`, 'danger');
      return;
    }

    const payload = {
      items: this.cart.map(c => ({
        medicine_id: c.medicine.id,
        quantity: c.quantity,
        unit_price: c.medicine.unit_price
      })),
      patient_id: this.selectedPatientId,
      payment_method: this.paymentMethod,
      amount_paid: tendered,
      notes: 'Outpatient POS Dispense'
    };

    const checkoutBtn = document.getElementById('pos-checkout-btn');
    if (checkoutBtn) checkoutBtn.disabled = true;

    try {
      const res = await window.pharmApp.fetchWithAuth('/api/pos/checkout', {
        method: 'POST',
        body: payload
      });
      const data = await res.json();

      if (data.success) {
        this.beep(1600, 0.15);
        window.pharmApp.showToast(`Dispensing Complete! Invoice: ${data.invoice_number}`);
        this.showReceipt(data);
        this.clearCart();
        // Refresh catalog quantities
        this.loadCatalog();
      } else {
        window.pharmApp.showToast(data.message || 'Checkout failed', 'danger');
      }
    } catch (e) {
      console.error(e);
      window.pharmApp.showToast('Server error during checkout', 'danger');
    } finally {
      if (checkoutBtn) checkoutBtn.disabled = false;
    }
  }

  showReceipt(saleData) {
    const modalContent = document.getElementById('receipt-preview-content');
    const printContainer = document.getElementById('printable-receipt-container');

    const patientName = this.selectedPatientId ? 
      (this.patients?.find(p => p.id === this.selectedPatientId)?.full_name || 'Registered Patient') : 'Walk-in Outpatient';

    const itemsHtml = saleData.allocations.map(m => {
      return m.allocations.map(a => `
        <tr>
          <td>${m.brand_name} (Lot: ${a.batch_number})</td>
          <td style="text-align:center;">${a.quantity}</td>
          <td style="text-align:right;">ZK ${a.unit_price.toFixed(2)}</td>
          <td style="text-align:right;">ZK ${a.total_price.toFixed(2)}</td>
        </tr>
      `).join('');
    }).join('');

    const receiptHtml = `
      <div class="receipt-thermal">
        <div class="receipt-header">
          <div class="receipt-pharmacy-name">PharmPulse Enterprise Rx Zambia</div>
          <div class="receipt-info-line">Lic: #ZAMRA-COMM-9941 • 24/7 Pharmacy</div>
          <div class="receipt-info-line">Plot 10444, Off Mungwi Road, Lusaka, Zambia</div>
          <div class="receipt-info-line">Tel: +260-211-286411 • Mobile: +260-977-102030</div>
        </div>

        <div class="receipt-meta">
          <span>Inv: ${saleData.invoice_number}</span>
          <span>${new Date().toLocaleDateString()}</span>
        </div>
        <div class="receipt-meta">
          <span>Patient: ${patientName}</span>
          <span>Cashier: ${window.pharmApp.currentUser?.full_name || 'Staff'}</span>
        </div>

        <table class="receipt-table">
          <thead>
            <tr>
              <th>Item / Batch</th>
              <th style="text-align:center;">Qty</th>
              <th style="text-align:right;">Price</th>
              <th style="text-align:right;">Total</th>
            </tr>
          </thead>
          <tbody>
            ${itemsHtml}
          </tbody>
        </table>

        <div class="receipt-totals">
          <div class="receipt-line">
            <span>Subtotal:</span>
            <span>ZK ${saleData.subtotal.toFixed(2)}</span>
          </div>
          <div class="receipt-line">
            <span>Sales Tax (4%):</span>
            <span>ZK ${saleData.tax_amount.toFixed(2)}</span>
          </div>
          <div class="receipt-line bold">
            <span>GRAND TOTAL:</span>
            <span>ZK ${saleData.total_amount.toFixed(2)}</span>
          </div>
          <div class="receipt-line">
            <span>Paid (${saleData.payment_method}):</span>
            <span>ZK ${saleData.amount_paid.toFixed(2)}</span>
          </div>
          <div class="receipt-line">
            <span>Change Due:</span>
            <span>ZK ${saleData.change_due.toFixed(2)}</span>
          </div>
        </div>

        <div class="receipt-barcode">
          *${saleData.invoice_number}*
        </div>

        <div class="receipt-footer-msg">
          Thank you for choosing PharmPulse Zambia!<br>
          Licensed medication dispensed per ZAMRA & HPCZ regulations.
        </div>
      </div>
    `;

    if (modalContent) modalContent.innerHTML = receiptHtml;
    if (printContainer) printContainer.innerHTML = receiptHtml;

    window.pharmApp.openModal('modal-receipt');
  }
}

// Global instance
window.posEngine = new POSEngine();
