"""
PharmPulse Pro - Commercial Pharmacy Management & BI System
Backend REST API Server built with Flask, SQLite3, PyJWT, and bcrypt.
Includes Remote Access Control, FEFO Inventory Engine, Clinical Drug Safety Checker,
POS Dispensing, Digital Prescriptions, and Real-Time Business Analytics.
"""

import os
import sqlite3
import jwt
import bcrypt
import json
import csv
import io
import random
from datetime import datetime, timedelta, date, timezone
from functools import wraps
from flask import Flask, request, jsonify, render_template, send_from_directory, Response
from flask_cors import CORS
from database import get_db, init_db

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

SECRET_KEY = os.environ.get("PHARM_SECRET_KEY", "pharmpulse-enterprise-super-secret-key-2026")
JWT_ALGORITHM = "HS256"

# Helper for JSON serialization of SQLite Row
def dict_from_row(row):
    if row is None:
        return None
    return dict(row)

def rows_to_list(rows):
    return [dict(r) for r in rows]

# Authentication Middleware
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        elif 'token' in request.args:
            token = request.args['token']

        if not token:
            return jsonify({'success': False, 'message': 'Authentication token missing or invalid'}), 401

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
            user_id = payload.get('user_id')
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, full_name, role, license_number, email, is_active FROM users WHERE id = ?;", (user_id,))
            user = cursor.fetchone()
            conn.close()

            if not user or not user['is_active']:
                return jsonify({'success': False, 'message': 'User account inactive or not found'}), 401

            request.current_user = dict(user)
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'message': 'Session token has expired. Please log in again.'}), 401
        except Exception as e:
            return jsonify({'success': False, 'message': f'Invalid token: {str(e)}'}), 401

        return f(*args, **kwargs)
    return decorated

def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                return jsonify({'success': False, 'message': 'Unauthorized'}), 401
            if request.current_user['role'] not in allowed_roles and request.current_user['role'] != 'admin':
                return jsonify({'success': False, 'message': 'Permission denied for this action'}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

def log_audit(conn, user_id, action, entity, entity_id, details):
    try:
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1')
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO audit_logs (user_id, action, entity, entity_id, details, ip_address)
        VALUES (?, ?, ?, ?, ?, ?);
        """, (user_id, action, entity, str(entity_id), details, ip))
    except Exception as e:
        print(f"Audit log error: {e}")

# ==========================================
# 1. CORE WEB ROUTE
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

# ==========================================
# 2. AUTHENTICATION & REMOTE LOGIN
# ==========================================
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?;", (username,))
    user = cursor.fetchone()

    if not user or not user['is_active']:
        conn.close()
        return jsonify({'success': False, 'message': 'Invalid credentials or account suspended'}), 401

    if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        conn.close()
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    # Issue JWT Token with 24h validity
    exp_time = datetime.utcnow() + timedelta(hours=24)
    token = jwt.encode({
        'user_id': user['id'],
        'username': user['username'],
        'role': user['role'],
        'exp': exp_time
    }, SECRET_KEY, algorithm=JWT_ALGORITHM)

    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1')
    user_agent = request.headers.get('User-Agent', 'Web Browser')
    device_type = 'Mobile' if 'Mobile' in user_agent else ('Tablet' if 'Tablet' in user_agent or 'iPad' in user_agent else 'Desktop Station')

    # Record Remote Session
    cursor.execute("""
    INSERT INTO user_sessions (user_id, token, ip_address, user_agent, device_type)
    VALUES (?, ?, ?, ?, ?);
    """, (user['id'], token, ip_address, user_agent[:250], device_type))
    session_id = cursor.lastrowid

    # Update last login
    cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?;", (user['id'],))
    log_audit(conn, user['id'], 'LOGIN_SUCCESS', 'AUTH', user['id'], f"Remote access granted via {device_type} ({ip_address})")
    conn.commit()
    conn.close()

    user_info = {
        'id': user['id'],
        'username': user['username'],
        'full_name': user['full_name'],
        'role': user['role'],
        'license_number': user['license_number'],
        'email': user['email']
    }

    return jsonify({
        'success': True,
        'message': f"Welcome back, {user['full_name']}",
        'token': token,
        'session_id': session_id,
        'user': user_info
    })

@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user():
    return jsonify({
        'success': True,
        'user': request.current_user
    })

@app.route('/api/auth/switch-demo-user/<username>', methods=['POST'])
def switch_demo_user(username):
    """Allows instant persona switching for testing role capabilities."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?;", (username,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return jsonify({'success': False, 'message': 'Demo user not found'}), 404

    exp_time = datetime.utcnow() + timedelta(hours=24)
    token = jwt.encode({
        'user_id': user['id'],
        'username': user['username'],
        'role': user['role'],
        'exp': exp_time
    }, SECRET_KEY, algorithm=JWT_ALGORITHM)

    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1')
    user_agent = request.headers.get('User-Agent', 'Desktop Terminal')
    device_type = 'Station Terminal'

    cursor.execute("""
    INSERT INTO user_sessions (user_id, token, ip_address, user_agent, device_type)
    VALUES (?, ?, ?, ?, ?);
    """, (user['id'], token, ip_address, user_agent[:250], device_type))
    session_id = cursor.lastrowid

    log_audit(conn, user['id'], 'DEMO_SWITCH', 'AUTH', user['id'], f"Switched role to {user['role']} ({user['full_name']})")
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'token': token,
        'session_id': session_id,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'full_name': user['full_name'],
            'role': user['role'],
            'license_number': user['license_number'],
            'email': user['email']
        }
    })

