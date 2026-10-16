"""
PharmPulse Pro - Commercial Pharmacy Management System
Database initialization, schema creation, and database connection helpers.
"""

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pharmacy.db")

def get_db():
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db():
    """Initialize all tables required for the commercial pharmacy management system."""
    conn = get_db()
    cursor = conn.cursor()

    # 1. Users / Staff Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'pharmacist', 'dispenser', 'cashier', 'inventory_manager')),
        license_number TEXT,
        email TEXT,
        phone TEXT,
        is_active INTEGER DEFAULT 1,
        last_login TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Remote Sessions & Login Audit Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT UNIQUE NOT NULL,
        ip_address TEXT,
        user_agent TEXT,
        device_type TEXT,
        login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # 3. Suppliers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT UNIQUE NOT NULL,
        contact_person TEXT,
        email TEXT,
        phone TEXT,
        address TEXT,
        lead_time_days INTEGER DEFAULT 3,
        payment_terms TEXT DEFAULT 'Net 30',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. Medicines / Catalog Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        barcode TEXT UNIQUE NOT NULL,
        brand_name TEXT NOT NULL,
        generic_name TEXT NOT NULL,
        category TEXT NOT NULL,
        dosage_form TEXT NOT NULL,
        strength TEXT NOT NULL,
        pack_size TEXT DEFAULT 'Box of 30',
        reorder_level INTEGER DEFAULT 20,
        requires_prescription INTEGER DEFAULT 0,
        is_controlled INTEGER DEFAULT 0,
        schedule_level TEXT,
        unit_cost REAL NOT NULL,
        unit_price REAL NOT NULL,
        storage_condition TEXT DEFAULT 'Room Temperature (15-25°C)',
        description TEXT,
        instructions TEXT,
        side_effects TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 5. Inventory Batches Table (with Expiry Tracking & First-Expired-First-Out FEFO)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER NOT NULL,
        batch_number TEXT NOT NULL,
        supplier_id INTEGER,
        manufacture_date DATE,
        expiry_date DATE NOT NULL,
        initial_quantity INTEGER NOT NULL,
        current_quantity INTEGER NOT NULL,
        unit_cost REAL NOT NULL,
        unit_price REAL NOT NULL,
        received_date DATE DEFAULT (DATE('now')),
        status TEXT DEFAULT 'active' CHECK(status IN ('active', 'quarantined', 'recalled', 'exhausted')),
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL,
        UNIQUE(medicine_id, batch_number)
    );
    """)

    # 6. Drug Interactions Database Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS drug_interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drug_a_generic TEXT NOT NULL,
        drug_b_generic TEXT NOT NULL,
        severity TEXT NOT NULL CHECK(severity IN ('Major', 'Moderate', 'Minor')),
        clinical_effect TEXT NOT NULL,
        recommendation TEXT NOT NULL
    );
    """)

    # 7. Prescribers / Doctors Directory
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prescribers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        license_number TEXT UNIQUE NOT NULL,
        hospital_clinic TEXT,
        specialization TEXT DEFAULT 'General Practice',
        phone TEXT,
        email TEXT,
        address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 8. Patients Directory
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_code TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        date_of_birth DATE,
        gender TEXT CHECK(gender IN ('Male', 'Female', 'Other')),
        phone TEXT,
        email TEXT,
        address TEXT,
        allergies TEXT,
        chronic_conditions TEXT,
        insurance_provider TEXT,
        insurance_policy_number TEXT,
        emergency_contact TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 9. Digital Prescriptions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prescriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rx_number TEXT UNIQUE NOT NULL,
        patient_id INTEGER NOT NULL,
        prescriber_id INTEGER NOT NULL,
        rx_date DATE NOT NULL,
        status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'Verified', 'Dispensed', 'Cancelled')),
        diagnosis TEXT,
        notes TEXT,
        verification_pharmacist_id INTEGER,
        dispensed_pharmacist_id INTEGER,
        dispensed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
        FOREIGN KEY (prescriber_id) REFERENCES prescribers(id) ON DELETE RESTRICT,
        FOREIGN KEY (verification_pharmacist_id) REFERENCES users(id) ON DELETE SET NULL,
        FOREIGN KEY (dispensed_pharmacist_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """)

    # 10. Prescription Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prescription_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prescription_id INTEGER NOT NULL,
        medicine_id INTEGER NOT NULL,
        dosage_instructions TEXT NOT NULL,
        quantity_prescribed INTEGER NOT NULL,
        quantity_dispensed INTEGER DEFAULT 0,
        refills_allowed INTEGER DEFAULT 0,
        refills_remaining INTEGER DEFAULT 0,
        FOREIGN KEY (prescription_id) REFERENCES prescriptions(id) ON DELETE CASCADE,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE RESTRICT
    );
    """)

    # 11. Sales Transactions / Invoices Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE NOT NULL,
        patient_id INTEGER,
        user_id INTEGER NOT NULL,
        prescription_id INTEGER,
        subtotal REAL NOT NULL,
        discount_amount REAL DEFAULT 0,
        tax_amount REAL DEFAULT 0,
        total_amount REAL NOT NULL,
        amount_paid REAL NOT NULL,
        change_due REAL DEFAULT 0,
        payment_method TEXT NOT NULL CHECK(payment_method IN ('Cash', 'Card', 'Insurance', 'Mobile Money', 'Split')),
        payment_reference TEXT,
        status TEXT DEFAULT 'Completed' CHECK(status IN ('Completed', 'Refunded', 'Cancelled')),
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE SET NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
        FOREIGN KEY (prescription_id) REFERENCES prescriptions(id) ON DELETE SET NULL
    );
    """)

    # 12. Sale Items Table (Linked to specific Batch for FEFO tracking)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sale_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        medicine_id INTEGER NOT NULL,
        batch_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        unit_cost REAL NOT NULL,
        unit_price REAL NOT NULL,
        total_price REAL NOT NULL,
        profit REAL NOT NULL,
        FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE RESTRICT,
        FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE RESTRICT
    );
    """)

    # 13. Stock Takes / Physical Inventory Audits Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_takes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        audit_code TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        conducted_by INTEGER NOT NULL,
        status TEXT DEFAULT 'Open' CHECK(status IN ('Open', 'Reconciled', 'Cancelled')),
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        total_items_counted INTEGER DEFAULT 0,
        net_variance_value REAL DEFAULT 0,
        notes TEXT,
        FOREIGN KEY (conducted_by) REFERENCES users(id) ON DELETE RESTRICT
    );
    """)

    # 14. Stock Take Item Details
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_take_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stock_take_id INTEGER NOT NULL,
        medicine_id INTEGER NOT NULL,
        batch_id INTEGER NOT NULL,
        system_quantity INTEGER NOT NULL,
        physical_count INTEGER NOT NULL,
        variance INTEGER NOT NULL,
        unit_cost REAL NOT NULL,
        variance_value REAL NOT NULL,
        notes TEXT,
        FOREIGN KEY (stock_take_id) REFERENCES stock_takes(id) ON DELETE CASCADE,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE RESTRICT,
        FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE RESTRICT
    );
    """)

    # 15. Stock Adjustments Log (Damages, Disposals, Adjustments)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_adjustments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER NOT NULL,
        batch_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        adjustment_type TEXT NOT NULL CHECK(adjustment_type IN ('Physical Audit', 'Damaged', 'Expired Disposal', 'Supplier Return', 'Correction')),
        quantity_changed INTEGER NOT NULL,
        previous_quantity INTEGER NOT NULL,
        new_quantity INTEGER NOT NULL,
        reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE RESTRICT,
        FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE RESTRICT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
    );
    """)

    # 16. Security & Audit Trail Log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        entity TEXT NOT NULL,
        entity_id TEXT,
        details TEXT,
        ip_address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """)

    # Create Indexes for fast real-time search & barcode scanning
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_medicines_barcode ON medicines(barcode);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_medicines_sku ON medicines(sku);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_medicines_names ON medicines(brand_name, generic_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_batches_expiry ON batches(expiry_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prescriptions_status ON prescriptions(status);")

    conn.commit()
    conn.close()
    print("Database schema successfully initialized.")

if __name__ == "__main__":
    init_db()
