import sqlite3
import hashlib
from datetime import datetime

DB_PATH = "diller.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Foydalanuvchilar
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            telegram_id INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # Dokonlar
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            phone TEXT,
            address TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # Tovarlar
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            price REAL NOT NULL DEFAULT 0,
            quantity INTEGER NOT NULL DEFAULT 0,
            unit TEXT DEFAULT 'dona',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # Buyurtmalar
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            discount_type TEXT DEFAULT 'none',
            discount_value REAL DEFAULT 0,
            total REAL NOT NULL,
            paid REAL DEFAULT 0,
            debt REAL DEFAULT 0,
            note TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (shop_id) REFERENCES shops(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # To'lovlar
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            note TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (shop_id) REFERENCES shops(id)
        )
    """)

    conn.commit()
    conn.close()


# ─── USERS ────────────────────────────────────────────────────────────────────

def register_user(email, password, name):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (email, password, name) VALUES (?,?,?)",
            (email.lower().strip(), hash_password(password), name.strip())
        )
        conn.commit()
        return True, "OK"
    except sqlite3.IntegrityError:
        return False, "Bu email allaqachon ro'yxatdan o'tgan!"
    finally:
        conn.close()


def login_user(email, password):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (email.lower().strip(), hash_password(password))
    ).fetchone()
    conn.close()
    return row


def update_telegram_id(user_id, telegram_id):
    conn = get_conn()
    conn.execute("UPDATE users SET telegram_id=? WHERE id=?", (telegram_id, user_id))
    conn.commit()
    conn.close()


def get_user_by_id(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return row


# ─── SHOPS ────────────────────────────────────────────────────────────────────

def add_shop(name, phone="", address=""):
    conn = get_conn()
    try:
        conn.execute("INSERT INTO shops (name, phone, address) VALUES (?,?,?)", (name, phone, address))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_shops():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM shops ORDER BY name").fetchall()
    conn.close()
    return rows


def get_shop(shop_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM shops WHERE id=?", (shop_id,)).fetchone()
    conn.close()
    return row


def delete_shop(shop_id):
    conn = get_conn()
    conn.execute("DELETE FROM shops WHERE id=?", (shop_id,))
    conn.commit()
    conn.close()


# ─── PRODUCTS ─────────────────────────────────────────────────────────────────

def add_product(name, price, quantity, unit="dona"):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO products (name, price, quantity, unit) VALUES (?,?,?,?)",
            (name, price, quantity, unit)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_products():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM products ORDER BY name").fetchall()
    conn.close()
    return rows


def get_product(product_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    conn.close()
    return row


def update_product_quantity(product_id, delta):
    conn = get_conn()
    conn.execute("UPDATE products SET quantity = quantity + ? WHERE id=?", (delta, product_id))
    conn.commit()
    conn.close()


def update_product_price(product_id, new_price):
    conn = get_conn()
    conn.execute("UPDATE products SET price=? WHERE id=?", (new_price, product_id))
    conn.commit()
    conn.close()


def delete_product(product_id):
    conn = get_conn()
    conn.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()


# ─── ORDERS ───────────────────────────────────────────────────────────────────

def add_order(shop_id, product_id, quantity, price, discount_type="none", discount_value=0, paid=0, note="", created_by=None):
    original_total = quantity * price
    if discount_type == "percent":
        discount_amount = original_total * discount_value / 100
    elif discount_type == "sum":
        discount_amount = discount_value
    else:
        discount_amount = 0

    total = max(0, original_total - discount_amount)
    debt = max(0, total - paid)

    conn = get_conn()
    conn.execute(
        """INSERT INTO orders 
        (shop_id, product_id, quantity, price, discount_type, discount_value, total, paid, debt, note, created_by) 
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (shop_id, product_id, quantity, price, discount_type, discount_value, total, paid, debt, note, created_by)
    )
    conn.commit()
    conn.close()
    update_product_quantity(product_id, -quantity)