@app.route('/api/auth/sessions', methods=['GET'])
@token_required
def list_active_sessions():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT s.id, s.user_id, u.username, u.full_name, u.role, s.ip_address, s.device_type, s.login_time, s.last_activity, s.is_active
    FROM user_sessions s
    JOIN users u ON s.user_id = u.id
    ORDER BY s.login_time DESC
    LIMIT 50;
    """)
    sessions = rows_to_list(cursor.fetchall())
    conn.close()
    return jsonify({'success': True, 'sessions': sessions})

@app.route('/api/auth/sessions/<int:session_id>', methods=['DELETE'])
@token_required
@roles_required('admin')
def terminate_session(session_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE user_sessions SET is_active = 0 WHERE id = ?;", (session_id,))
    log_audit(conn, request.current_user['id'], 'REVOKE_SESSION', 'SESSION', session_id, "Admin terminated remote session.")
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Remote session revoked successfully.'})

# ==========================================
# 3. INVENTORY & STOCK MANAGEMENT
# ==========================================
@app.route('/api/inventory/medicines', methods=['GET'])
@token_required
def get_medicines():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    status_filter = request.args.get('status', '').strip() # 'low_stock', 'expiring', 'out_of_stock'

    conn = get_db()
    cursor = conn.cursor()

    query = """
    SELECT m.*,
           COALESCE(SUM(b.current_quantity), 0) AS total_stock,
           MIN(CASE WHEN b.current_quantity > 0 THEN b.expiry_date ELSE NULL END) AS nearest_expiry,
           COUNT(CASE WHEN b.current_quantity > 0 THEN b.id ELSE NULL END) AS active_batches_count
    FROM medicines m
    LEFT JOIN batches b ON m.id = b.medicine_id AND b.status = 'active'
    WHERE 1=1
    """
    params = []

    if search:
        query += " AND (m.brand_name LIKE ? OR m.generic_name LIKE ? OR m.barcode LIKE ? OR m.sku LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])

    if category and category != 'All':
        query += " AND m.category = ?"
        params.append(category)

    query += " GROUP BY m.id"

    # Status post-filter via HAVING
    if status_filter == 'low_stock':
        query += " HAVING total_stock > 0 AND total_stock <= m.reorder_level"
    elif status_filter == 'out_of_stock':
        query += " HAVING total_stock = 0"
    elif status_filter == 'expiring':
        query += f" HAVING nearest_expiry <= DATE('now', '+90 days')"

    query += " ORDER BY m.brand_name ASC;"

    cursor.execute(query, params)
    items = rows_to_list(cursor.fetchall())

    # Add calculated shelf health flags
    today = date.today()
    for item in items:
        if item['nearest_expiry']:
            exp = datetime.strptime(item['nearest_expiry'], '%Y-%m-%d').date()
            delta = (exp - today).days
            item['days_to_expiry'] = delta
            if delta < 0:
                item['expiry_status'] = 'expired'
            elif delta <= 30:
                item['expiry_status'] = 'critical'
            elif delta <= 90:
                item['expiry_status'] = 'warning'
            else:
                item['expiry_status'] = 'good'
        else:
            item['days_to_expiry'] = None
            item['expiry_status'] = 'no_stock'

        if item['total_stock'] == 0:
            item['stock_status'] = 'out_of_stock'
        elif item['total_stock'] <= item['reorder_level']:
            item['stock_status'] = 'low_stock'
        else:
            item['stock_status'] = 'healthy'

    conn.close()
    return jsonify({'success': True, 'medicines': items})

@app.route('/api/inventory/medicines/<int:med_id>', methods=['GET'])
@token_required
def get_medicine_detail(med_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medicines WHERE id = ?;", (med_id,))
    med = cursor.fetchone()
    if not med:
        conn.close()
        return jsonify({'success': False, 'message': 'Medicine not found'}), 404

    # Fetch all batches for this medicine
    cursor.execute("""
    SELECT b.*, s.name as supplier_name
    FROM batches b
    LEFT JOIN suppliers s ON b.supplier_id = s.id
    WHERE b.medicine_id = ?
    ORDER BY b.expiry_date ASC;
    """, (med_id,))
    batches = rows_to_list(cursor.fetchall())
    conn.close()

    res = dict(med)
    res['batches'] = batches
    return jsonify({'success': True, 'medicine': res})

@app.route('/api/inventory/medicines', methods=['POST'])
@token_required
@roles_required('admin', 'pharmacist', 'inventory_manager')
def add_medicine():
    data = request.get_json() or {}
    brand = data.get('brand_name', '').strip()
    generic = data.get('generic_name', '').strip()
    sku = data.get('sku', '').strip()
    barcode = data.get('barcode', '').strip()

    if not brand or not generic:
        return jsonify({'success': False, 'message': 'Brand and Generic names required'}), 400

    conn = get_db()
    cursor = conn.cursor()

    if not sku:
        cursor.execute("SELECT COUNT(*) as count FROM medicines;")
        count = cursor.fetchone()['count'] + 1
        sku = f"MED-{count:03d}"

    if not barcode:
        barcode = f"890103{random.randint(100000, 999999)}"

    try:
        cursor.execute("""
        INSERT INTO medicines (sku, barcode, brand_name, generic_name, category, dosage_form, strength, pack_size, reorder_level, requires_prescription, is_controlled, schedule_level, unit_cost, unit_price, storage_condition, description, instructions, side_effects)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            sku,
            barcode,
            brand,
            generic,
            data.get('category', 'General Medicine'),
            data.get('dosage_form', 'Tablet'),
            data.get('strength', 'Standard'),
            data.get('pack_size', 'Box of 30'),
            int(data.get('reorder_level', 20)),
            1 if data.get('requires_prescription') else 0,
            1 if data.get('is_controlled') else 0,
            data.get('schedule_level', None),
            float(data.get('unit_cost', 5.0)),
            float(data.get('unit_price', 12.0)),
            data.get('storage_condition', 'Room Temperature (15-25°C)'),
            data.get('description', ''),
            data.get('instructions', ''),
            data.get('side_effects', '')
        ))
        med_id = cursor.lastrowid
        log_audit(conn, request.current_user['id'], 'CREATE_MEDICINE', 'MEDICINE', med_id, f"Added catalog item: {brand} ({generic})")
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Medicine {brand} registered successfully.', 'id': med_id})
    except sqlite3.IntegrityError as e:
        conn.close()
        return jsonify({'success': False, 'message': f'Duplicate entry or constraint violation: {str(e)}'}), 400

