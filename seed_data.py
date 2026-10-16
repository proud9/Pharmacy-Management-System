"""
PharmPulse Pro - Seed Data Generator (Zambia Localization: Zambian Kwacha ZMW/ZK)
Populates the database with realistic commercial pharmacy data including:
- Staff roles & permissions
- Clinical drug catalog with Zambian Kwacha (ZK) pricing & FEFO batch lots
- High-risk drug-drug interactions & allergy rules
- Registered prescribers (UTH, Levy Mwanawasa, Fairview Hospital)
- Patient medical records with NHIMA & local insurance
- Active & dispensed e-prescriptions
- 30-day historical sales with ZK revenue, NHIMA, Airtel Money, MTN MoMo
"""

import bcrypt
import sqlite3
from datetime import datetime, timedelta, date
from database import get_db, init_db
import random

def hash_pw(password: str) -> str:
    """Generate bcrypt password hash."""
    salt = bcrypt.gensalt(rounds=10)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def seed_all():
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    # Clear existing data if any
    tables = [
        'audit_logs', 'stock_adjustments', 'stock_take_items', 'stock_takes',
        'sale_items', 'sales', 'prescription_items', 'prescriptions',
        'batches', 'medicines', 'drug_interactions', 'patients',
        'prescribers', 'suppliers', 'user_sessions', 'users'
    ]
    for table in tables:
        cursor.execute(f"DELETE FROM {table};")
    cursor.execute("DELETE FROM sqlite_sequence;")

    print("Seeding Staff Users...")
    users = [
        ('admin', hash_pw('admin123'), 'Elena Mwansa, BPharm, MPS', 'admin', 'ZAMRA-RPH-4421', 'elena.mwansa@pharmpulse.zm', '+260-977-102030'),
        ('dr_sarah', hash_pw('pharma123'), 'Dr. Sarah Tembo, Chief Pharmacist', 'pharmacist', 'ZAMRA-RPH-2109', 'sarah.tembo@pharmpulse.zm', '+260-966-203040'),
        ('marcus_disp', hash_pw('dispense123'), 'Marcus Chileshe, Pharmacy Dispenser', 'dispenser', 'HPCZ-TECH-8841', 'marcus.c@pharmpulse.zm', '+260-955-304050'),
        ('jenny_cash', hash_pw('cash123'), 'Jenny Phiri, Lead Cashier & POS Operator', 'cashier', None, 'jenny.p@pharmpulse.zm', '+260-971-405060'),
        ('alex_inv', hash_pw('stock123'), 'Alex Bwalya, Inventory Controller', 'inventory_manager', None, 'alex.b@pharmpulse.zm', '+260-962-506070'),
    ]
    cursor.executemany("""
    INSERT INTO users (username, password_hash, full_name, role, license_number, email, phone)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, users)

    print("Seeding Zambian Pharmaceutical Suppliers...")
    suppliers = [
        ('Yash Pharmaceuticals Zambia Ltd', 'SUP-YASH-01', 'Rajiv Patel', 'orders@yashpharma.co.zm', '+260-211-286411', 'Plot 10444, Off Mungwi Road, Industrial Area, Lusaka', 2, 'Net 30'),
        ('Medlands Medical Wholesale Zambia', 'SUP-MED-02', 'Grace Musonda', 'supply@medlands.co.zm', '+260-211-377700', 'Plot 4838, Great East Road, Lusaka', 1, 'Net 15'),
        ('CAMS Pharmaceutical Distro', 'SUP-CAMS-03', 'Kennedy Zulu', 'orders@cams-zambia.com', '+260-211-244199', 'Lumumba Road, Lusaka', 3, 'Net 30'),
        ('International Drug Company (IDC) Zambia', 'SUP-IDC-04', 'Precious Banda', 'pbanda@idczambia.com', '+260-212-611200', 'President Avenue, Ndola, Copperbelt', 2, 'Net 45'),
        ('Novartis Regional Southern Africa', 'SUP-NOV-05', 'Claire Sterling', 'orders@novartis-safrica.com', '+260-211-220190', 'Kabulonga Shopping Complex, Lusaka', 4, 'Net 30')
    ]
    cursor.executemany("""
    INSERT INTO suppliers (name, code, contact_person, email, phone, address, lead_time_days, payment_terms)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, suppliers)

    print("Seeding Drug Interaction Rules...")
    interactions = [
        ('Warfarin', 'Aspirin', 'Major', 'Synergistic bleeding risk and dangerous gastrointestinal hemorrhage.', 'Avoid combination or monitor INR closely; prescribe alternative non-NSAID analgesic.'),
        ('Warfarin', 'Ibuprofen', 'Major', 'Marked increase in upper gastrointestinal bleeding risk.', 'Co-administration contraindicated; recommend Paracetamol / Acetaminophen instead.'),
        ('Lisinopril', 'Spironolactone', 'Major', 'Risk of severe, potentially fatal hyperkalemia.', 'Monitor serum potassium levels within 72 hours; adjust potassium-sparing diuretics.'),
        ('Ciprofloxacin', 'Calcium Carbonate', 'Moderate', 'Chelation of quinolone antibiotic significantly reduces bioavailability.', 'Separate intake by at least 2 hours before or 4 hours after calcium/antacid.'),
        ('Metformin', 'Cimetidine', 'Moderate', 'Reduced renal elimination of metformin leading to lactic acidosis risk.', 'Consider famotidine or PPI as alternative gastric acid inhibitor.'),
        ('Atorvastatin', 'Clarithromycin', 'Major', 'Inhibition of CYP3A4 leading to extreme statin serum levels and rhabdomyolysis.', 'Temporarily suspend Atorvastatin during clarithromycin antibiotic course.'),
        ('Sildenafil', 'Nitroglycerin', 'Major', 'Profound, catastrophic systemic hypotension.', 'Absolute contraindication! Do not dispense nitrates within 24-48 hours of PDE-5 inhibitors.'),
        ('Tramadol', 'Fluoxetine', 'Major', 'Excessive serotonergic accumulation precipitating Serotonin Syndrome.', 'Avoid combination; choose non-serotonergic analgesic or consult prescriber.')
    ]
    cursor.executemany("""
    INSERT INTO drug_interactions (drug_a_generic, drug_b_generic, severity, clinical_effect, recommendation)
    VALUES (?, ?, ?, ?, ?);
    """, interactions)

    print("Seeding Prescribing Physicians in Zambia...")
    prescribers = [
        ('Dr. Mwape Chanda, MD, MMed', 'HPCZ-MD-1092', 'University Teaching Hospital (UTH)', 'Cardiology', '+260-977-881122', 'mchanda@uth.gov.zm', 'Cardiology Wing, UTH, Nationalist Road, Lusaka'),
        ('Dr. Thandiwe Banda, MBChB', 'HPCZ-MD-2415', 'Levy Mwanawasa University Teaching Hospital', 'Family Medicine', '+260-966-443322', 'tbanda@luth.gov.zm', 'Great East Road, Lusaka'),
        ('Dr. Kondwani Phiri, MD', 'HPCZ-MD-3981', 'Fairview Medical Center', 'Endocrinology', '+260-955-778899', 'kphiri@fairview-hospital.com', 'Church Road, Fairview, Lusaka'),
        ('Dr. Natasha Lungu, MBChB, DCH', 'HPCZ-MD-4012', 'Ndola Teaching Hospital', 'Pediatrics', '+260-971-332211', 'nlungu@nth.gov.zm', 'Broadway, Ndola'),
        ('Dr. Emmanuel Mutale, MMed Ortho', 'HPCZ-MD-5190', 'Carepoint Specialist Clinic', 'Orthopedic Surgery', '+260-962-990011', 'emutale@carepoint.co.zm', 'Addis Ababa Drive, Rhodes Park, Lusaka')
    ]
    cursor.executemany("""
    INSERT INTO prescribers (full_name, license_number, hospital_clinic, specialization, phone, email, address)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, prescribers)

    print("Seeding Zambian Patients with NHIMA & Medical Records...")
    patients = [
        ('PT-1001', 'Arthur Mwila', '1962-04-12', 'Male', '+260-977-501122', 'arthur.mwila@zamtel.zm', 'Plot 22, Woodlands Extension, Lusaka', 'Penicillin, Sulfa drugs', 'Hypertension, Type 2 Diabetes', 'NHIMA Zambia', 'NHIMA-ZM-884120', 'Margaret Mwila (+260-977-501123)', 'NHIMA insured. Requires large-print bottle labels.'),
        ('PT-1002', 'Beatrice Chileshe', '1985-09-24', 'Female', '+260-966-602233', 'bchileshe@gmail.com', '120 Great North Road, Kabwe', 'Aspirin, Codeine', 'Asthma, Allergic Rhinitis', 'Prudential Zambia', 'PRU-ZM-449102', 'Charles Chileshe (+260-966-602234)', 'Patient prefers child-resistant caps.'),
        ('PT-1003', 'Carlos Lubinda', '1974-11-03', 'Male', '+260-955-703344', 'clubinda@miningcorp.zm', 'Plot 88, Kansenshi, Ndola', 'None Known', 'High Cholesterol, GERD', 'NHIMA Zambia', 'NHIMA-ZM-339182', 'Maria Lubinda (+260-955-703345)', 'Frequent traveler between Lusaka and Kitwe.'),
        ('PT-1004', 'Diana Musonda', '1992-06-18', 'Female', '+260-971-804455', 'dmusonda@bankofzambia.zm', '512 Independence Avenue, Lusaka', 'Latex, Ciprofloxacin', 'None', 'Madison General Health', 'MAD-ZM-990142', 'James Musonda (+260-971-804456)', 'Registered for SMS refill reminders via Airtel Money.'),
        ('PT-1005', 'Edward Kangwa', '1950-02-28', 'Male', '+260-962-905566', 'ekangwa@zescopension.zm', '14 Sunningdale, Lusaka', 'Penicillin', 'Congestive Heart Failure, Atrial Fibrillation', 'NHIMA Senior Care', 'NHIMA-ZM-114920', 'Luz Kangwa (+260-962-905567)', 'On Warfarin anticoagulant protocol.')
    ]
    cursor.executemany("""
    INSERT INTO patients (patient_code, full_name, date_of_birth, gender, phone, email, address, allergies, chronic_conditions, insurance_provider, insurance_policy_number, emergency_contact, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, patients)

    print("Seeding Medicine Catalog with Zambian Kwacha (ZK) Pricing...")
    # (sku, barcode, brand, generic, category, form, strength, pack, reorder, rx_req, is_ctrl, sched, cost_zk, price_zk, storage, desc, instr, sides)
    medicines_data = [
        ('MED-001', '890103001001', 'Amoxil Forte', 'Amoxicillin', 'Antibiotics', 'Capsule', '500mg', 'Box of 20', 25, 1, 0, None, 65.00, 130.00, 'Room Temp (15-25°C)', 'Broad-spectrum beta-lactam antibiotic.', 'Take 1 capsule every 8 hours with or without food. Finish full course.', 'Nausea, mild diarrhea, rash.'),
        ('MED-002', '890103001002', 'Glucophage XR', 'Metformin', 'Antidiabetic', 'Tablet (Extended Release)', '850mg', 'Box of 60', 30, 1, 0, None, 95.00, 185.00, 'Room Temp (15-25°C)', 'First-line biguanide for type 2 diabetes.', 'Take 1 tablet twice daily with evening meals to avoid GI upset.', 'GI upset, metallic taste, nausea.'),
        ('MED-003', '890103001003', 'Lipitor Elite', 'Atorvastatin', 'Cardiovascular', 'Tablet', '20mg', 'Box of 30', 20, 1, 0, None, 140.00, 290.00, 'Room Temp (15-25°C)', 'HMG-CoA reductase inhibitor for dyslipidemia.', 'Take 1 tablet daily at bedtime. Avoid grapefruit.', 'Myalgia, headache, mild nausea.'),
        ('MED-004', '890103001004', 'Nexium Pro', 'Omeprazole', 'Gastrointestinal', 'Delayed-Release Capsule', '20mg', 'Box of 28', 25, 0, 0, None, 75.00, 160.00, 'Room Temp (15-25°C)', 'Proton pump inhibitor for GERD and acid reflux.', 'Take 1 capsule once daily in the morning 30 minutes before breakfast.', 'Headache, abdominal cramps.'),
        ('MED-005', '890103001005', 'Panadol Extra', 'Paracetamol', 'Analgesics & Antipyretics', 'Tablet', '500mg', 'Pack of 32', 40, 0, 0, None, 22.00, 50.00, 'Room Temp (15-25°C)', 'Everyday pain and fever relief with caffeine boost.', 'Take 1-2 tablets every 4-6 hours as needed. Do not exceed 8 tablets in 24 hours.', 'Rare allergic reactions.'),
        ('MED-006', '890103001006', 'Cipro-Standard', 'Ciprofloxacin', 'Antibiotics', 'Film-Coated Tablet', '500mg', 'Box of 14', 15, 1, 0, None, 80.00, 175.00, 'Room Temp (15-25°C)', 'Fluoroquinolone antibiotic for bacterial infections.', 'Take 1 tablet twice daily. Avoid calcium, milk, or antacids for 2 hours.', 'Tendonitis warning, dizziness.'),
        ('MED-007', '890103001007', 'Prinivil Heart', 'Lisinopril', 'Cardiovascular', 'Tablet', '10mg', 'Box of 30', 20, 1, 0, None, 60.00, 145.00, 'Room Temp (15-25°C)', 'ACE inhibitor for arterial hypertension and heart failure.', 'Take 1 tablet once daily in the morning.', 'Dry hacking cough, dizziness, hyperkalemia.'),
        ('MED-008', '890103001008', 'Ventolin HFA', 'Salbutamol', 'Respiratory', 'Metered Dose Inhaler', '100mcg/dose', 'Inhaler (200 doses)', 15, 1, 0, None, 180.00, 360.00, 'Store below 30°C, keep dry', 'Short-acting beta2-agonist bronchodilator for acute asthma.', 'Inhale 1-2 puffs during acute bronchospasm. Rinse mouth.', 'Tremors, tachycardia, palpitations.'),
        ('MED-009', '890103001009', 'Lantus SoloStar', 'Insulin Glargine', 'Antidiabetic', 'Pre-filled SubQ Pen', '100 units/mL', 'Box of 5 Pens', 10, 1, 0, None, 680.00, 1350.00, 'Refrigerated (2-8°C), Do Not Freeze', 'Long-acting basal human insulin analog.', 'Administer once daily subcutaneously at the exact same hour.', 'Hypoglycemia, injection site lipodystrophy.'),
        ('MED-010', '890103001010', 'Zithromax Tri-Pak', 'Azithromycin', 'Antibiotics', 'Film-Coated Tablet', '250mg', 'Pack of 6', 15, 1, 0, None, 110.00, 230.00, 'Room Temp (15-25°C)', 'Macrolide antibiotic for upper and lower respiratory tract infections.', 'Take 500mg on day 1, then 250mg daily on days 2 to 5.', 'Mild diarrhea, abdominal pain.'),
        ('MED-011', '890103001011', 'Advil Max Relief', 'Ibuprofen', 'Analgesics & Antipyretics', 'Liquid Softgel', '400mg', 'Bottle of 50', 35, 0, 0, None, 35.00, 85.00, 'Room Temp (15-25°C)', 'Non-steroidal anti-inflammatory drug (NSAID).', 'Take 1 softgel every 6 hours with a glass of water and food.', 'Gastric irritation, heartburn.'),
        ('MED-012', '890103001012', 'Rocephin Vials', 'Ceftriaxone', 'Antibiotics', 'Powder for Injection', '1g Vial', 'Pack of 5 Vials', 8, 1, 0, None, 190.00, 420.00, 'Store protected from light', 'Third-generation cephalosporin for severe hospital/clinic infections.', 'Reconstitute with 1% lidocaine or sterile water. IM/IV strictly.', 'Pain at injection site, eosinophilia.'),
        ('MED-013', '890103001013', 'Cozaar Vascular', 'Losartan Potassium', 'Cardiovascular', 'Tablet', '50mg', 'Box of 30', 25, 1, 0, None, 65.00, 155.00, 'Room Temp (15-25°C)', 'Angiotensin II receptor antagonist (ARB).', 'Take 1 tablet daily with or without food.', 'Dizziness, upper respiratory congestion.'),
        ('MED-014', '890103001014', 'Zyrtec 24hr', 'Cetirizine HCl', 'Allergy & Antihistamines', 'Tablet', '10mg', 'Pack of 30', 30, 0, 0, None, 38.00, 95.00, 'Room Temp (15-25°C)', 'Second-generation non-sedating antihistamine.', 'Take 1 tablet once daily in the evening.', 'Mild drowsiness, dry mouth.'),
        ('MED-015', '890103001015', 'Norvasc Pulse', 'Amlodipine Besylate', 'Cardiovascular', 'Tablet', '5mg', 'Box of 30', 20, 1, 0, None, 50.00, 130.00, 'Room Temp (15-25°C)', 'Calcium channel blocker for hypertension and chronic stable angina.', 'Take 1 tablet once daily.', 'Peripheral edema, flushing, palpitations.'),
        ('MED-016', '890103001016', 'Ultram Control', 'Tramadol HCl', 'Controlled Substances', 'Tablet', '50mg', 'Box of 20', 12, 1, 1, 'Schedule IV', 120.00, 280.00, 'Lock and Key Controlled Storage', 'Centrally acting synthetic opioid analgesic.', 'Take 1 tablet every 6 hours as strictly prescribed. Monitor for dependence.', 'Drowsiness, constipation, potential addiction.'),
        ('MED-017', '890103001017', 'Coumadin ClotCare', 'Warfarin Sodium', 'Anticoagulants', 'Tablet', '5mg', 'Bottle of 100', 15, 1, 0, None, 85.00, 210.00, 'Room Temp (15-25°C)', 'Vitamin K antagonist oral anticoagulant.', 'Strict dosage per INR lab test. Take at 6:00 PM daily. Avoid sudden diet changes.', 'Bleeding risk, bruising, hematuria.'),
        ('MED-018', '890103001018', 'Bayer Cardio Aspirin', 'Aspirin (EC)', 'Cardiovascular', 'Enteric Coated Tablet', '81mg', 'Bottle of 120', 30, 0, 0, None, 30.00, 75.00, 'Room Temp (15-25°C)', 'Low-dose platelet aggregation inhibitor for cardiovascular prophylaxis.', 'Take 1 tablet daily after food.', 'Gastric irritation, bruising.'),
        ('MED-019', '890103001019', 'Augmentin Duo', 'Amoxicillin + Clavulanic Acid', 'Antibiotics', 'Tablet', '625mg', 'Box of 14', 20, 1, 0, None, 130.00, 275.00, 'Room Temp (15-25°C)', 'Beta-lactamase resistant combination antibiotic.', 'Take 1 tablet every 12 hours at the start of a meal.', 'Diarrhea, nausea, candidiasis.'),
        ('MED-020', '890103001020', 'Xanax Calmer', 'Alprazolam', 'Controlled Substances', 'Tablet', '0.5mg', 'Bottle of 60', 10, 1, 1, 'Schedule IV', 145.00, 320.00, 'Double-lock Controlled Cabinet', 'Short-acting benzodiazepine for acute panic and anxiety.', 'Take as directed by psychiatrist. Taper off gradually.', 'Sedation, memory impairment, ataxia.')
    ]

    cursor.executemany("""
    INSERT INTO medicines (sku, barcode, brand_name, generic_name, category, dosage_form, strength, pack_size, reorder_level, requires_prescription, is_controlled, schedule_level, unit_cost, unit_price, storage_condition, description, instructions, side_effects)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, medicines_data)

    print("Seeding Inventory Batches with FEFO Dates...")
    cursor.execute("SELECT id, sku, unit_cost, unit_price FROM medicines ORDER BY id;")
    med_rows = cursor.fetchall()
    med_map = {row['sku']: dict(row) for row in med_rows}

    cursor.execute("SELECT id FROM suppliers ORDER BY id;")
    sup_ids = [r['id'] for r in cursor.fetchall()]
    s1, s2, s3, s4, s5 = sup_ids[0], sup_ids[1], sup_ids[2], sup_ids[3], sup_ids[4]

    today = date.today()

    batches_data = [
        # Amoxicillin (MED-001): 2 batches - one expiring in 25 days (alert trigger!), one in 14 months
        (med_map['MED-001']['id'], 'BATCH-AMX-2024-01', s1, str(today - timedelta(days=340)), str(today + timedelta(days=25)), 100, 18, 65.00, 130.00, 'active', 'FEFO Alert: Expiring soon'),
        (med_map['MED-001']['id'], 'BATCH-AMX-2025-02', s1, str(today - timedelta(days=60)), str(today + timedelta(days=420)), 200, 185, 65.00, 130.00, 'active', 'Fresh shipment'),

        # Metformin (MED-002)
        (med_map['MED-002']['id'], 'BATCH-MET-881', s3, str(today - timedelta(days=120)), str(today + timedelta(days=500)), 150, 110, 95.00, 185.00, 'active', 'Standard inventory'),

        # Atorvastatin (MED-003): low stock alert (only 12 units remaining vs 20 reorder level)
        (med_map['MED-003']['id'], 'BATCH-ATV-301', s2, str(today - timedelta(days=180)), str(today + timedelta(days=365)), 80, 12, 140.00, 290.00, 'active', 'Critical: Reorder needed'),

        # Omeprazole (MED-004): 2 batches
        (med_map['MED-004']['id'], 'BATCH-OME-109', s4, str(today - timedelta(days=90)), str(today + timedelta(days=45)), 120, 24, 75.00, 160.00, 'active', 'Expiring within 45 days'),
        (med_map['MED-004']['id'], 'BATCH-OME-110', s4, str(today - timedelta(days=30)), str(today + timedelta(days=600)), 200, 190, 75.00, 160.00, 'active', 'Primary reserve'),

        # Paracetamol (MED-005): high turnover, 2 batches
        (med_map['MED-005']['id'], 'BATCH-PAR-904', s3, str(today - timedelta(days=100)), str(today + timedelta(days=280)), 300, 85, 22.00, 50.00, 'active', 'Fast moving shelf'),
        (med_map['MED-005']['id'], 'BATCH-PAR-905', s3, str(today - timedelta(days=15)), str(today + timedelta(days=700)), 500, 480, 22.00, 50.00, 'active', 'Warehouse reserve'),

        # Ciprofloxacin (MED-006): low stock (8 units left)
        (med_map['MED-006']['id'], 'BATCH-CIP-044', s5, str(today - timedelta(days=140)), str(today + timedelta(days=220)), 50, 8, 80.00, 175.00, 'active', 'Low stock alert'),

        # Lisinopril (MED-007)
        (med_map['MED-007']['id'], 'BATCH-LIS-712', s1, str(today - timedelta(days=75)), str(today + timedelta(days=390)), 90, 64, 60.00, 145.00, 'active', 'Normal'),

        # Ventolin (MED-008)
        (med_map['MED-008']['id'], 'BATCH-VEN-502', s2, str(today - timedelta(days=80)), str(today + timedelta(days=300)), 60, 42, 180.00, 360.00, 'active', 'Normal'),

        # Lantus Insulin (MED-009): cold chain stock
        (med_map['MED-009']['id'], 'BATCH-LAN-118', s2, str(today - timedelta(days=40)), str(today + timedelta(days=210)), 30, 21, 680.00, 1350.00, 'active', 'Cold storage monitored'),

        # Azithromycin (MED-010)
        (med_map['MED-010']['id'], 'BATCH-AZI-609', s5, str(today - timedelta(days=95)), str(today + timedelta(days=330)), 70, 48, 110.00, 230.00, 'active', 'Normal'),

        # Ibuprofen (MED-011)
        (med_map['MED-011']['id'], 'BATCH-IBU-312', s4, str(today - timedelta(days=60)), str(today + timedelta(days=650)), 150, 130, 35.00, 85.00, 'active', 'Normal'),

        # Ceftriaxone (MED-012): low stock (6 vials left)
        (med_map['MED-012']['id'], 'BATCH-CEF-009', s1, str(today - timedelta(days=110)), str(today + timedelta(days=180)), 40, 6, 190.00, 420.00, 'active', 'Urgent reorder'),

        # Losartan (MED-013)
        (med_map['MED-013']['id'], 'BATCH-LOS-441', s3, str(today - timedelta(days=50)), str(today + timedelta(days=480)), 100, 82, 65.00, 155.00, 'active', 'Normal'),

        # Cetirizine (MED-014)
        (med_map['MED-014']['id'], 'BATCH-CET-220', s4, str(today - timedelta(days=120)), str(today + timedelta(days=550)), 120, 94, 38.00, 95.00, 'active', 'Normal'),

        # Amlodipine (MED-015)
        (med_map['MED-015']['id'], 'BATCH-AML-771', s1, str(today - timedelta(days=85)), str(today + timedelta(days=410)), 90, 70, 50.00, 130.00, 'active', 'Normal'),

        # Tramadol Controlled (MED-016)
        (med_map['MED-016']['id'], 'BATCH-TRM-889', s5, str(today - timedelta(days=45)), str(today + timedelta(days=360)), 50, 35, 120.00, 280.00, 'active', 'Schedule IV Safe A'),

        # Warfarin (MED-017)
        (med_map['MED-017']['id'], 'BATCH-WAR-303', s3, str(today - timedelta(days=90)), str(today + timedelta(days=320)), 60, 44, 85.00, 210.00, 'active', 'Anticoagulant cabinet'),

        # Aspirin 81mg (MED-018)
        (med_map['MED-018']['id'], 'BATCH-ASP-101', s4, str(today - timedelta(days=100)), str(today + timedelta(days=600)), 120, 95, 30.00, 75.00, 'active', 'Normal'),

        # Augmentin (MED-019)
        (med_map['MED-019']['id'], 'BATCH-AUG-991', s1, str(today - timedelta(days=70)), str(today + timedelta(days=290)), 80, 52, 130.00, 275.00, 'active', 'Normal'),

        # Xanax Controlled (MED-020)
        (med_map['MED-020']['id'], 'BATCH-XAN-014', s5, str(today - timedelta(days=30)), str(today + timedelta(days=400)), 40, 28, 145.00, 320.00, 'active', 'Schedule IV Safe B')
    ]

    cursor.executemany("""
    INSERT INTO batches (medicine_id, batch_number, supplier_id, manufacture_date, expiry_date, initial_quantity, current_quantity, unit_cost, unit_price, status, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, batches_data)

    print("Seeding Digital Prescriptions...")
    prescriptions_data = [
        ('RX-2026-0091', 1, 1, str(today - timedelta(days=2)), 'Verified', 'Essential Hypertension & Early Diabetic Microalbuminuria', 'Monitor BP every 7 days. Check kidney function in 3 months.', 2, None, None),
        ('RX-2026-0092', 3, 2, str(today - timedelta(days=1)), 'Pending', 'Acute Rhinosinusitis', 'Patient reports severe frontal headache and purulent nasal discharge.', None, None, None),
        ('RX-2026-0093', 5, 1, str(today - timedelta(days=4)), 'Dispensed', 'Atrial Fibrillation Stroke Prevention', 'INR target range is strictly 2.0 to 3.0.', 2, 2, str(today - timedelta(days=4)) + ' 14:20:00'),
        ('RX-2026-0094', 2, 4, str(today), 'Pending', 'Mild Exercise-Induced Asthma Exacerbation', 'Use inhaler 15 minutes before running or aerobic workout.', None, None, None)
    ]
    cursor.executemany("""
    INSERT INTO prescriptions (rx_number, patient_id, prescriber_id, rx_date, status, diagnosis, notes, verification_pharmacist_id, dispensed_pharmacist_id, dispensed_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, prescriptions_data)

    cursor.execute("SELECT id, rx_number FROM prescriptions;")
    rx_map = {row['rx_number']: row['id'] for row in cursor.fetchall()}

    rx_items = [
        (rx_map['RX-2026-0091'], med_map['MED-007']['id'], 'Take 1 tablet (10mg) by mouth once daily in the morning', 30, 0, 2, 2),
        (rx_map['RX-2026-0091'], med_map['MED-002']['id'], 'Take 1 tablet (850mg) by mouth twice daily with meals', 60, 0, 3, 3),
        (rx_map['RX-2026-0092'], med_map['MED-019']['id'], 'Take 1 tablet every 12 hours with meals for 7 days', 14, 0, 0, 0),
        (rx_map['RX-2026-0092'], med_map['MED-014']['id'], 'Take 1 tablet at bedtime for allergic congestion', 10, 0, 1, 1),
        (rx_map['RX-2026-0093'], med_map['MED-017']['id'], 'Take 1 tablet (5mg) by mouth every evening at 6 PM', 30, 30, 5, 4),
        (rx_map['RX-2026-0094'], med_map['MED-008']['id'], 'Inhale 1-2 puffs via spacer as needed for wheezing or exercise', 1, 0, 2, 2)
    ]
    cursor.executemany("""
    INSERT INTO prescription_items (prescription_id, medicine_id, dosage_instructions, quantity_prescribed, quantity_dispensed, refills_allowed, refills_remaining)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, rx_items)

    print("Seeding 30-Day Historical Sales Transactions in Zambian Kwacha (ZK)...")
    cursor.execute("SELECT id, medicine_id, unit_cost, unit_price FROM batches WHERE status = 'active';")
    batch_records = cursor.fetchall()

    sale_counter = 1000
    # Common payment methods in Zambian pharmacies: Cash, Card, Insurance (NHIMA), Mobile Money (Airtel/MTN)
    payment_methods = ['Cash', 'Mobile Money', 'Card', 'Insurance', 'Cash', 'Mobile Money']

    for i in range(45):
        sale_counter += 1
        inv_code = f"INV-2026-{sale_counter}"
        days_ago = random.randint(0, 30)
        minute = random.randint(0, 59)
        tx_time = datetime.now() - timedelta(days=days_ago, hours=random.randint(1, 10), minutes=minute)
        tx_str = tx_time.strftime("%Y-%m-%d %H:%M:%S")

        patient_id = random.choice([1, 2, 3, 4, 5, None, None])
        user_id = random.choice([1, 2, 3, 4])
        pay_method = random.choice(payment_methods)

        num_items = random.randint(1, 3)
        chosen_batches = random.sample(batch_records, num_items)

        subtotal = 0.0
        total_profit = 0.0
        items_to_insert = []

        for b in chosen_batches:
            qty = random.randint(1, 3)
            price = b['unit_price']
            cost = b['unit_cost']
            item_sub = price * qty
            item_prof = (price - cost) * qty
            subtotal += item_sub
            total_profit += item_prof
            items_to_insert.append((b['medicine_id'], b['id'], qty, cost, price, item_sub, item_prof))

        discount = round(subtotal * 0.05, 2) if (patient_id and random.random() > 0.6) else 0.0
        tax = round((subtotal - discount) * 0.04, 2)
        total = round(subtotal - discount + tax, 2)
        amount_paid = total if pay_method != 'Cash' else (total + random.choice([0, 20, 50, 100]))
        change = round(amount_paid - total, 2)

        cursor.execute("""
        INSERT INTO sales (invoice_number, patient_id, user_id, prescription_id, subtotal, discount_amount, tax_amount, total_amount, amount_paid, change_due, payment_method, payment_reference, status, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (inv_code, patient_id, user_id, None, subtotal, discount, tax, total, amount_paid, change, pay_method, f"TXN-ZM-{random.randint(100000, 999999)}", 'Completed', 'Walk-in / NHIMA Outpatient POS checkout', tx_str))

        sale_id = cursor.lastrowid
        for it in items_to_insert:
            cursor.execute("""
            INSERT INTO sale_items (sale_id, medicine_id, batch_id, quantity, unit_cost, unit_price, total_price, profit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (sale_id, it[0], it[1], it[2], it[3], it[4], it[5], it[6]))

    print("Seeding Sample Stock Take Audit in ZK...")
    cursor.execute("""
    INSERT INTO stock_takes (audit_code, title, conducted_by, status, started_at, completed_at, total_items_counted, net_variance_value, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        'AUDIT-2026-Q1',
        'Q1 Lusaka Branch Comprehensive Stock Audit (ZK)',
        5,
        'Reconciled',
        (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d 09:30:00"),
        (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d 15:45:00"),
        15,
        -66.00,
        'Full physical count of cold chain insulin, antibiotics, and Schedule IV substances completed. Discrepancy logged for 3 Paracetamol blister units.'
    ))
    stock_take_id = cursor.lastrowid

    cursor.execute("""
    INSERT INTO stock_take_items (stock_take_id, medicine_id, batch_id, system_quantity, physical_count, variance, unit_cost, variance_value, notes)
    VALUES 
    (?, 1, 1, 18, 18, 0, 65.00, 0.0, 'Amoxil verified exact.'),
    (?, 5, 6, 88, 85, -3, 22.00, -66.00, '3 damaged blister packs discarded.'),
    (?, 9, 10, 21, 21, 0, 680.00, 0.0, 'Cold chain fridge log verified.'),
    (?, 16, 17, 35, 35, 0, 120.00, 0.0, 'Schedule IV safe count verified.');
    """, (stock_take_id, stock_take_id, stock_take_id, stock_take_id))

    print("Seeding Security & Operational Audit Logs...")
    audit_events = [
        (1, 'SYSTEM_INIT', 'SYSTEM', '1', 'PharmPulse Pro localized for Zambia (ZK/ZMW). Database seeded.', '127.0.0.1', (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")),
        (2, 'LOGIN_SUCCESS', 'AUTH', '2', 'Remote login authenticated via SHA-256 JWT from Lusaka Central Terminal.', '192.168.1.104', (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d 08:14:22")),
        (5, 'STOCK_AUDIT', 'STOCK_TAKE', 'AUDIT-2026-Q1', 'Completed Q1 Physical Stock Audit. Net variance: -ZK 66.00.', '192.168.1.112', (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d 15:45:00")),
        (2, 'DISPENSE_RX', 'PRESCRIPTION', 'RX-2026-0093', 'Verified and dispensed Warfarin 5mg under NHIMA prescription.', '192.168.1.104', (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d 14:20:00")),
        (1, 'PRICE_UPDATE', 'MEDICINE', 'MED-009', 'Updated Lantus SoloStar unit price in ZK to reflect new ZAMRA import duties.', '192.168.1.100', (datetime.now() - timedelta(days=12)).strftime("%Y-%m-%d 11:05:10"))
    ]
    cursor.executemany("""
    INSERT INTO audit_logs (user_id, action, entity, entity_id, details, ip_address, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, audit_events)

    conn.commit()
    conn.close()
    print("Seed complete! All prices and transactions successfully localized to Zambian Kwacha (ZK).")

if __name__ == "__main__":
    seed_all()
