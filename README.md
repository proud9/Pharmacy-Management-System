# PharmPulse Pro — Commercial Pharmacy Management & BI System

An enterprise-grade, modern commercial pharmacy management platform featuring **digitalized medical records**, **role-based remote login**, **FEFO inventory taking & batch tracking**, **business intelligence & financial statistics**, **real-time clinical interaction checks**, and a **high-speed Point of Sale (POS)** terminal.

---

## 🌟 Key Features

### 1. 🔐 Remote Access & Role-Based Access Control (RBAC)
- **Multi-Device & Remote Sessions**: Remote login over web/LAN with SHA-256 JWT tokens.
- **Role Hierarchy**:
  - `admin` (Elena Vance, PharmD — Super Admin): Full access, financial analytics, user management, audit logs.
  - `pharmacist` (Dr. Sarah Jenkins — Chief Pharmacist): Clinical verification, prescription sign-off, controlled substances.
  - `dispenser` (Marcus Thorne — Dispensing Tech): Prescription handling, stock intake.
  - `cashier` (Jenny Lind — POS Cashier): Point of sale, split tenders, receipt printing.
  - `inventory_manager` (Alex Rivera — Inventory Controller): Cycle audits, batch entries, waste write-offs.
- **Active Session Monitor & Remote Revocation**: Terminate compromised or unauthorized remote sessions instantly.
- **One-Click Persona Switcher**: Test any role perspective directly in the app bar.

### 2. 💊 First-Expired, First-Out (FEFO) Inventory & Expiry Radar
- **Automated Batch Allocation**: When dispensing, the system automatically pulls stock from the earliest-expiring active batch first.
- **Shelf-Life Risk Radar**:
  - `Critical (< 30 days)`: Red warning tag with automated markdowns or return alerts.
  - `Approaching (31–90 days)`: Amber warning.
  - `Healthy (> 90 days)`: Green status.
- **Batch Management**: Lot numbers, manufacture dates, expiry dates, supplier linkages, and purchase costs.
- **Stock Adjustments**: Record damaged blister packs, expired stock safe disposals, and supplier returns with reasons.

### 3. 🛡️ Clinical Drug Safety & Allergy Contraindication Engine
- **Drug-to-Drug Interaction Matrix**: Checks cart items pairwise in real-time (e.g. Warfarin + Ibuprofen/Aspirin bleeding hazard, Lisinopril + Spironolactone hyperkalemia warning).
- **Patient Allergy Cross-Check**: Automatically cross-references medications against the customer's allergy profile (e.g. Penicillin allergy vs. Amoxil/Augmentin).
- **Pharmacist Clinical Alerts**: Displays severity levels (Major, Moderate, Minor) and required clinical actions.

### 4. ⚡ High-Speed Point of Sale (POS) Terminal
- **Instant Search & Barcode Scan**: USB barcode scanner or live SKU search.
- **Therapeutic Category Filtering**: Antibiotics, Cardiovascular, Analgesics, Antidiabetic, Gastrointestinal, Controlled.
- **Multi-Tender Payments**: Cash (with live change calculator), Credit Card, Health Insurance Co-pay, and Mobile Money.
- **80mm Thermal Receipt & A4 Printing**: Generates clean printable receipts with itemized batches, tax, and barcodes.

### 5. 📋 Physical Stock Taking & Cycle Count Audits
- **Digital Audit Sheets**: Pre-populated with system expected quantities.
- **Instant Variance Detection**: Real-time comparison between physical count and system count.
- **Financial Valuation of Discrepancies**: Net gain or loss calculated automatically based on unit costs.
- **One-Click Auto-Reconcile**: Updates live inventory and logs immutable audit records.

### 6. 📑 Digital E-Prescription Queue
- **Prescription Workflow**: Pending Verification ➔ Pharmacist Approved ➔ Dispensed.
- **Direct-to-POS Dispatch**: Transfer verified prescription items and dosage into the POS cart with 1 click.
- **Refill Tracking**: Refills remaining, dosage instructions, and doctor medical license sign-off.

### 7. 📈 Business Intelligence & Predictive Analytics
- **Executive KPIs**: Today's Revenue, Revenue Growth %, Cumulative Gross Profit, Profit Margin %, Low Stock Count.
- **14-Day Sales & Margin Trajectory**: Custom interactive SVG area/line chart.
- **Expiry Risk Financial Matrix**: Zambian Kwacha (ZK) value of inventory approaching expiration.
- **Category & Payment Distribution**: Therapeutic sales breakdown and payment gateway share.
- **CSV Data Export**: Export Inventory, Sales Transactions, and Security Audit logs.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+ (Python 3.13 tested)

### Starting the Server
Run the one-click batch launcher:
```cmd
run.bat
```
Or run directly from terminal:
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 👥 Pre-Configured Demo Credentials

| Username | Password | Role | Full Name |
| :--- | :--- | :--- | :--- |
| `admin` | `admin123` | Super Admin | Elena Vance, PharmD |
| `dr_sarah` | `pharma123` | Chief Pharmacist | Dr. Sarah Jenkins |
| `marcus_disp` | `dispense123` | Dispenser | Marcus Thorne |
| `jenny_cash` | `cash123` | POS Cashier | Jenny Lind |
| `alex_inv` | `stock123` | Inventory Controller | Alex Rivera |

*(You can also use the interactive **Persona dropdown** in the top navigation bar to switch roles instantly without re-logging in)*

---

## ⌨️ Global Keyboard Shortcuts

- `F2`: Instantly jump to Point of Sale (POS) Dispense
- `F3`: Focus Medication / Barcode Search Input
- `Esc`: Close any active modal dialog