@app.route('/api/inventory/batches', methods=['POST'])
@token_required
@roles_required('admin', 'pharmacist', 'inventory_manager')
def add_batch():
    data = request.get_json() or {}
    med_id = data.get('medicine_id')
    batch_num = data.get('batch_number', '').strip()
    qty = int(data.get('quantity', 0))
    expiry = data.get('expiry_date', '').strip()
    mfg = data.get('manufacture_date', str(date.today() - timedelta(days=30)))
    unit_cost = float(data.get('unit_cost', 0))
    unit_price = float(data.get('unit_price', 0))
    supplier_id = data.get('supplier_id')

    if not med_id or not batch_num or qty <= 0 or not expiry:
        return jsonify({'success': False, 'message': 'Medicine, Batch Number, Quantity (>0), and Expiry Date are required.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO batches (medicine_id, batch_number, supplier_id, manufacture_date, expiry_date, initial_quantity, current_quantity, unit_cost, unit_price, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?);
        """, (med_id, batch_num, supplier_id, mfg, expiry, qty, qty, unit_cost, unit_price, data.get('notes', 'Stock Intake')))
        batch_id = cursor.lastrowid

        log_audit(conn, request.current_user['id'], 'ADD_BATCH', 'BATCH', batch_id, f"Intake of {qty} units in batch {batch_num} (Exp: {expiry})")
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Batch {batch_num} successfully added to inventory.', 'batch_id': batch_id})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'success': False, 'message': f'Batch {batch_num} already exists for this medicine.'}), 400

@app.route('/api/inventory/adjust', methods=['POST'])
@token_required
@roles_required('admin', 'pharmacist', 'inventory_manager')
def adjust_stock():
    data = request.get_json() or {}
    batch_id = data.get('batch_id')
    adj_type = data.get('adjustment_type', 'Correction') # 'Damaged', 'Expired Disposal', 'Correction', 'Supplier Return'
    qty_change = int(data.get('quantity_changed', 0)) # can be negative or positive
    reason = data.get('reason', '').strip()

    if not batch_id or qty_change == 0 or not reason:
        return jsonify({'success': False, 'message': 'Batch ID, non-zero quantity change, and justification reason are required.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT b.*, m.brand_name FROM batches b JOIN medicines m ON b.medicine_id = m.id WHERE b.id = ?;", (batch_id,))
    batch = cursor.fetchone()
    if not batch:
        conn.close()
        return jsonify({'success': False, 'message': 'Batch not found'}), 404

    old_qty = batch['current_quantity']
    new_qty = old_qty + qty_change
    if new_qty < 0:
        conn.close()
        return jsonify({'success': False, 'message': f'Cannot deduct {abs(qty_change)} units; current batch only has {old_qty} units.'}), 400

    cursor.execute("UPDATE batches SET current_quantity = ? WHERE id = ?;", (new_qty, batch_id))
    cursor.execute("""
    INSERT INTO stock_adjustments (medicine_id, batch_id, user_id, adjustment_type, quantity_changed, previous_quantity, new_quantity, reason)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, (batch['medicine_id'], batch_id, request.current_user['id'], adj_type, qty_change, old_qty, new_qty, reason))

    log_audit(conn, request.current_user['id'], 'STOCK_ADJUSTMENT', 'BATCH', batch_id, f"{adj_type}: {qty_change} units for {batch['brand_name']} batch {batch['batch_number']}. Reason: {reason}")
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Inventory successfully adjusted.', 'previous_quantity': old_qty, 'new_quantity': new_qty})

@app.route('/api/inventory/alerts', methods=['GET'])
@token_required
def get_inventory_alerts():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Low stock alerts
    cursor.execute("""
    SELECT m.id, m.sku, m.brand_name, m.generic_name, m.reorder_level, COALESCE(SUM(b.current_quantity), 0) AS total_stock
    FROM medicines m
    LEFT JOIN batches b ON m.id = b.medicine_id AND b.status = 'active'
    GROUP BY m.id
    HAVING total_stock <= m.reorder_level
    ORDER BY total_stock ASC;
    """)
    low_stock = rows_to_list(cursor.fetchall())

    # 2. Expiry alerts
    cursor.execute("""
    SELECT b.id as batch_id, b.batch_number, b.expiry_date, b.current_quantity,
           m.id as medicine_id, m.brand_name, m.generic_name, m.unit_price, s.name as supplier_name,
           CAST((JULIANDAY(b.expiry_date) - JULIANDAY('now')) AS INTEGER) as days_remaining
    FROM batches b
    JOIN medicines m ON b.medicine_id = m.id
    LEFT JOIN suppliers s ON b.supplier_id = s.id
    WHERE b.current_quantity > 0 AND b.expiry_date <= DATE('now', '+90 days')
    ORDER BY b.expiry_date ASC;
    """)
    expiring = rows_to_list(cursor.fetchall())
    conn.close()

    expired = [b for b in expiring if b['days_remaining'] < 0]
    critical_30 = [b for b in expiring if 0 <= b['days_remaining'] <= 30]
    warning_90 = [b for b in expiring if 30 < b['days_remaining'] <= 90]

    return jsonify({
        'success': True,
        'low_stock_count': len(low_stock),
        'low_stock_items': low_stock,
        'expired_count': len(expired),
        'expired_items': expired,
        'critical_30_count': len(critical_30),
        'critical_30_items': critical_30,
        'warning_90_count': len(warning_90),
        'warning_90_items': warning_90
    })

@app.route('/api/inventory/barcode/<query>', methods=['GET'])
@token_required
def lookup_barcode(query):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT m.*, COALESCE(SUM(b.current_quantity), 0) as total_stock,
           MIN(CASE WHEN b.current_quantity > 0 THEN b.expiry_date ELSE NULL END) as nearest_expiry
    FROM medicines m
    LEFT JOIN batches b ON m.id = b.medicine_id AND b.status = 'active'
    WHERE m.barcode = ? OR m.sku = ? OR m.brand_name LIKE ?
    GROUP BY m.id;
    """, (query, query, f"%{query}%"))
    item = cursor.fetchone()

    if not item:
        conn.close()
        return jsonify({'success': False, 'message': f'No medicine found matching barcode/SKU "{query}"'}), 404

    # Fetch available active batches in FEFO order (First-Expired, First-Out)
    cursor.execute("""
    SELECT * FROM batches 
    WHERE medicine_id = ? AND current_quantity > 0 AND status = 'active' AND expiry_date >= DATE('now')
    ORDER BY expiry_date ASC;
    """, (item['id'],))
    batches = rows_to_list(cursor.fetchall())
    conn.close()

    res = dict(item)
    res['active_batches'] = batches
    return jsonify({'success': True, 'medicine': res})

# ==========================================
# 4. PHYSICAL STOCK TAKING & AUDIT
# ==========================================
@app.route('/api/stock-takes', methods=['GET'])
@token_required
def get_stock_takes():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT st.*, u.full_name as conducted_by_name
    FROM stock_takes st
    JOIN users u ON st.conducted_by = u.id
    ORDER BY st.started_at DESC;
    """)
    audits = rows_to_list(cursor.fetchall())
    conn.close()
    return jsonify({'success': True, 'audits': audits})

@app.route('/api/stock-takes', methods=['POST'])
@token_required
@roles_required('admin', 'pharmacist', 'inventory_manager')
def create_stock_take():
    data = request.get_json() or {}
    title = data.get('title', f"Stock Audit {datetime.now().strftime('%b %Y')}")
    audit_code = f"AUDIT-{datetime.now().strftime('%Y%m%d-%H%M')}"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO stock_takes (audit_code, title, conducted_by, status, notes)
    VALUES (?, ?, ?, 'Open', ?);
    """, (audit_code, title, request.current_user['id'], data.get('notes', 'Physical cycle count.')))
    audit_id = cursor.lastrowid

    # Populate snapshot of all active batches with current system quantities
    cursor.execute("""
    SELECT b.id as batch_id, b.medicine_id, b.current_quantity, b.unit_cost
    FROM batches b
    WHERE b.status = 'active';
    """)
    active_batches = cursor.fetchall()

    for b in active_batches:
        cursor.execute("""
        INSERT INTO stock_take_items (stock_take_id, medicine_id, batch_id, system_quantity, physical_count, variance, unit_cost, variance_value)
        VALUES (?, ?, ?, ?, ?, 0, ?, 0.0);
        """, (audit_id, b['medicine_id'], b['batch_id'], b['current_quantity'], b['current_quantity'], b['unit_cost']))

    log_audit(conn, request.current_user['id'], 'START_STOCK_TAKE', 'STOCK_TAKE', audit_id, f"Initiated physical inventory count: {audit_code}")
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'audit_id': audit_id, 'audit_code': audit_code})

@app.route('/api/stock-takes/<int:audit_id>', methods=['GET'])
@token_required
def get_stock_take_detail(audit_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT st.*, u.full_name as conducted_by_name
    FROM stock_takes st
    JOIN users u ON st.conducted_by = u.id
    WHERE st.id = ?;
    """, (audit_id,))
    audit = cursor.fetchone()
    if not audit:
        conn.close()
        return jsonify({'success': False, 'message': 'Stock audit not found'}), 404

    cursor.execute("""
    SELECT sti.*, m.brand_name, m.generic_name, m.sku, m.barcode, b.batch_number, b.expiry_date
    FROM stock_take_items sti
    JOIN medicines m ON sti.medicine_id = m.id
    JOIN batches b ON sti.batch_id = b.id
    WHERE sti.stock_take_id = ?
    ORDER BY m.brand_name ASC;
    """, (audit_id,))
    items = rows_to_list(cursor.fetchall())
    conn.close()

    res = dict(audit)
    res['items'] = items
    return jsonify({'success': True, 'audit': res})