def get_orders(shop_id=None):
    conn = get_conn()
    if shop_id:
        rows = conn.execute("""
            SELECT o.*, s.name as shop_name, p.name as product_name, p.unit
            FROM orders o
            JOIN shops s ON o.shop_id = s.id
            JOIN products p ON o.product_id = p.id
            WHERE o.shop_id=?
            ORDER BY o.created_at DESC
        """, (shop_id,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT o.*, s.name as shop_name, p.name as product_name, p.unit
            FROM orders o
            JOIN shops s ON o.shop_id = s.id
            JOIN products p ON o.product_id = p.id
            ORDER BY o.created_at DESC
        """).fetchall()
    conn.close()
    return rows


# ─── DEBTORS ──────────────────────────────────────────────────────────────────

def get_debtors():
    conn = get_conn()
    rows = conn.execute("""
        SELECT s.id, s.name, s.phone,
               COALESCE(SUM(o.debt), 0) as total_debt
        FROM shops s
        JOIN orders o ON s.id = o.shop_id
        WHERE o.debt > 0
        GROUP BY s.id, s.name, s.phone
        HAVING total_debt > 0
        ORDER BY total_debt DESC
    """).fetchall()
    conn.close()
    return rows


def get_shop_debt_detail(shop_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT o.id, o.created_at, p.name as product_name, p.unit,
               o.quantity, o.price, o.discount_type, o.discount_value,
               o.total, o.paid, o.debt, o.note
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.shop_id=? AND o.debt > 0
        ORDER BY o.created_at DESC
    """, (shop_id,)).fetchall()
    conn.close()
    return rows


def get_shop_total_debt(shop_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT COALESCE(SUM(debt),0) as total FROM orders WHERE shop_id=? AND debt>0",
        (shop_id,)
    ).fetchone()
    conn.close()
    return row["total"] if row else 0


def add_payment(shop_id, amount, note=""):
    conn = get_conn()
    remaining = amount
    orders = conn.execute(
        "SELECT id, debt FROM orders WHERE shop_id=? AND debt>0 ORDER BY created_at ASC",
        (shop_id,)
    ).fetchall()
    for order in orders:
        if remaining <= 0:
            break
        if remaining >= order["debt"]:
            remaining -= order["debt"]
            conn.execute("UPDATE orders SET paid=paid+debt, debt=0 WHERE id=?", (order["id"],))
        else:
            conn.execute(
                "UPDATE orders SET paid=paid+?, debt=debt-? WHERE id=?",
                (remaining, remaining, order["id"])
            )
            remaining = 0

    conn.execute("INSERT INTO payments (shop_id, amount, note) VALUES (?,?,?)", (shop_id, amount, note))
    conn.commit()
    conn.close()


def get_payments(shop_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM payments WHERE shop_id=? ORDER BY created_at DESC",
        (shop_id,)
    ).fetchall()
    conn.close()
    return rows


# ─── HISTORY ──────────────────────────────────────────────────────────────────

def get_daily_history(date_str=None):
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    conn = get_conn()
    rows = conn.execute("""
        SELECT o.created_at, s.name as shop_name, p.name as product_name, p.unit,
               o.quantity, o.price, o.discount_type, o.discount_value,
               o.total, o.paid, o.debt, o.note
        FROM orders o
        JOIN shops s ON o.shop_id = s.id
        JOIN products p ON o.product_id = p.id
        WHERE DATE(o.created_at) = ?
        ORDER BY o.created_at DESC
    """, (date_str,)).fetchall()
    conn.close()
    return rows


def get_history_summary(date_str=None):
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    conn = get_conn()
    row = conn.execute("""
        SELECT COUNT(*) as order_count,
               COALESCE(SUM(o.total),0) as total_sum,
               COALESCE(SUM(o.paid),0) as paid_sum,
               COALESCE(SUM(o.debt),0) as debt_sum,
               COALESCE(SUM(o.quantity),0) as total_qty
        FROM orders o
        WHERE DATE(o.created_at) = ?
    """, (date_str,)).fetchone()
    conn.close()
    return row


def get_available_dates():
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT DATE(created_at) as d FROM orders ORDER BY d DESC LIMIT 30"
    ).fetchall()
    conn.close()
    return [r["d"] for r in rows]