@app.route('/api/stock-takes/<int:audit_id>/count', methods=['POST'])
@token_required
@roles_required('admin', 'pharmacist', 'inventory_manager')
def update_stock_take_count(audit_id):
    data = request.get_json() or {}
    item_id = data.get('item_id')
    physical_count = int(data.get('physical_count', 0))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stock_take_items WHERE id = ? AND stock_take_id = ?;", (item_id, audit_id))
    item = cursor.fetchone()
    if not item:
        conn.close()
        return jsonify({'success': False, 'message': 'Item record not found in this audit.'}), 404

    sys_qty = item['system_quantity']
    variance = physical_count - sys_qty
    var_val = round(variance * item['unit_cost'], 2)

    cursor.execute("""
    UPDATE stock_take_items 
    SET physical_count = ?, variance = ?, variance_value = ?, notes = ?
    WHERE id = ?;
    """, (physical_count, variance, var_val, data.get('notes', ''), item_id))

    conn.commit()
    conn.close()
    return jsonify({'success': True, 'variance': variance, 'variance_value': var_val})

@app.route('/api/stock-takes/<int:audit_id>/reconcile', methods=['POST'])
@token_required
@roles_required('admin', 'pharmacist')
def reconcile_stock_take(audit_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stock_takes WHERE id = ?;", (audit_id,))
    audit = cursor.fetchone()
    if not audit:
        conn.close()
        return jsonify({'success': False, 'message': 'Audit not found'}), 404

    if audit['status'] == 'Reconciled':
        conn.close()
        return jsonify({'success': False, 'message': 'Audit is already reconciled.'}), 400

    cursor.execute("SELECT * FROM stock_take_items WHERE stock_take_id = ?;", (audit_id,))
    items = cursor.fetchall()

    net_variance_val = 0.0
    adjusted_count = 0

    for item in items:
        variance = item['variance']
        if variance != 0:
            # Update the batch quantity directly
            cursor.execute("UPDATE batches SET current_quantity = ? WHERE id = ?;", (item['physical_count'], item['batch_id']))
            cursor.execute("""
            INSERT INTO stock_adjustments (medicine_id, batch_id, user_id, adjustment_type, quantity_changed, previous_quantity, new_quantity, reason)
            VALUES (?, ?, ?, 'Physical Audit', ?, ?, ?, ?);
            """, (item['medicine_id'], item['batch_id'], request.current_user['id'], variance, item['system_quantity'], item['physical_count'], f"Reconciled via {audit['audit_code']}"))
            adjusted_count += 1
            net_variance_val += item['variance_value']

    cursor.execute("""
    UPDATE stock_takes 
    SET status = 'Reconciled', completed_at = CURRENT_TIMESTAMP, total_items_counted = ?, net_variance_value = ?
    WHERE id = ?;
    """, (len(items), net_variance_val, audit_id))

    log_audit(conn, request.current_user['id'], 'RECONCILE_STOCK_TAKE', 'STOCK_TAKE', audit_id, f"Reconciled {audit['audit_code']}. {adjusted_count} batches adjusted. Net variance: ZK {net_variance_val:,.2f}")
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': f"Stock take {audit['audit_code']} reconciled successfully. {adjusted_count} discrepancies adjusted in real-time.",
        'net_variance_value': net_variance_val
    })

# ==========================================
# 5. CLINICAL DRUG SAFETY CHECKER
# ==========================================
@app.route('/api/pos/check-safety', methods=['POST'])
@token_required
def check_safety():
    data = request.get_json() or {}
    cart_items = data.get('items', []) # [{'medicine_id': 1, 'generic_name': 'Warfarin'}, ...]
    patient_id = data.get('patient_id')

    warnings = []
    conn = get_db()
    cursor = conn.cursor()

    # 1. Check Patient Allergies
    if patient_id:
        cursor.execute("SELECT full_name, allergies FROM patients WHERE id = ?;", (patient_id,))
        patient = cursor.fetchone()
        if patient and patient['allergies']:
            allergies = [a.strip().lower() for a in patient['allergies'].split(',') if a.strip()]
            for item in cart_items:
                med_id = item.get('medicine_id')
                cursor.execute("SELECT brand_name, generic_name, category FROM medicines WHERE id = ?;", (med_id,))
                med = cursor.fetchone()
                if med:
                    gen_lower = med['generic_name'].lower()
                    brand_lower = med['brand_name'].lower()
                    cat_lower = med['category'].lower()

                    for allergy in allergies:
                        # Direct match or cross-reactivity patterns
                        if (allergy in gen_lower or allergy in brand_lower or
                            (allergy == 'penicillin' and ('amoxicillin' in gen_lower or 'augmentin' in brand_lower or 'ampicillin' in gen_lower)) or
                            (allergy == 'aspirin' and ('ibuprofen' in gen_lower or 'nsaid' in cat_lower))):
                            warnings.append({
                                'type': 'ALLERGY_ALERT',
                                'severity': 'CRITICAL',
                                'drug': med['brand_name'],
                                'title': f"Patient Allergy Contraindication: {allergy.upper()}",
                                'message': f"Patient {patient['full_name']} has documented allergy to '{allergy}'. Dispensing {med['brand_name']} ({med['generic_name']}) is high risk!",
                                'action_required': 'Pharmacist clinical intervention required before dispensing.'
                            })

    # 2. Check Drug-to-Drug Interactions between all items in cart
    if len(cart_items) >= 2:
        # Collect all generic names
        generic_names = []
        for item in cart_items:
            med_id = item.get('medicine_id')
            cursor.execute("SELECT brand_name, generic_name FROM medicines WHERE id = ?;", (med_id,))
            med = cursor.fetchone()
            if med:
                generic_names.append((med['brand_name'], med['generic_name']))

        # Cross-reference pairwise
        for i in range(len(generic_names)):
            for j in range(i + 1, len(generic_names)):
                brand_a, gen_a = generic_names[i]
                brand_b, gen_b = generic_names[j]

                cursor.execute("""
                SELECT * FROM drug_interactions 
                WHERE (drug_a_generic LIKE ? AND drug_b_generic LIKE ?)
                   OR (drug_a_generic LIKE ? AND drug_b_generic LIKE ?);
                """, (f"%{gen_a}%", f"%{gen_b}%", f"%{gen_b}%", f"%{gen_a}%"))
                inter = cursor.fetchone()

                if inter:
                    warnings.append({
                        'type': 'DRUG_INTERACTION',
                        'severity': inter['severity'],
                        'drug_a': brand_a,
                        'drug_b': brand_b,
                        'title': f"{inter['severity']} Interaction: {gen_a} + {gen_b}",
                        'message': inter['clinical_effect'],
                        'recommendation': inter['recommendation']
                    })

    conn.close()
    return jsonify({
        'success': True,
        'has_warnings': len(warnings) > 0,
        'critical_count': len([w for w in warnings if w.get('severity') in ('CRITICAL', 'Major')]),
        'warnings': warnings
    })

# ==========================================
# 6. POINT OF SALE (POS) & FEFO DISPENSING
# ==========================================
@app.route('/api/pos/checkout', methods=['POST'])
@token_required
def checkout():
    data = request.get_json() or {}
    items = data.get('items', []) # [{'medicine_id': 1, 'quantity': 2, 'unit_price': 11.50}]
    patient_id = data.get('patient_id')
    prescription_id = data.get('prescription_id')
    payment_method = data.get('payment_method', 'Cash') # Cash, Card, Insurance, Mobile Money
    discount_amount = float(data.get('discount_amount', 0.0))
    amount_paid = float(data.get('amount_paid', 0.0))
    notes = data.get('notes', '')

    if not items:
        return jsonify({'success': False, 'message': 'No items in cart for checkout.'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Pre-check available stock across batches for all items
    fefo_allocations = []
    subtotal = 0.0
    total_cost = 0.0

    today_str = str(date.today())

    for it in items:
        med_id = it['medicine_id']
        requested_qty = int(it['quantity'])
        cursor.execute("SELECT * FROM medicines WHERE id = ?;", (med_id,))
        med = cursor.fetchone()
        if not med:
            conn.close()
            return jsonify({'success': False, 'message': f'Medicine ID {med_id} not found'}), 404

        # Fetch active batches in strict FEFO order (First-Expired, First-Out, excluding expired)
        cursor.execute("""
        SELECT * FROM batches 
        WHERE medicine_id = ? AND current_quantity > 0 AND status = 'active' AND expiry_date >= ?
        ORDER BY expiry_date ASC;
        """, (med_id, today_str))
        available_batches = cursor.fetchall()

        available_qty = sum(b['current_quantity'] for b in available_batches)
        if available_qty < requested_qty:
            conn.close()
            return jsonify({
                'success': False,
                'message': f"Insufficient unexpired stock for '{med['brand_name']}'. Requested: {requested_qty}, Available: {available_qty}"
            }), 400

        # FEFO allocation across oldest unexpired batches
        remaining_to_deduct = requested_qty
        med_allocations = []

        for b in available_batches:
            if remaining_to_deduct <= 0:
                break
            deduct = min(b['current_quantity'], remaining_to_deduct)
            price = med['unit_price']
            cost = b['unit_cost']
            profit = (price - cost) * deduct

            med_allocations.append({
                'batch_id': b['id'],
                'batch_number': b['batch_number'],
                'expiry_date': b['expiry_date'],
                'quantity': deduct,
                'unit_cost': cost,
                'unit_price': price,
                'total_price': price * deduct,
                'profit': profit
            })
            subtotal += price * deduct
            total_cost += cost * deduct
            remaining_to_deduct -= deduct

        fefo_allocations.append({
            'medicine_id': med_id,
            'brand_name': med['brand_name'],
            'generic_name': med['generic_name'],
            'allocations': med_allocations
        })

    # Calculations
    tax_amount = round((subtotal - discount_amount) * 0.04, 2)
    total_amount = round(subtotal - discount_amount + tax_amount, 2)
    change_due = round(max(0.0, amount_paid - total_amount), 2) if payment_method == 'Cash' else 0.0

    # Generate Invoice Number
    inv_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    # Record Sale
    cursor.execute("""
    INSERT INTO sales (invoice_number, patient_id, user_id, prescription_id, subtotal, discount_amount, tax_amount, total_amount, amount_paid, change_due, payment_method, payment_reference, status, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Completed', ?);
    """, (
        inv_number,
        patient_id,
        request.current_user['id'],
        prescription_id,
        subtotal,
        discount_amount,
        tax_amount,
        total_amount,
        amount_paid if amount_paid > 0 else total_amount,
        change_due,
        payment_method,
        f"TXN-{random.randint(100000, 999999)}",
        notes
    ))
    sale_id = cursor.lastrowid

    # Deduct stock from batches and insert sale_items
    for med_group in fefo_allocations:
        med_id = med_group['medicine_id']
        for alloc in med_group['allocations']:
            cursor.execute("""
            INSERT INTO sale_items (sale_id, medicine_id, batch_id, quantity, unit_cost, unit_price, total_price, profit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (sale_id, med_id, alloc['batch_id'], alloc['quantity'], alloc['unit_cost'], alloc['unit_price'], alloc['total_price'], alloc['profit']))

            cursor.execute("""
            UPDATE batches SET current_quantity = current_quantity - ? WHERE id = ?;
            """, (alloc['quantity'], alloc['batch_id']))

    # If linked to a prescription, mark items as dispensed
    if prescription_id:
        cursor.execute("""
        UPDATE prescriptions 
        SET status = 'Dispensed', dispensed_pharmacist_id = ?, dispensed_at = CURRENT_TIMESTAMP
        WHERE id = ?;
        """, (request.current_user['id'], prescription_id))

        cursor.execute("""
        UPDATE prescription_items 
        SET quantity_dispensed = quantity_prescribed
        WHERE prescription_id = ?;
        """, (prescription_id,))

    log_audit(conn, request.current_user['id'], 'DISPENSE_SALE', 'SALE', sale_id, f"Completed checkout {inv_number}. Total: ZK {total_amount:,.2f} via {payment_method}")
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': f"Dispense & Checkout completed successfully. Invoice: {inv_number}",
        'sale_id': sale_id,
        'invoice_number': inv_number,
        'subtotal': subtotal,
        'discount_amount': discount_amount,
        'tax_amount': tax_amount,
        'total_amount': total_amount,
        'amount_paid': amount_paid if amount_paid > 0 else total_amount,
        'change_due': change_due,
        'payment_method': payment_method,
        'allocations': fefo_allocations
    })

# ==========================================
# 7. DIGITAL PRESCRIPTIONS
# ==========================================
@app.route('/api/prescriptions', methods=['GET'])
@token_required
def get_prescriptions():
    status = request.args.get('status', '').strip()
    conn = get_db()
    cursor = conn.cursor()

    query = """
    SELECT rx.*, p.full_name as patient_name, p.patient_code, p.phone as patient_phone, p.allergies as patient_allergies,
           pr.full_name as prescriber_name, pr.license_number as prescriber_license, pr.hospital_clinic,
           u1.full_name as verified_by_name, u2.full_name as dispensed_by_name,
           (SELECT COUNT(*) FROM prescription_items WHERE prescription_id = rx.id) as item_count
    FROM prescriptions rx
    JOIN patients p ON rx.patient_id = p.id
    JOIN prescribers pr ON rx.prescriber_id = pr.id
    LEFT JOIN users u1 ON rx.verification_pharmacist_id = u1.id
    LEFT JOIN users u2 ON rx.dispensed_pharmacist_id = u2.id
    WHERE 1=1
    """
    params = []
    if status and status != 'All':
        query += " AND rx.status = ?"
        params.append(status)

    query += " ORDER BY rx.rx_date DESC, rx.id DESC;"

    cursor.execute(query, params)
    rxs = rows_to_list(cursor.fetchall())
    conn.close()
    return jsonify({'success': True, 'prescriptions': rxs})

@app.route('/api/prescriptions/<int:rx_id>', methods=['GET'])
@token_required
def get_prescription_detail(rx_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT rx.*, p.full_name as patient_name, p.patient_code, p.phone as patient_phone, p.date_of_birth, p.gender, p.allergies, p.chronic_conditions, p.insurance_provider, p.insurance_policy_number,
           pr.full_name as prescriber_name, pr.license_number as prescriber_license, pr.hospital_clinic, pr.specialization, pr.phone as prescriber_phone,
           u1.full_name as verified_by_name, u2.full_name as dispensed_by_name
    FROM prescriptions rx
    JOIN patients p ON rx.patient_id = p.id
    JOIN prescribers pr ON rx.prescriber_id = pr.id
    LEFT JOIN users u1 ON rx.verification_pharmacist_id = u1.id
    LEFT JOIN users u2 ON rx.dispensed_pharmacist_id = u2.id
    WHERE rx.id = ?;
    """, (rx_id,))
    rx = cursor.fetchone()
    if not rx:
        conn.close()
        return jsonify({'success': False, 'message': 'Prescription not found'}), 404

    cursor.execute("""
    SELECT rxi.*, m.brand_name, m.generic_name, m.dosage_form, m.strength, m.unit_price, m.requires_prescription,
           COALESCE((SELECT SUM(current_quantity) FROM batches WHERE medicine_id = m.id AND current_quantity > 0 AND expiry_date >= DATE('now')), 0) as available_stock
    FROM prescription_items rxi
    JOIN medicines m ON rxi.medicine_id = m.id
    WHERE rxi.prescription_id = ?;
    """, (rx_id,))
    items = rows_to_list(cursor.fetchall())
    conn.close()

    res = dict(rx)
    res['items'] = items
    return jsonify({'success': True, 'prescription': res})

@app.route('/api/prescriptions', methods=['POST'])
@token_required
@roles_required('admin', 'pharmacist', 'dispenser')
def create_prescription():
    data = request.get_json() or {}
    patient_id = data.get('patient_id')
    prescriber_id = data.get('prescriber_id')
    items = data.get('items', []) # [{'medicine_id': 1, 'dosage': '1 tab daily', 'quantity': 30, 'refills': 1}]

    if not patient_id or not prescriber_id or not items:
        return jsonify({'success': False, 'message': 'Patient, Prescriber, and at least one medication item are required.'}), 400

    rx_number = f"RX-{datetime.now().strftime('%Y')}-{random.randint(10000, 99999)}"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO prescriptions (rx_number, patient_id, prescriber_id, rx_date, status, diagnosis, notes)
    VALUES (?, ?, ?, DATE('now'), 'Pending', ?, ?);
    """, (rx_number, patient_id, prescriber_id, data.get('diagnosis', 'Clinical Consultation'), data.get('notes', 'Walk-in / E-Prescription Entry')))
    rx_id = cursor.lastrowid

    for it in items:
        cursor.execute("""
        INSERT INTO prescription_items (prescription_id, medicine_id, dosage_instructions, quantity_prescribed, refills_allowed, refills_remaining)
        VALUES (?, ?, ?, ?, ?, ?);
        """, (rx_id, it['medicine_id'], it.get('dosage_instructions', 'As directed by physician'), int(it.get('quantity_prescribed', 1)), int(it.get('refills_allowed', 0)), int(it.get('refills_allowed', 0))))

    log_audit(conn, request.current_user['id'], 'CREATE_PRESCRIPTION', 'PRESCRIPTION', rx_id, f"Registered e-prescription {rx_number} with {len(items)} items")
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': f'Prescription {rx_number} created successfully.', 'prescription_id': rx_id, 'rx_number': rx_number})

@app.route('/api/prescriptions/<int:rx_id>/verify', methods=['POST'])
@token_required
@roles_required('admin', 'pharmacist')
def verify_prescription(rx_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prescriptions WHERE id = ?;", (rx_id,))
    rx = cursor.fetchone()
    if not rx:
        conn.close()
        return jsonify({'success': False, 'message': 'Prescription not found'}), 404

    cursor.execute("""
    UPDATE prescriptions 
    SET status = 'Verified', verification_pharmacist_id = ?
    WHERE id = ?;
    """, (request.current_user['id'], rx_id))

    log_audit(conn, request.current_user['id'], 'VERIFY_PRESCRIPTION', 'PRESCRIPTION', rx_id, f"Clinical verification approved for {rx['rx_number']} by {request.current_user['full_name']} (Lic: {request.current_user.get('license_number', 'N/A')})")
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': f"Prescription {rx['rx_number']} verified and approved for dispensing."})

# ==========================================
# 8. PATIENTS & PRESCRIBERS & SUPPLIERS DIRECTORY
# ==========================================
@app.route('/api/records/patients', methods=['GET', 'POST'])
@token_required
def manage_patients():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.get_json() or {}
        name = data.get('full_name', '').strip()
        if not name:
            conn.close()
            return jsonify({'success': False, 'message': 'Full name is required.'}), 400

        cursor.execute("SELECT COUNT(*) as count FROM patients;")
        code = f"PT-{1000 + cursor.fetchone()['count'] + 1}"

        cursor.execute("""
        INSERT INTO patients (patient_code, full_name, date_of_birth, gender, phone, email, address, allergies, chronic_conditions, insurance_provider, insurance_policy_number, emergency_contact, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            code,
            name,
            data.get('date_of_birth'),
            data.get('gender', 'Other'),
            data.get('phone', ''),
            data.get('email', ''),
            data.get('address', ''),
            data.get('allergies', 'None Known'),
            data.get('chronic_conditions', 'None'),
            data.get('insurance_provider', ''),
            data.get('insurance_policy_number', ''),
            data.get('emergency_contact', ''),
            data.get('notes', '')
        ))
        pid = cursor.lastrowid
        log_audit(conn, request.current_user['id'], 'CREATE_PATIENT', 'PATIENT', pid, f"Registered new patient {name} ({code})")
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Patient {name} ({code}) created successfully.', 'id': pid, 'patient_code': code})

    # GET
    search = request.args.get('search', '').strip()
    query = "SELECT * FROM patients"
    params = []
    if search:
        query += " WHERE full_name LIKE ? OR patient_code LIKE ? OR phone LIKE ?"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    query += " ORDER BY full_name ASC;"

    cursor.execute(query, params)
    patients = rows_to_list(cursor.fetchall())
    conn.close()
    return jsonify({'success': True, 'patients': patients})

@app.route('/api/records/prescribers', methods=['GET', 'POST'])
@token_required
def manage_prescribers():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.get_json() or {}
        name = data.get('full_name', '').strip()
        lic = data.get('license_number', '').strip()
        if not name or not lic:
            conn.close()
            return jsonify({'success': False, 'message': 'Doctor name and medical license are required.'}), 400

        try:
            cursor.execute("""
            INSERT INTO prescribers (full_name, license_number, hospital_clinic, specialization, phone, email, address)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (name, lic, data.get('hospital_clinic', ''), data.get('specialization', 'General Practice'), data.get('phone', ''), data.get('email', ''), data.get('address', '')))
            doc_id = cursor.lastrowid
            log_audit(conn, request.current_user['id'], 'CREATE_PRESCRIBER', 'PRESCRIBER', doc_id, f"Registered doctor {name} ({lic})")
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': f'Doctor {name} registered.', 'id': doc_id})
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'success': False, 'message': f'License number {lic} is already registered.'}), 400

    # GET
    cursor.execute("SELECT * FROM prescribers ORDER BY full_name ASC;")
    prescribers = rows_to_list(cursor.fetchall())
    conn.close()
    return jsonify({'success': True, 'prescribers': prescribers})

@app.route('/api/records/suppliers', methods=['GET', 'POST'])
@token_required
def manage_suppliers():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        if not name:
            conn.close()
            return jsonify({'success': False, 'message': 'Supplier name is required.'}), 400

        cursor.execute("SELECT COUNT(*) as count FROM suppliers;")
        code = f"SUP-{data.get('name', 'GEN')[:3].upper()}-{cursor.fetchone()['count'] + 1:02d}"

        cursor.execute("""
        INSERT INTO suppliers (name, code, contact_person, email, phone, address, lead_time_days, payment_terms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (name, code, data.get('contact_person', ''), data.get('email', ''), data.get('phone', ''), data.get('address', ''), int(data.get('lead_time_days', 3)), data.get('payment_terms', 'Net 30')))
        sup_id = cursor.lastrowid
        log_audit(conn, request.current_user['id'], 'CREATE_SUPPLIER', 'SUPPLIER', sup_id, f"Registered supplier {name}")
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Supplier {name} created.', 'id': sup_id})

    # GET
    cursor.execute("SELECT * FROM suppliers ORDER BY name ASC;")
    suppliers = rows_to_list(cursor.fetchall())
    conn.close()
    return jsonify({'success': True, 'suppliers': suppliers})

# ==========================================
# 9. BUSINESS INTELLIGENCE & STATISTICS
# ==========================================
@app.route('/api/analytics/kpis', methods=['GET'])
@token_required
def get_kpis():
    conn = get_db()
    cursor = conn.cursor()

    today_str = date.today().strftime('%Y-%m-%d')
    yesterday_str = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')

    # Today's Revenue & Profit
    cursor.execute("""
    SELECT COALESCE(SUM(total_amount), 0) as today_revenue,
           COALESCE(COUNT(id), 0) as today_transactions
    FROM sales 
    WHERE DATE(created_at) = ? AND status = 'Completed';
    """, (today_str,))
    today_res = cursor.fetchone()

    # Yesterday's Revenue
    cursor.execute("""
    SELECT COALESCE(SUM(total_amount), 0) as yesterday_revenue
    FROM sales 
    WHERE DATE(created_at) = ? AND status = 'Completed';
    """, (yesterday_str,))
    yesterday_rev = cursor.fetchone()['yesterday_revenue']

    # Total Gross Profit across all completed sales
    cursor.execute("""
    SELECT COALESCE(SUM(si.profit), 0) as total_profit,
           COALESCE(SUM(s.total_amount), 0) as total_revenue
    FROM sale_items si
    JOIN sales s ON si.sale_id = s.id
    WHERE s.status = 'Completed';
    """)
    totals = cursor.fetchone()

    # Low Stock Items Count
    cursor.execute("""
    SELECT COUNT(*) as count FROM (
        SELECT m.id, COALESCE(SUM(b.current_quantity), 0) as stock, m.reorder_level
        FROM medicines m
        LEFT JOIN batches b ON m.id = b.medicine_id AND b.status = 'active'
        GROUP BY m.id
        HAVING stock <= m.reorder_level
    );
    """)
    low_stock_count = cursor.fetchone()['count']

    # Expiring batches count (<= 90 days)
    cursor.execute("""
    SELECT COUNT(*) as count 
    FROM batches 
    WHERE current_quantity > 0 AND status = 'active' AND expiry_date <= DATE('now', '+90 days');
    """)
    expiring_count = cursor.fetchone()['count']

    # Pending Prescriptions Count
    cursor.execute("SELECT COUNT(*) as count FROM prescriptions WHERE status = 'Pending';")
    pending_rx = cursor.fetchone()['count']

    # Total catalog count
    cursor.execute("SELECT COUNT(*) as count FROM medicines;")
    total_meds = cursor.fetchone()['count']

    conn.close()

    today_rev = today_res['today_revenue']
    rev_growth = round(((today_rev - yesterday_rev) / yesterday_rev * 100), 1) if yesterday_rev > 0 else 0.0
    profit_margin = round((totals['total_profit'] / totals['total_revenue'] * 100), 1) if totals['total_revenue'] > 0 else 0.0

    return jsonify({
        'success': True,
        'today_revenue': round(today_rev, 2),
        'today_transactions': today_res['today_transactions'],
        'revenue_growth_pct': rev_growth,
        'all_time_revenue': round(totals['total_revenue'], 2),
        'all_time_profit': round(totals['total_profit'], 2),
        'profit_margin_pct': profit_margin,
        'low_stock_count': low_stock_count,
        'expiring_count': expiring_count,
        'pending_rx_count': pending_rx,
        'total_medications': total_meds
    })

@app.route('/api/analytics/charts', methods=['GET'])
@token_required
def get_chart_analytics():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Sales & Profit by Date over the last 14 days
    cursor.execute("""
    SELECT DATE(s.created_at) as sale_date,
           COALESCE(SUM(s.total_amount), 0) as revenue,
           COALESCE(SUM(si.profit), 0) as profit,
           COUNT(DISTINCT s.id) as orders
    FROM sales s
    LEFT JOIN sale_items si ON s.id = si.sale_id
    WHERE s.created_at >= DATE('now', '-14 days') AND s.status = 'Completed'
    GROUP BY DATE(s.created_at)
    ORDER BY sale_date ASC;
    """)
    daily_sales = rows_to_list(cursor.fetchall())

    # 2. Top 8 Fast-Moving / High Revenue Medicines
    cursor.execute("""
    SELECT m.brand_name, m.generic_name, m.category,
           SUM(si.quantity) as total_units_sold,
           ROUND(SUM(si.total_price), 2) as total_revenue,
           ROUND(SUM(si.profit), 2) as total_profit
    FROM sale_items si
    JOIN medicines m ON si.medicine_id = m.id
    GROUP BY m.id
    ORDER BY total_revenue DESC
    LIMIT 8;
    """)
    top_selling = rows_to_list(cursor.fetchall())

    # 3. Category Sales Distribution
    cursor.execute("""
    SELECT m.category,
           ROUND(SUM(si.total_price), 2) as revenue,
           COUNT(si.id) as item_count
    FROM sale_items si
    JOIN medicines m ON si.medicine_id = m.id
    GROUP BY m.category
    ORDER BY revenue DESC;
    """)
    category_split = rows_to_list(cursor.fetchall())

    # 4. Expiry Risk Financial Matrix (ZK Value of inventory at risk)
    cursor.execute("""
    SELECT 
        SUM(CASE WHEN expiry_date < DATE('now') THEN current_quantity * unit_cost ELSE 0 END) as expired_value,
        SUM(CASE WHEN expiry_date >= DATE('now') AND expiry_date <= DATE('now', '+30 days') THEN current_quantity * unit_cost ELSE 0 END) as value_30d,
        SUM(CASE WHEN expiry_date > DATE('now', '+30 days') AND expiry_date <= DATE('now', '+90 days') THEN current_quantity * unit_cost ELSE 0 END) as value_90d,
        SUM(CASE WHEN expiry_date > DATE('now', '+90 days') THEN current_quantity * unit_cost ELSE 0 END) as healthy_value
    FROM batches
    WHERE current_quantity > 0 AND status = 'active';
    """)
    risk_matrix = dict_from_row(cursor.fetchone())

    # 5. Payment Methods Breakdown
    cursor.execute("""
    SELECT payment_method, COUNT(*) as count, ROUND(SUM(total_amount), 2) as total_amount
    FROM sales
    WHERE status = 'Completed'
    GROUP BY payment_method;
    """)
    payment_methods = rows_to_list(cursor.fetchall())

    conn.close()

    return jsonify({
        'success': True,
        'daily_trends': daily_sales,
        'top_selling': top_selling,
        'category_split': category_split,
        'risk_matrix': risk_matrix,
        'payment_methods': payment_methods
    })

# ==========================================
# 10. SYSTEM USERS & AUDIT TRAIL
# ==========================================
@app.route('/api/users', methods=['GET', 'POST'])
@token_required
@roles_required('admin')
def manage_users():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.get_json() or {}
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        full_name = data.get('full_name', '').strip()
        role = data.get('role', 'dispenser').strip()

        if not username or not password or not full_name:
            conn.close()
            return jsonify({'success': False, 'message': 'Username, password, and full name are required.'}), 400

        salt = bcrypt.gensalt(rounds=10)
        pw_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

        try:
            cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, role, license_number, email, phone)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (username, pw_hash, full_name, role, data.get('license_number'), data.get('email'), data.get('phone')))
            uid = cursor.lastrowid
            log_audit(conn, request.current_user['id'], 'CREATE_USER', 'USER', uid, f"Created staff user account '{username}' with role '{role}'")
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': f"User account '{username}' created successfully.", 'user_id': uid})
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'success': False, 'message': f"Username '{username}' already exists."}), 400

    # GET
    cursor.execute("SELECT id, username, full_name, role, license_number, email, phone, is_active, last_login, created_at FROM users ORDER BY id ASC;")
    users = rows_to_list(cursor.fetchall())
    conn.close()
    return jsonify({'success': True, 'users': users})

@app.route('/api/users/<int:user_id>/toggle-status', methods=['POST'])
@token_required
@roles_required('admin')
def toggle_user_status(user_id):
    if user_id == request.current_user['id']:
        return jsonify({'success': False, 'message': 'Cannot deactivate your own active session account.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT is_active, username FROM users WHERE id = ?;", (user_id,))
    u = cursor.fetchone()
    if not u:
        conn.close()
        return jsonify({'success': False, 'message': 'User not found'}), 404

    new_status = 0 if u['is_active'] else 1
    cursor.execute("UPDATE users SET is_active = ? WHERE id = ?;", (new_status, user_id))
    action = "Activated" if new_status else "Suspended"
    log_audit(conn, request.current_user['id'], 'TOGGLE_USER_STATUS', 'USER', user_id, f"{action} account for user {u['username']}")
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': f"User {u['username']} {action.lower()}.", 'is_active': new_status})

@app.route('/api/audit/logs', methods=['GET'])
@token_required
def get_audit_logs():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT al.*, u.full_name as user_name, u.role as user_role
    FROM audit_logs al
    LEFT JOIN users u ON al.user_id = u.id
    ORDER BY al.created_at DESC
    LIMIT 100;
    """)
    logs = rows_to_list(cursor.fetchall())
    conn.close()
    return jsonify({'success': True, 'logs': logs})

# ==========================================
# 11. EXPORTS & PRINTABLE INVOICES
# ==========================================
@app.route('/api/sales/<int:sale_id>/receipt', methods=['GET'])
@token_required
def get_sale_receipt(sale_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT s.*, p.full_name as patient_name, p.patient_code, u.full_name as cashier_name
    FROM sales s
    LEFT JOIN patients p ON s.patient_id = p.id
    JOIN users u ON s.user_id = u.id
    WHERE s.id = ?;
    """, (sale_id,))
    sale = cursor.fetchone()
    if not sale:
        conn.close()
        return jsonify({'success': False, 'message': 'Invoice not found'}), 404

    cursor.execute("""
    SELECT si.*, m.brand_name, m.generic_name, m.dosage_form, m.strength, b.batch_number, b.expiry_date
    FROM sale_items si
    JOIN medicines m ON si.medicine_id = m.id
    JOIN batches b ON si.batch_id = b.id
    WHERE si.sale_id = ?;
    """, (sale_id,))
    items = rows_to_list(cursor.fetchall())
    conn.close()

    res = dict(sale)
    res['items'] = items
    return jsonify({'success': True, 'receipt': res})

@app.route('/api/reports/export-csv', methods=['GET'])
@token_required
def export_csv():
    report_type = request.args.get('type', 'inventory') # 'inventory', 'sales', 'audit'
    conn = get_db()
    cursor = conn.cursor()

    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == 'inventory':
        writer.writerow(['SKU', 'Barcode', 'Brand Name', 'Generic Name', 'Category', 'Dosage Form', 'Strength', 'Total Stock', 'Unit Cost (ZMW)', 'Unit Price (ZMW)', 'Nearest Expiry'])
        cursor.execute("""
        SELECT m.sku, m.barcode, m.brand_name, m.generic_name, m.category, m.dosage_form, m.strength,
               COALESCE(SUM(b.current_quantity), 0) as total_stock, m.unit_cost, m.unit_price,
               MIN(CASE WHEN b.current_quantity > 0 THEN b.expiry_date ELSE NULL END) as nearest_expiry
        FROM medicines m
        LEFT JOIN batches b ON m.id = b.medicine_id AND b.status = 'active'
        GROUP BY m.id
        ORDER BY m.brand_name ASC;
        """)
        for row in cursor.fetchall():
            writer.writerow([row['sku'], row['barcode'], row['brand_name'], row['generic_name'], row['category'], row['dosage_form'], row['strength'], row['total_stock'], f"{row['unit_cost']:.2f}", f"{row['unit_price']:.2f}", row['nearest_expiry'] or 'N/A'])
        filename = f"pharmpulse_inventory_{date.today()}.csv"

    elif report_type == 'sales':
        writer.writerow(['Invoice #', 'Date Time', 'Patient', 'Cashier', 'Payment Method', 'Subtotal (ZMW)', 'Discount (ZMW)', 'Tax (ZMW)', 'Total (ZMW)', 'Status'])
        cursor.execute("""
        SELECT s.invoice_number, s.created_at, COALESCE(p.full_name, 'Walk-in Guest') as patient, u.full_name as cashier,
               s.payment_method, s.subtotal, s.discount_amount, s.tax_amount, s.total_amount, s.status
        FROM sales s
        LEFT JOIN patients p ON s.patient_id = p.id
        JOIN users u ON s.user_id = u.id
        ORDER BY s.created_at DESC;
        """)
        for row in cursor.fetchall():
            writer.writerow([row['invoice_number'], row['created_at'], row['patient'], row['cashier'], row['payment_method'], f"{row['subtotal']:.2f}", f"{row['discount_amount']:.2f}", f"{row['tax_amount']:.2f}", f"{row['total_amount']:.2f}", row['status']])
        filename = f"pharmpulse_sales_{date.today()}.csv"

    else: # audit
        writer.writerow(['Timestamp', 'User', 'Action', 'Entity', 'Entity ID', 'Details', 'IP Address'])
        cursor.execute("""
        SELECT al.created_at, COALESCE(u.full_name, 'System') as user, al.action, al.entity, al.entity_id, al.details, al.ip_address
        FROM audit_logs al
        LEFT JOIN users u ON al.user_id = u.id
        ORDER BY al.created_at DESC;
        """)
        for row in cursor.fetchall():
            writer.writerow([row['created_at'], row['user'], row['action'], row['entity'], row['entity_id'], row['details'], row['ip_address']])
        filename = f"pharmpulse_audit_{date.today()}.csv"

    conn.close()
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

if __name__ == '__main__':
    # Initialize DB schema if not already present
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print(f"PharmPulse Pro Commercial Pharmacy Server running on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
