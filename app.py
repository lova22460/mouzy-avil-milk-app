from flask import Flask, render_template_string, request, redirect, session, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo
import sqlite3 #import
import os
import psycopg2
import json
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
try:
    from pywebpush import webpush
except Exception:
    webpush = None
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL")
KITCHEN_PIN = "2246"
DB_NAME = "mouzy.db" #DB functions


def get_db():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()

    if DATABASE_URL:
        # PostgreSQL
        conn.cursor().execute("""
            CREATE TABLE IF NOT EXISTS stock (
                ingredient TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                qty TEXT DEFAULT ''
            )
        """)

        conn.cursor().execute("""
            CREATE TABLE IF NOT EXISTS stock_history (
                id SERIAL PRIMARY KEY,
                item TEXT NOT NULL,
                status TEXT NOT NULL,
                qty TEXT DEFAULT '',
                time TEXT NOT NULL
            )
        """)

        for ingredient, data in stock.items():
            conn.cursor().execute("""
                INSERT INTO stock
                (ingredient, status, qty)
                VALUES (%s, %s, %s)
                ON CONFLICT (ingredient) DO NOTHING
            """, (
                ingredient,
                data["status"],
                data.get("qty", "")
            ))

    else:
        # SQLite — local VS Code
        conn.cursor().execute("""
            CREATE TABLE IF NOT EXISTS stock (
                ingredient TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                qty TEXT DEFAULT ''
            )
        """)

        conn.cursor().execute("""
            CREATE TABLE IF NOT EXISTS stock_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT NOT NULL,
                status TEXT NOT NULL,
                qty TEXT DEFAULT '',
                time TEXT NOT NULL
            )
        """)

        for ingredient, data in stock.items():
            conn.cursor().execute("""
                INSERT OR IGNORE INTO stock
                (ingredient, status, qty)
                VALUES (?, ?, ?)
            """, (
                ingredient,
                data["status"],
                data.get("qty", "")
            ))

    # Persistent storage for PWA push subscriptions and the VAPID key pair.
    conn.cursor().execute("""
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            endpoint TEXT PRIMARY KEY,
            subscription TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.cursor().execute("""
        CREATE TABLE IF NOT EXISTS vapid_config (
            id INTEGER PRIMARY KEY,
            private_key TEXT NOT NULL,
            public_key TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

app = Flask(__name__)

# PWA files are served from the site root so Chrome can use the
# service worker for the whole app (not only /static/).
@app.route("/manifest.json")
def pwa_manifest():
    return app.send_static_file("manifest.json")

@app.route("/sw.js")
def pwa_service_worker():
    return app.send_static_file("sw.js")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

def _b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def get_vapid_keys():
    conn=get_db(); cur=conn.cursor()
    try:
        cur.execute("SELECT private_key, public_key FROM vapid_config WHERE id = " + ("%s" if DATABASE_URL else "?"), (1,))
        row=cur.fetchone()
        if row:
            return (row["private_key"], row["public_key"]) if isinstance(row, dict) else (row[0], row[1])
        key=ec.generate_private_key(ec.SECP256R1())
        private_key=_b64url(key.private_numbers().private_value.to_bytes(32,"big"))
        public_key=_b64url(key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint))
        if DATABASE_URL:
            cur.execute("INSERT INTO vapid_config (id, private_key, public_key) VALUES (%s,%s,%s)",(1,private_key,public_key))
        else:
            cur.execute("INSERT INTO vapid_config (id, private_key, public_key) VALUES (?,?,?)",(1,private_key,public_key))
        conn.commit()
        return private_key,public_key
    finally:
        cur.close(); conn.close()

def send_push_notification(title, body, tag="mouzy"):
    if webpush is None: return
    private_key,_=get_vapid_keys()
    conn=get_db(); cur=conn.cursor()
    try:
        cur.execute("SELECT endpoint, subscription FROM push_subscriptions")
        rows=cur.fetchall(); dead=[]
        for row in rows:
            endpoint=row["endpoint"] if isinstance(row,dict) else row[0]
            subscription=row["subscription"] if isinstance(row,dict) else row[1]
            try:
                webpush(subscription_info=json.loads(subscription), data=json.dumps({"title":title,"body":body,"tag":tag}), vapid_private_key=private_key, vapid_claims={"sub":"mailto:mouzy-notifications@localhost"})
            except Exception as exc:
                status=getattr(getattr(exc,"response",None),"status_code",None)
                if status in (404,410): dead.append(endpoint)
        for endpoint in dead:
            cur.execute("DELETE FROM push_subscriptions WHERE endpoint = " + ("%s" if DATABASE_URL else "?"), (endpoint,))
        conn.commit()
    finally:
        cur.close(); conn.close()

@app.route("/push/public-key")
def push_public_key():
    _,public_key=get_vapid_keys()
    return jsonify({"publicKey":public_key})

@app.route("/push/subscribe", methods=["POST"])
def push_subscribe():
    sub=request.get_json(silent=True) or {}
    endpoint=sub.get("endpoint")
    if not endpoint or not isinstance(sub.get("keys"),dict):
        return jsonify({"ok":False}),400
    conn=get_db(); cur=conn.cursor()
    try:
        now=datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d-%m-%Y %I:%M:%S %p")
        payload=json.dumps(sub,separators=(",",":"))
        if DATABASE_URL:
            cur.execute("INSERT INTO push_subscriptions(endpoint,subscription,created_at) VALUES(%s,%s,%s) ON CONFLICT(endpoint) DO UPDATE SET subscription=EXCLUDED.subscription, created_at=EXCLUDED.created_at",(endpoint,payload,now))
        else:
            cur.execute("INSERT INTO push_subscriptions(endpoint,subscription,created_at) VALUES(?,?,?) ON CONFLICT(endpoint) DO UPDATE SET subscription=excluded.subscription, created_at=excluded.created_at",(endpoint,payload,now))
        conn.commit()
    finally:
        cur.close(); conn.close()
    return jsonify({"ok":True})

# =========================
# STOCK
# =========================
# The database is seeded from the final ingredient master below.
stock = {}

# =========================
# MAIN INGREDIENTS
# =========================

INGREDIENT_CATEGORIES = {
    "SINGLE INGREDIENTS": [
        "Fruit Mix", "Boost", "Dates", "Blueberry Dry", "Dry Fruits",
        "Chocolate", "Cashew / Nuts", "Badam", "Chocos", "Chocolate Wafer", "Umbrella", "Spanish chips",
        "Chocolate Chips", "White Chips", "Cherry",
    ],

    "MILK / DAIRY": [
        "Fresh Cream", "Shake Milk", "Diet Milk", "Lassi",
    ],

    "ICE CREAM": [
        "Vanilla Ice Cream", "Chocolate Ice Cream", "Mango Ice Cream",
        "Strawberry Ice Cream", "Pista Ice Cream", "Butterscotch Ice Cream",
        "Spanish Ice Cream", "Dates Ice Cream", "Tender Ice Cream",
        "Blueberry Ice Cream",
    ],

    "FRESH FRUITS": [
        "Tender Cut Piece",
        "Pineapple", "Orange", "Mango", "Strawberry", "Blueberry",
        "Kiwi", "Lemon", "Papaya", "Muskmelon", "Mosambi", "Seetaphal",
        "Watermelon", "Robest banana", "Big banana",
    ],

    "PULP": [
        "Tender Pulp", "Mango Pulp", "Dates Pulp", "Passion Pulp",
        "Pineapple Pulp", "Chiku Pulp", "Fig Pulp", "Strawberry Pulp",
        "Grapes Pulp",
    ],

    "LIME": [
        "Mint", "Ginger",
    ],

    "MOJITO": [
        "Sprite",
    ],

    "FALOODA": [
        "Falooda", "Kaskas", "Semia",
    ],

    "CHOCOLATE SHAKE ITEMS": [
        "Coffee", "Oreo", "Kitkat", "Choco Pie", "Chocolate Wafer", "Brownie",
    ],

    "CHEESEY CHIKEN": [
        "Bread", "Samoona", "Chicken", "Mayonnaisse", "White Mayonnaise",
        "Slices", "Mozzarella Cheese", "Butter", "Green Sauce", "BBQ Sauce",
        "Mexican Sauce", "Schezwan Sauce", "Spring Onion", "Red Capsicum",
        "Black Olives", "Black Seeds", "White Seeds", "Dried Oregano",
        "Chilli Flakes",
    ],

    "SYRUPS": [
        "Passion Syrup", "Rose syrup", "Strawberry Syrup", "Mango Syrup",
        "Pista Syrup", "Chocolate Syrup", "Butterscotch Syrup",
        "Blueberry Syrup", "Honey", "Rooh Afza Syrup", "Watermelon Syrup",
        "Kiwi Syrup", "Date Syrup", "Tender Syrup", "Spanish Syrup",
    ],
}

MAIN_INGREDIENTS = []
for _names in INGREDIENT_CATEGORIES.values():
    for _name in _names:
        if _name not in MAIN_INGREDIENTS:
            MAIN_INGREDIENTS.append(_name)


# =========================
# MENU DEPENDENCIES
# =========================

menu = {
    "REGULAR AVIL MILK": {
        "Mini": [],
        "Normal": [],
        "Normal Boost": ["Boost"],
        "Fruit": ["Fruit Mix"],
        "Mango Passion": ["Mango", "Passion Syrup"],
        "White": ["Vanilla Ice Cream", "White Chips"],
        "Special": ["Fruit Mix", "Vanilla Ice Cream"],
        "SP Boost": ["Boost", "Vanilla Ice Cream"],
    },

    "LITTLE COMBO AVIL MILK": {
        "Little Strawberry": ["Strawberry Ice Cream", "Strawberry", "Strawberry Syrup", "Umbrella"],
        "Little Pista": ["Pista Ice Cream", "Pista Syrup", "Umbrella"],
        "Little Mango": ["Mango Ice Cream", "Mango", "Mango Syrup", "Umbrella"],
        "Little Arabian": ["Dates Ice Cream", "Dates", "Date Syrup", "Umbrella"],
        "Little Butterscotch": ["Butterscotch Ice Cream", "Butterscotch Syrup", "Umbrella"],
        "Little Choco": ["Chocolate Ice Cream", "Chocos", "Chocolate Syrup", "Chocolate Wafer", "Umbrella"],
    },

    "FUSION AVIL MILK": {
        "Watermelon": ["Vanilla Ice Cream", "Watermelon", "Watermelon Syrup"],
        "Rooh Afza": ["Vanilla Ice Cream", "Watermelon", "Rooh Afza Syrup"],
        "Butterscotch": ["Butterscotch Ice Cream", "Butterscotch Syrup"],
        "Pista": ["Pista Ice Cream", "Pista Syrup"],
        "Kiwi": ["Vanilla Ice Cream", "Kiwi", "Kiwi Syrup"],
        "Chocolate": ["Chocolate Ice Cream", "Chocolate Chips", "Chocolate Syrup"],
        "Strawberry": ["Strawberry Ice Cream", "Strawberry", "Strawberry Syrup"],
        "Mango": ["Mango Ice Cream", "Mango", "Mango Syrup"],
        "Dates": ["Dates Ice Cream", "Dates", "Date Syrup"],
    },

    "SUPREME AVIL MILK": {
        "Nuts": ["Butterscotch Ice Cream", "Cashew / Nuts", "Badam", "Chocolate Syrup"],
        "Fruit Nut": ["Fruit Mix", "Vanilla Ice Cream", "Cashew / Nuts", "Badam", "Mango Syrup"],
        "Royal": ["Fruit Mix", "Mango Ice Cream", "Cashew / Nuts", "Badam", "Mango Syrup", "Rose syrup"],
        "Redberry Nut": ["Fruit Mix", "Vanilla Ice Cream", "Strawberry Ice Cream", "Cashew / Nuts", "Badam", "Strawberry", "Mango Syrup"],
        "Malgoa Nut": ["Mango Ice Cream", "Mango", "Cashew / Nuts", "Badam", "Mango Syrup"],
        "Pista Nut": ["Fruit Mix", "Vanilla Ice Cream", "Pista Ice Cream", "Cashew / Nuts", "Badam", "Mango Syrup"],
        "Choco Nut": ["Chocolate Ice Cream", "Chocos", "Cashew / Nuts", "Badam", "Chocolate Syrup"],
        "Rio Nut": ["Fruit Mix", "Pista Ice Cream", "Mango Ice Cream", "Cashew / Nuts", "Badam", "Mango Syrup"],
        "Spanish Nut": ["Spanish Ice Cream", "Cashew / Nuts", "Badam", "Spanish chips", "Spanish Syrup"],
        "Tender Coconut": ["Tender Ice Cream", "Tender Cut Piece", "Cashew / Nuts", "Badam", "Tender Syrup", "Honey"],
        "Blueberry Nut": ["Blueberry Ice Cream", "Cashew / Nuts", "Badam", "Blueberry Dry", "Blueberry Syrup"],
        "Arabian Nut": ["Dates Ice Cream", "Dates", "Cashew / Nuts", "Badam", "Date Syrup"],
        "Dry Fruits": ["Mango Ice Cream", "Dry Fruits", "Cashew / Nuts", "Badam"],
        "Special Nut": ["Spanish Ice Cream", "Cashew / Nuts", "Badam"],
    },

    "DIET AVIL MILK": {
        "Normal Diet": ["Diet Milk"],
        "Fruit Diet": ["Diet Milk", "Fruit Mix"],
        "Fruit Nut Diet": ["Diet Milk", "Fruit Mix", "Cashew / Nuts", "Badam"],
        "Nuts Diet": ["Diet Milk", "Cashew / Nuts", "Badam"],
        "Dry Fruits Diet": ["Diet Milk", "Cashew / Nuts", "Dry Fruits", "Badam"],
    },

    "CHEESEY CHIKEN": {
        "Chicken Club Sandwich": ["Bread", "Chicken", "Mayonnaisse", "Slices", "Butter"],
        "Chicken Mini Sandwich": ["Bread", "Chicken", "Mayonnaisse", "Slices", "Butter"],
        "Samoona": ["Samoona", "Chicken", "Mayonnaisse", "Slices", "Butter"],
        "Cheesy Chick Bake - Classic Medium": ["Bread", "Green Sauce", "Chicken", "Mozzarella Cheese", "White Mayonnaise", "Spring Onion", "Red Capsicum"],
        "Cheesy Chick Bake - Classic Large": ["Bread", "Green Sauce", "Chicken", "Mozzarella Cheese", "White Mayonnaise", "Spring Onion", "Red Capsicum"],
        "Cheesy Chick Bake - Schezwan Medium": ["Bread", "Schezwan Sauce", "Chicken", "Mozzarella Cheese", "Spring Onion", "Red Capsicum", "Chilli Flakes"],
        "Cheesy Chick Bake - Schezwan Large": ["Bread", "Schezwan Sauce", "Chicken", "Mozzarella Cheese", "Spring Onion", "Red Capsicum", "Chilli Flakes"],
        "Cheesy Chick Bake - BBQ Medium": ["Bread", "BBQ Sauce", "Chicken", "Mozzarella Cheese", "Spring Onion", "Black Seeds", "Black Olives"],
        "Cheesy Chick Bake - BBQ Large": ["Bread", "BBQ Sauce", "Chicken", "Mozzarella Cheese", "Spring Onion", "Black Seeds", "Black Olives"],
        "Cheesy Chick Bake - Mexican Medium": ["Bread", "Mexican Sauce", "Chicken", "Mozzarella Cheese", "Spring Onion", "White Seeds", "Dried Oregano"],
        "Cheesy Chick Bake - Mexican Large": ["Bread", "Mexican Sauce", "Chicken", "Mozzarella Cheese", "Spring Onion", "White Seeds", "Dried Oregano"],
    },

    "LIME": {
        "Fresh Lime": ["Lemon"],
        "Mexican Mint Lime": ["Lemon", "Mint", "Pineapple"],
        "Mint Lime": ["Lemon", "Mint"],
        "Pineapple Lime": ["Lemon", "Pineapple"],
        "Orange Lime": ["Lemon", "Orange"],
        "Ginger Lime": ["Lemon", "Ginger"],
    },

    "MOJITO": {
        "Classic Mojito": ["Lemon", "Mint", "Sprite"],
        "Mango Mojito": ["Lemon", "Mint", "Sprite", "Mango Pulp"],
        "Grapes Mojito": ["Lemon", "Mint", "Sprite", "Grapes Pulp"],
        "Passion Mojito": ["Lemon", "Mint", "Sprite", "Passion Pulp"],
        "Pineapple Mojito": ["Lemon", "Mint", "Sprite", "Pineapple Pulp"],
        "Strawberry Mojito": ["Lemon", "Mint", "Sprite", "Strawberry Pulp"],
    },

    "FRUIT SHAKE": {
        "Banago": ["Shake Milk", "Robest banana", "Mango Pulp"],
        "Mangopass": ["Shake Milk", "Robest banana", "Mango Pulp", "Passion Pulp"],
        "Chikudates": ["Shake Milk", "Robest banana", "Chiku Pulp", "Dates Pulp"],
        "Banatend": ["Shake Milk", "Tender Pulp", "Robest banana"],
        "Tendates": ["Shake Milk", "Tender Pulp", "Robest banana", "Dates Pulp"],
        "Datifig": ["Shake Milk", "Robest banana", "Dates Pulp", "Fig Pulp"],
    },

    "FRESH JUICE": {
        "Orange": ["Orange"],
        "Watermelon": ["Watermelon"],
        "Pineapple": ["Pineapple"],
        "Pappaya": ["Papaya"],
        "Muskmelon": ["Muskmelon"],
        "Mosambi": ["Mosambi"],
    },

    "FALOODA": {
        "Royal Banaloooda": ["Falooda", "Pista Ice Cream", "Vanilla Ice Cream", "Strawberry Ice Cream", "Kaskas", "Semia", "Big banana", "Fruit Mix", "Cashew / Nuts", "Badam", "Rose syrup", "Mango Ice Cream", "Cherry"],
        "Strawberry Banaloooda": ["Falooda", "Strawberry Syrup", "Strawberry Ice Cream", "Vanilla Ice Cream", "Kaskas", "Semia", "Big banana", "Cashew / Nuts", "Badam", "Strawberry", "Cherry"],
        "Chocolate Banaloooda": ["Falooda", "Chocolate Syrup", "Chocolate Ice Cream", "Vanilla Ice Cream", "Kaskas", "Semia", "Big banana", "Cashew / Nuts", "Badam", "Chocolate Chips", "Cherry"],
        "Mango Banaloooda": ["Falooda", "Mango Syrup", "Mango Ice Cream", "Vanilla Ice Cream", "Kaskas", "Semia", "Big banana", "Cashew / Nuts", "Badam", "Mango", "Cherry"],
        "Pista Banaloooda": ["Falooda", "Pista Syrup", "Pista Ice Cream", "Vanilla Ice Cream", "Kaskas", "Semia", "Big banana", "Cashew / Nuts", "Badam", "Cherry"],
        "Dry Fruit Banaloooda": ["Falooda", "Butterscotch Syrup", "Butterscotch Ice Cream", "Vanilla Ice Cream", "Kaskas", "Semia", "Big banana", "Cashew / Nuts", "Badam", "Mango Ice Cream", "Dry Fruits", "Cherry"],
    },

    "CHOCOLATE SHAKE": {
        "Mississippi Mud": ["Shake Milk", "Chocolate Syrup", "Brownie", "Chocolate Ice Cream", "Vanilla Ice Cream"],
        "Oreo Wonder": ["Shake Milk", "Chocolate Syrup", "Oreo", "Chocolate Ice Cream", "Vanilla Ice Cream"],
        "Pie Melt": ["Shake Milk", "Chocolate Syrup", "Choco Pie", "Chocolate Ice Cream", "Vanilla Ice Cream"],
        "Kitkat Smash": ["Shake Milk", "Chocolate Syrup", "Kitkat", "Chocolate Ice Cream", "Vanilla Ice Cream"],
        "Boost Blast": ["Shake Milk", "Chocolate Syrup", "Boost", "Chocolate Ice Cream", "Vanilla Ice Cream"],
        "Choco Coffee Charge": ["Shake Milk", "Chocolate Syrup", "Coffee", "Chocolate Ice Cream", "Vanilla Ice Cream"],
    },

    "DOODH MALAI": {
        "Mix Fruit Malai": ["Fresh Cream", "Fruit Mix", "Cashew / Nuts"],
        "Mango Magic Malai": ["Fresh Cream", "Mango", "Cashew / Nuts"],
        "Chocolate Malai": ["Fresh Cream", "Kitkat", "Cashew / Nuts"],
        "Seetaphal Malai": ["Fresh Cream", "Seetaphal", "Cashew / Nuts"],
        "Kiwi Malai": ["Fresh Cream", "Kiwi", "Cashew / Nuts"],
    },

    "LASSI": {
        "Plain Lassi": ["Lassi"],
        "Mango Lassi": ["Lassi", "Mango"],
        "Chocolate Lassi": ["Lassi", "Chocolate"],
        "Mix Fruit Lassi": ["Lassi", "Fruit Mix"],
        "Dry Nuts Lassi": ["Lassi", "Cashew / Nuts", "Badam"],
        "Dry Fruit Lassi": ["Lassi", "Dry Fruits"],
    },
}


# =========================
# MENU CONTROLS (PHASE 2)
# =========================

def init_menu_controls():
    """Create persistent ON/OFF controls for categories and individual items."""
    conn = get_db()
    cur = conn.cursor()

    if DATABASE_URL:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS category_controls (
                category TEXT PRIMARY KEY,
                enabled BOOLEAN NOT NULL DEFAULT TRUE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS item_controls (
                category TEXT NOT NULL,
                item TEXT NOT NULL,
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                manual_status TEXT NOT NULL DEFAULT 'AUTO',
                qty INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (category, item)
            )
        """)

        # Migration: older Phase 2 databases may already have item_controls
        # without the manual_status column. Add it before any INSERT uses it.
        cur.execute("SELECT 1 FROM information_schema.columns WHERE table_name = 'item_controls' AND column_name = 'manual_status'")
        if cur.fetchone() is None:
            cur.execute("ALTER TABLE item_controls ADD COLUMN manual_status TEXT NOT NULL DEFAULT 'AUTO'")
        cur.execute("SELECT 1 FROM information_schema.columns WHERE table_name = 'item_controls' AND column_name = 'qty'")
        if cur.fetchone() is None:
            cur.execute("ALTER TABLE item_controls ADD COLUMN qty INTEGER NOT NULL DEFAULT 1")

        for category, items in menu.items():
            cur.execute("""
                INSERT INTO category_controls (category, enabled)
                VALUES (%s, TRUE)
                ON CONFLICT (category) DO NOTHING
            """, (category,))
            for item in items:
                cur.execute("""
                    INSERT INTO item_controls (category, item, enabled, manual_status, qty)
                    VALUES (%s, %s, TRUE, 'AUTO', 1)
                    ON CONFLICT (category, item) DO NOTHING
                """, (category, item))
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS category_controls (
                category TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 1
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS item_controls (
                category TEXT NOT NULL,
                item TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                manual_status TEXT NOT NULL DEFAULT 'AUTO',
                qty INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (category, item)
            )
        """)

        # Migration: older local databases may already have item_controls
        # without the manual_status column. Add it before any INSERT uses it.
        cur.execute("PRAGMA table_info(item_controls)")
        cols = [r[1] for r in cur.fetchall()]
        if "manual_status" not in cols:
            cur.execute("ALTER TABLE item_controls ADD COLUMN manual_status TEXT NOT NULL DEFAULT 'AUTO'")
        if "qty" not in cols:
            cur.execute("ALTER TABLE item_controls ADD COLUMN qty INTEGER NOT NULL DEFAULT 1")

        for category, items in menu.items():
            cur.execute("""
                INSERT OR IGNORE INTO category_controls (category, enabled)
                VALUES (?, 1)
            """, (category,))
            for item in items:
                cur.execute("""
                    INSERT OR IGNORE INTO item_controls (category, item, enabled, manual_status, qty)
                    VALUES (?, ?, 1, 'AUTO', 1)
                """, (category, item))

    conn.commit()
    cur.close()
    conn.close()


def load_menu_controls():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT category, enabled FROM category_controls")
    category_rows = cur.fetchall()
    cur.execute("SELECT category, item, enabled, manual_status, qty FROM item_controls")
    item_rows = cur.fetchall()
    cur.close()
    conn.close()

    categories = {row["category"]: bool(row["enabled"]) for row in category_rows}
    items = {(row["category"], row["item"]): {"enabled": bool(row["enabled"]), "manual_status": row["manual_status"], "qty": int(row["qty"] or 1)} for row in item_rows}
    return categories, items




def load_stock_from_db():
    """Load the latest ingredient statuses/quantities from the database."""
    global stock
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT ingredient, status, qty FROM stock")
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    loaded = {}
    for row in rows:
        if isinstance(row, dict):
            ingredient = row["ingredient"]
            status = row["status"]
            qty = row.get("qty", "")
        else:
            ingredient = row[0]
            status = row[1]
            qty = row[2]
        loaded[ingredient] = {"status": status, "qty": qty}

    # Keep every final master/dependency ingredient available to the UI.
    for ingredient in MAIN_INGREDIENTS:
        if ingredient not in loaded:
            loaded[ingredient] = {"status": "AVAILABLE", "qty": ""}

    stock = loaded


# Final master seed/load. This runs only after INGREDIENT_CATEGORIES and menu
# are fully defined, so every dependency has a persistent DB row.
for _category_items in menu.values():
    for _deps in _category_items.values():
        for _dep in _deps:
            if _dep not in MAIN_INGREDIENTS:
                MAIN_INGREDIENTS.append(_dep)

for _dep in MAIN_INGREDIENTS:
    if _dep not in stock:
        stock[_dep] = {"status": "AVAILABLE", "qty": ""}

init_db()
load_stock_from_db()



def effective_item_status(category, item, dependencies, category_enabled=None, item_control=None):
    """Calculate menu status without repeatedly opening the database."""
    if category_enabled is None or item_control is None:
        category_controls, item_controls = load_menu_controls()
        category_enabled = category_controls.get(category, True)
        item_control = item_controls.get((category, item), {"enabled": True, "manual_status": "AUTO", "qty": 1})

    if not category_enabled:
        return "CLOSED"

    if isinstance(item_control, bool):
        item_control = {"enabled": item_control, "manual_status": "AUTO", "qty": 1}

    if not item_control.get("enabled", True):
        return "CLOSED"

    if item_control.get("manual_status") == "LIMITED":
        if int(item_control.get("qty", 1) or 0) <= 0:
            return "CLOSED"
        for ingredient in dependencies:
            if stock.get(ingredient, {"status": "AVAILABLE"})["status"] == "OUT":
                return "CLOSED"
        return "LIMITED"

    for ingredient in dependencies:
        if stock.get(ingredient, {"status": "AVAILABLE"})["status"] == "OUT":
            return "CLOSED"

    for ingredient in dependencies:
        if stock.get(ingredient, {"status": "AVAILABLE"})["status"] == "LIMITED":
            return "LIMITED"

    return "AVAILABLE"


# =========================
# MENU ALERTS (MANUAL CATEGORY / ITEM CONTROLS)
# =========================

def menu_alerts():
    """Return grouped manual category/item OUT and LIMITED alerts.

    Dependency-driven OUT/LIMITED states are shown through ingredient alerts;
    these alerts are only for manual menu controls.
    """
    category_controls, item_controls = load_menu_controls()
    out_alerts = []
    limited_alerts = []

    for category, items in menu.items():
        if not category_controls.get(category, True):
            out_alerts.append({"category": category, "item": None, "items": []})
            continue

        out_names = []
        limited_items = []
        for item in items:
            control = item_controls.get(
                (category, item),
                {"enabled": True, "manual_status": "AUTO", "qty": 1}
            )
            if not control.get("enabled", True):
                out_names.append(item)
            elif control.get("manual_status") == "LIMITED" and int(control.get("qty", 1) or 0) > 0:
                limited_items.append({"item": item, "qty": int(control.get("qty", 1) or 1)})

        if out_names:
            out_alerts.append({"category": category, "item": out_names[0], "items": out_names})
        if limited_items:
            limited_alerts.append({"category": category, "items": limited_items})

    return out_alerts, limited_alerts


# =========================
# MENU STATUS
# =========================

def item_status(dependencies, category=None, item=None, category_enabled=None, item_control=None):
    if category is not None and item is not None:
        return effective_item_status(category, item, dependencies, category_enabled, item_control)

    for ingredient in dependencies:
        if stock.get(ingredient, {"status": "AVAILABLE"})["status"] == "OUT":
            return "CLOSED"
    for ingredient in dependencies:
        if stock.get(ingredient, {"status": "AVAILABLE"})["status"] == "LIMITED":
            return "LIMITED"
    return "AVAILABLE"


# =========================
# AFFECTED MENU
# =========================

def affected_menu(ingredient, category_controls=None, item_controls=None):
    if category_controls is None or item_controls is None:
        category_controls, item_controls = load_menu_controls()

    result = []
    for category, items in menu.items():
        for item, dependencies in items.items():
            if ingredient in dependencies:
                control = item_controls.get((category, item), {"enabled": True, "manual_status": "AUTO", "qty": 1})
                result.append({
                    "category": category,
                    "item": item,
                    "status": item_status(
                        dependencies, category, item,
                        category_controls.get(category, True), control
                    )
                })
    return result


def group_affected_menu(affected, wanted_status):
    """Group affected menu items by category for compact display."""
    grouped = []
    category_map = {}

    for item in affected:
        if item["status"] != wanted_status:
            continue
        category = item["category"]
        if category not in category_map:
            category_map[category] = []
            grouped.append({"category": category, "items": category_map[category]})
        category_map[category].append(item["item"])

    return grouped




# KITCHEN LOGIN 
# ==================================================

@app.route("/login", methods=["GET", "POST"]) #routes
def login():

    if request.method == "POST":

        pin = request.form.get("pin", "")

        if pin == KITCHEN_PIN:

            session["kitchen"] = True

            return redirect("/")

        return """
        <h2 style="text-align:center;color:red;">
        ❌ TUMSE NAA HOO PAYEGA!😒 ❌
        </h2>

        <p style="text-align:center;">
        <a href="/login">FIRSE DALIYENA</a>
        </p>
        """

    return """
    <!DOCTYPE html>

    <html>

    <head>

    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#ffffff">

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

    <title>Kitchen Login</title>

    </head>

    <body style="
        font-family:Arial;
        text-align:center;
        padding:40px;
    ">

    <h1>👨‍🍳 MOUZY EDAPPALLY KITCHEN</h1>

    <h3>🔐 Kitchen Head Login</h3>

    <form method="POST">

        <input
            type="password"
            name="pin"
            placeholder="Enter PIN"
            maxlength="4"
            inputmode="numeric"
            style="
                padding:12px;
                font-size:18px;
                width:150px;
            "
        >

        <br><br>

        <button
            type="submit"
            style="
                padding:12px 25px;
                font-size:16px;
            "
         onclick="event.stopPropagation()">
            🔓 ANDAR JANE K LIYE AAPKA DALIYEN NAA😁🤩
        </button>

    </form>

    <br>

    <a href="/staff">
        👀 Staff View OHH HELLO IDHAR DEKHO IDHAR
    </a>

    
<script>
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function () {
    navigator.serviceWorker.register('/sw.js').catch(function () {});
  });
}
</script>
</body>

    </html>
    """
# ==================================================
# KITCHEN LOGOUT
# ==================================================

@app.route("/logout")
def logout():

    session.pop("kitchen", None)

    return redirect("/login")

# =========================
# STOCK HISTORY
# =========================

@app.route("/clear-history", methods=["POST"])
def clear_history():

    if not session.get("kitchen"):
        return redirect("/login")

    conn = get_db()
    conn.cursor().execute("DELETE FROM stock_history")
    conn.commit()
    conn.close()

    return redirect("/history")

@app.route("/history")
def history():

    if not session.get("kitchen"):
        return redirect("/login")

    conn = get_db()

    cur = conn.cursor()
    cur.execute("""
        SELECT item, status, qty, time
        FROM stock_history
        ORDER BY id DESC
    """)
    rows = cur.fetchall()
    cur.close()

    conn.close()

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Stock History</title>

        
    </head>
    <meta http-equiv="refresh" content="1">
    </head>

    <body>

        <h2>📋 Stock History</h2>
        <form method="POST" action="/clear-history"
      onsubmit="return confirm('Clear all history?');"
      style="text-align:center; margin-bottom:20px;">

    <button type="submit" onclick="event.stopPropagation()">
        🗑️ Clear History
    </button>

</form>

        {% for row in history %}

        <div class="history">
            <div class="item">
                {{ row["item"] }} → {{ row["status"] }}
            </div>

            {% if row["qty"] %}
            <div>
                Quantity: {{ row["qty"] }}
            </div>
            {% endif %}

            <div class="time">
                {{ row["time"] }}
            </div>
        </div>

        {% else %}

        <p style="text-align:center;">
            KUCH BHI NAHI HAI 
        </p>

        {% endfor %}

    
<script>
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function () {
    navigator.serviceWorker.register('/sw.js').catch(function () {});
  });
}
</script>
</body>
    </html>
    """, history=rows)

# ==================================================
# STAFF VIEW
# ==================================================



@app.route("/staff-live")
def staff_live():
    out_items=[]; limited_items=[]
    category_controls,item_controls=load_menu_controls()
    for ingredient in MAIN_INGREDIENTS:
        data=stock[ingredient]
        if data["status"]=="OUT":
            out_items.append({"name":ingredient,"affected":affected_menu(ingredient,category_controls,item_controls),"affected_groups":group_affected_menu(affected_menu(ingredient,category_controls,item_controls),"CLOSED")})
        elif data["status"]=="LIMITED":
            try: live_qty=int(data.get("qty") or 1)
            except (TypeError,ValueError): live_qty=1
            limited_items.append({"name":ingredient,"qty":live_qty,"affected":affected_menu(ingredient,category_controls,item_controls),"affected_groups":group_affected_menu(affected_menu(ingredient,category_controls,item_controls),"LIMITED")})
    menu_out_alerts,menu_limited_alerts=menu_alerts()
    menu_status={}
    for category,items in menu.items():
        menu_status[category]={"enabled":category_controls.get(category,True),"items":[]}
        for item,deps in items.items():
            ctrl=item_controls.get((category,item),{"enabled":True,"manual_status":"AUTO"})
            menu_status[category]["items"].append({"name":item,"status":item_status(deps,category,item,category_controls.get(category,True),ctrl),"enabled":ctrl.get("enabled",True),"manual_status":ctrl.get("manual_status","AUTO")})
    return render_template_string(STAFF_LIVE_HTML,out_items=out_items,limited_items=limited_items,menu_status=menu_status,menu_out_alerts=menu_out_alerts,menu_limited_alerts=menu_limited_alerts,ingredient_categories=INGREDIENT_CATEGORIES,stock=stock)


@app.route("/staff")
def staff():

    out_items = []
    limited_items = []
    available_main = []
    category_controls, item_controls = load_menu_controls()

    for ingredient in MAIN_INGREDIENTS:
        data = stock[ingredient]
        if data["status"] == "OUT":
            out_items.append({"name": ingredient, "affected": affected_menu(ingredient, category_controls, item_controls), "affected_groups": group_affected_menu(affected_menu(ingredient, category_controls, item_controls), "CLOSED")})
        elif data["status"] == "LIMITED":
            try: staff_qty=int(data.get("qty") or 1)
            except (TypeError,ValueError): staff_qty=1
            limited_items.append({"name": ingredient, "qty": staff_qty, "affected": affected_menu(ingredient, category_controls, item_controls), "affected_groups": group_affected_menu(affected_menu(ingredient, category_controls, item_controls), "LIMITED")})
        else:
            available_main.append({"name": ingredient})

    menu_out_alerts, menu_limited_alerts = menu_alerts()
    menu_status = {}

    for category, items in menu.items():

        menu_status[category] = {
            "enabled": category_controls.get(category, True),
            "items": []
        }

        for item, dependencies in items.items():

            ctrl = item_controls.get((category, item), {"enabled": True, "manual_status": "AUTO", "qty": 1})
            menu_status[category]["items"].append({
                "name": item,
                "status": item_status(dependencies, category, item, category_controls.get(category, True), ctrl),
                "enabled": item_controls.get((category, item), {"enabled": True}).get("enabled", True),
                "manual_status": item_controls.get((category, item), {"manual_status": "AUTO"}).get("manual_status", "AUTO"),
                "qty": int(item_controls.get((category, item), {"qty": 1}).get("qty", 1) or 1)
            })

    conn = get_db()

    cur = conn.cursor()
    cur.execute("""
        SELECT item, status, qty, time
        FROM stock_history
        ORDER BY id DESC
        LIMIT 1
    """)
    latest_history = cur.fetchall()
    cur.close()

    conn.close()

    return render_template_string(
        STAFF_HTML,
        out_items=out_items,
        limited_items=limited_items,
        available_main=available_main,
        menu_status=menu_status,
        menu_out_alerts=menu_out_alerts,
        menu_limited_alerts=menu_limited_alerts,
        history=latest_history,
        ingredient_categories=INGREDIENT_CATEGORIES,
        stock=stock
    )


# =========================
# PHASE 2 — CATEGORY / ITEM ON-OFF
# =========================

@app.route("/toggle-category", methods=["POST"])
def toggle_category():
    if not session.get("kitchen"):
        return redirect("/login")

    category = request.form.get("category", "")
    action = request.form.get("action", "OFF")
    enabled = action == "ON"

    if category not in menu:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()
    if DATABASE_URL:
        cur.execute("UPDATE category_controls SET enabled = %s WHERE category = %s", (enabled, category))
    else:
        cur.execute("UPDATE category_controls SET enabled = ? WHERE category = ?", (1 if enabled else 0, category))
    conn.commit()
    cur.close()
    conn.close()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return "OK", 200
    return redirect("/")


@app.route("/toggle-item", methods=["POST"])
def toggle_item():
    if not session.get("kitchen"):
        return redirect("/login")
    category = request.form.get("category", "")
    item = request.form.get("item", "")
    action = request.form.get("action", "ON").upper()
    if category not in menu or item not in menu[category]:
        return redirect("/")
    if action not in {"ON", "OFF", "LIMITED"}:
        action = "ON"

    conn = get_db(); cur = conn.cursor()
    if action == "ON":
        enabled, manual_status, qty = True, "AUTO", 1
    elif action == "OFF":
        enabled, manual_status, qty = False, "OFF", 1
    else:
        enabled, manual_status, qty = True, "LIMITED", 1

    if DATABASE_URL:
        cur.execute("UPDATE item_controls SET enabled = %s, manual_status = %s, qty = %s WHERE category = %s AND item = %s", (enabled, manual_status, qty, category, item))
    else:
        cur.execute("UPDATE item_controls SET enabled = ?, manual_status = ?, qty = ? WHERE category = ? AND item = ?", (1 if enabled else 0, manual_status, qty, category, item))
    conn.commit(); cur.close(); conn.close()
    send_push_notification("📋 MOUZY Menu Update", f"{item} → {action}.", "mouzy-menu")
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return "OK", 200
    return redirect("/")


@app.route("/update-menu-item", methods=["POST"])
def update_menu_item():
    if not session.get("kitchen"):
        return redirect("/login")
    category = request.form.get("category", "")
    item = request.form.get("item", "")
    action = request.form.get("action", "AVAILABLE").upper()
    if category not in menu or item not in menu[category]:
        return redirect("/")

    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT qty FROM item_controls WHERE category = " + ("%s" if DATABASE_URL else "?") + " AND item = " + ("%s" if DATABASE_URL else "?"), (category, item))
    row = cur.fetchone()
    current_qty = int((row["qty"] if row else 1) or 1)

    if action == "AVAILABLE":
        enabled, manual_status, new_qty = True, "AUTO", 1
    elif action == "PLUS":
        enabled, manual_status, new_qty = True, "LIMITED", current_qty + 1
    elif action == "MINUS":
        new_qty = current_qty - 1
        if new_qty <= 0:
            enabled, manual_status, new_qty = False, "OFF", 1
        else:
            enabled, manual_status = True, "LIMITED"
    elif action == "SET_LIMITED":
        try:
            new_qty = max(1, int(request.form.get("qty", "1")))
        except ValueError:
            new_qty = 1
        enabled, manual_status = True, "LIMITED"
    else:
        enabled, manual_status, new_qty = True, "AUTO", 1

    if DATABASE_URL:
        cur.execute("UPDATE item_controls SET enabled = %s, manual_status = %s, qty = %s WHERE category = %s AND item = %s", (enabled, manual_status, new_qty, category, item))
    else:
        cur.execute("UPDATE item_controls SET enabled = ?, manual_status = ?, qty = ? WHERE category = ? AND item = ?", (1 if enabled else 0, manual_status, new_qty, category, item))
    conn.commit(); cur.close(); conn.close()
    send_push_notification("📋 MOUZY Menu Update", f"{item} → {action}.", "mouzy-menu")
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return "OK", 200
    return redirect("/")

# =========================
# UPDATE STOCK
# =========================

@app.route("/update", methods=["POST"])
def update():

    if not session.get("kitchen"):
        return redirect("/login")

    ingredient = request.form["ingredient"]
    status = request.form["status"].upper()
    qty = request.form.get("qty", "").strip()

    # LIMITED quantity is integer-based. 0 automatically becomes OUT.
    if status == "LIMITED":
        try: qty_value = int(qty)
        except (TypeError,ValueError): qty_value = 1
        if qty_value <= 0:
            status, qty = "OUT", ""
        else:
            qty = str(qty_value)
    elif status in {"AVAILABLE", "OUT"}:
        qty = ""
    else:
        status, qty = "AVAILABLE", ""

    # Save stock status to database
    conn = get_db()
    saved_qty = qty if status == "LIMITED" else ""

    if DATABASE_URL:
        conn.cursor().execute("""
            UPDATE stock
            SET status = %s, qty = %s
            WHERE ingredient = %s
        """, (status, saved_qty, ingredient))

        conn.cursor().execute("""
            INSERT INTO stock_history
            (item, status, qty, time)
            VALUES (%s, %s, %s, %s)
        """, (ingredient, status, saved_qty,
               datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d-%m-%Y %I:%M:%S %p")))
    else:
        conn.cursor().execute("""
            UPDATE stock
            SET status = ?, qty = ?
            WHERE ingredient = ?
        """, (status, saved_qty, ingredient))

        conn.cursor().execute("""
            INSERT INTO stock_history
            (item, status, qty, time)
            VALUES (?, ?, ?, ?)
        """, (ingredient, status, saved_qty,
               datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d-%m-%Y %I:%M:%S %p")))

    conn.commit()
    conn.close()

    # Reload latest stock from database
    load_stock_from_db()
    if status == "OUT":
        send_push_notification("🔴 MOUZY Stock Alert", f"{ingredient} is OUT OF STOCK.", "mouzy-stock-out")
    elif status == "LIMITED":
        send_push_notification("🟡 MOUZY Stock Alert", f"{ingredient} is LIMITED ({qty}).", "mouzy-stock-limited")
    elif status == "AVAILABLE":
        send_push_notification("🟢 MOUZY Stock Alert", f"{ingredient} is AVAILABLE again.", "mouzy-stock-available")

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return "OK", 200
    return redirect("/")


# =========================
# LIVE KITCHEN DATA
# =========================

@app.route("/live")
def live():
    if not session.get("kitchen"):
        return "", 401

    out_items = []
    limited_items = []
    available_main = []
    category_controls, item_controls = load_menu_controls()
    for ingredient in MAIN_INGREDIENTS:
        data = stock[ingredient]
        if data["status"] == "OUT":
            out_items.append({"name": ingredient, "qty": data["qty"], "affected": affected_menu(ingredient, category_controls, item_controls), "affected_groups": group_affected_menu(affected_menu(ingredient, category_controls, item_controls), "CLOSED")})
        elif data["status"] == "LIMITED":
            limited_items.append({"name": ingredient, "qty": data["qty"], "affected": affected_menu(ingredient, category_controls, item_controls), "affected_groups": group_affected_menu(affected_menu(ingredient, category_controls, item_controls), "LIMITED")})
        else:
            available_main.append({"name": ingredient})

    menu_out_alerts, menu_limited_alerts = menu_alerts()
    menu_status = {}
    for category, items in menu.items():
        menu_status[category] = {"enabled": category_controls.get(category, True), "items": []}
        for item, dependencies in items.items():
            ctrl = item_controls.get((category, item), {"enabled": True, "manual_status": "AUTO", "qty": 1})
            menu_status[category]["items"].append({
                "name": item,
                "status": item_status(dependencies, category, item, category_controls.get(category, True), ctrl),
                "enabled": ctrl.get("enabled", True),
                "manual_status": ctrl.get("manual_status", "AUTO"), "qty": int(ctrl.get("qty", 1) or 1)
            })

    return render_template_string(KITCHEN_LIVE_HTML,
        out_items=out_items, limited_items=limited_items, available_main=available_main,
        menu_status=menu_status, menu_out_alerts=menu_out_alerts,
        menu_limited_alerts=menu_limited_alerts,
        ingredient_categories=INGREDIENT_CATEGORIES,
        stock=stock)


# =========================
# HOME
# =========================

@app.route("/")
def home():

    if not session.get("kitchen"):
        return redirect("/login")

    out_items = []
    limited_items = []
    available_main = []
    category_controls, item_controls = load_menu_controls()

    for ingredient in MAIN_INGREDIENTS:
        data = stock[ingredient]
        if data["status"] == "OUT":
            out_items.append({"name": ingredient, "qty": data["qty"], "affected": affected_menu(ingredient, category_controls, item_controls), "affected_groups": group_affected_menu(affected_menu(ingredient, category_controls, item_controls), "CLOSED")})
        elif data["status"] == "LIMITED":
            limited_items.append({"name": ingredient, "qty": data["qty"], "affected": affected_menu(ingredient, category_controls, item_controls), "affected_groups": group_affected_menu(affected_menu(ingredient, category_controls, item_controls), "LIMITED")})
        else:
            available_main.append({"name": ingredient})

    menu_out_alerts, menu_limited_alerts = menu_alerts()
    menu_status = {}

    for category, items in menu.items():

        menu_status[category] = {
            "enabled": category_controls.get(category, True),
            "items": []
        }

        for item, dependencies in items.items():

            ctrl = item_controls.get((category, item), {"enabled": True, "manual_status": "AUTO", "qty": 1})
            menu_status[category]["items"].append({
                "name": item,
                "status": item_status(dependencies, category, item, category_controls.get(category, True), ctrl),
                "enabled": item_controls.get((category, item), {"enabled": True}).get("enabled", True),
                "manual_status": item_controls.get((category, item), {"manual_status": "AUTO"}).get("manual_status", "AUTO"),
                "qty": int(item_controls.get((category, item), {"qty": 1}).get("qty", 1) or 1)
            })


    return render_template_string(
        HTML,
        out_items=out_items,
        limited_items=limited_items,
        available_main=available_main,
        menu_status=menu_status,
        menu_out_alerts=menu_out_alerts,
        menu_limited_alerts=menu_limited_alerts,
        ingredient_categories=INGREDIENT_CATEGORIES,
        stock=stock
    )


# ==================================================
# KITCHEN HEAD HTML
# ==================================================

HTML = """
<!DOCTYPE html>
<html>
<head>
<link rel="manifest" href="/manifest.json">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MOUZY BANANA AVIL MILK</title>
<style>
body{font-family:Arial,sans-serif;background:#f3f5f7;margin:0;padding:15px}
h1{text-align:center}
.section{background:white;padding:15px;margin-bottom:18px;border-radius:15px;box-shadow:0 3px 10px rgba(0,0,0,.08)}
.card{background:#f8f8f8;padding:12px;margin:10px 0;border-radius:10px}
.available{border-left:6px solid green}.out{border-left:6px solid red}.limited{border-left:6px solid orange}.dependency-line{margin-top:7px;padding-left:4px;color:#444;font-size:14px}
button{border:none;padding:8px 12px;border-radius:8px;margin:4px 2px;font-weight:bold;cursor:pointer}
.out-btn{background:#dc3545;color:white}.limited-btn{background:#ffc107;color:#111}.back-btn{background:#28a745;color:white}.qty-row{display:inline-flex;align-items:center;gap:4px;margin-left:6px}.qty-btn{min-width:34px;padding:7px 10px!important;background:#6c757d;color:white}.qty-number{display:inline-block;min-width:28px;text-align:center;font-weight:bold}
input{padding:8px;border:1px solid #ccc;border-radius:7px;width:110px}
.menu-category{background:#f8f8f8;margin:10px 0;border-radius:12px;overflow:hidden;border:1px solid #eee}
.menu-category summary{cursor:pointer;padding:15px;font-weight:bold;font-size:17px;list-style:none}
.menu-category summary::-webkit-details-marker{display:none}.menu-category summary::after{content:" ▼";float:right}.menu-category[open] summary::after{content:" ▲"}
.category-items{padding:0 12px 8px}.menu-item-name{cursor:pointer;flex:1}.menu-item{display:flex;justify-content:space-between;gap:10px;align-items:center;padding:10px 3px;border-bottom:1px solid #eee}
.green{color:green;font-weight:bold}.yellow{color:#e69500;font-weight:bold}.red{color:red;font-weight:bold}.small{color:#777;font-size:13px}.ingredient-alert .qty-number{margin-left:18px;min-width:32px;display:inline-block;text-align:center}
.category-state{float:right;font-size:13px}.cat-on{color:green}.cat-off{color:red}
.ingredient-master-category{background:#f8f8f8;margin:10px 0;border-radius:12px;overflow:hidden;border:1px solid #eee}.ingredient-master-category summary{cursor:pointer;padding:14px;font-weight:bold;font-size:16px;list-style:none;display:flex;justify-content:space-between}.ingredient-master-category summary::-webkit-details-marker{display:none}.ingredient-master-category[open] summary{border-bottom:1px solid #eee}.ingredient-master-row{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px 3px;border-bottom:1px solid #eee}.ingredient-master-row .item-controls{white-space:nowrap}.ingredient-name{cursor:pointer;flex:1}.ingredient-alert{cursor:pointer}.ingredient-alert summary{list-style:none;display:flex;justify-content:space-between;align-items:center;gap:8px;cursor:pointer}.ingredient-alert summary::-webkit-details-marker{display:none}.ingredient-alert[open] summary{margin-bottom:10px}.ingredient-alert .dependency-group{margin:8px 0;padding:8px 10px;border-radius:10px;background:#f1f1f1}
.control-row{padding:8px 0;border-bottom:1px solid #eee}.item-controls{white-space:nowrap;text-align:right}
.category-off-btn,.category-on-btn,.item-off-btn,.item-on-btn,.item-limited-btn{color:white;border:none;border-radius:7px;padding:7px 10px;font-weight:bold}
.category-off-btn,.item-off-btn{background:#dc3545}.category-on-btn,.item-on-btn{background:#28a745}.item-limited-btn{background:#ffc107;color:#111!important}
.item-off-btn,.item-on-btn,.item-limited-btn{padding:5px 7px;font-size:11px}
@media(max-width:650px){.menu-item{align-items:flex-start;flex-direction:column}.item-controls{text-align:left}}
</style>
</head>
<body>
<h1>🥤 MOUZY BANANA AVIL MILK</h1>
<div style="text-align:center;margin-bottom:15px">
<a href="/history" style="display:inline-block;background:#343a40;color:white;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:bold">📋 STOCK HISTORY</a>
<a href="/logout" style="display:inline-block;background:#dc3545;color:white;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:bold;margin-left:6px">🔒 LOGOUT</a>
</div>
<div id="kitchen-live-root">Loading...</div>
<script>
let kitchenEditing=false;
async function refreshKitchen(){
  if(kitchenEditing)return;
  try{
    const r=await fetch('/live',{cache:'no-store'}); if(!r.ok)return;
    const root=document.getElementById('kitchen-live-root');
    const open=Array.from(root.querySelectorAll('details[open]'))
      .map(d=>d.dataset.key || d.dataset.category || d.dataset.ingredient)
      .filter(Boolean);
    root.innerHTML=await r.text();
    open.forEach(key=>{
      const d=Array.from(root.querySelectorAll('details')).find(x=>
        (x.dataset.key || x.dataset.category || x.dataset.ingredient)===key
      );
      if(d)d.open=true;
    });
  }catch(e){}
}
const kitchenRoot=document.getElementById('kitchen-live-root');
let kitchenBusy=false;
kitchenRoot.addEventListener('focusin',e=>{
  if(e.target.matches('input,select,textarea')) kitchenEditing=true;
});
kitchenRoot.addEventListener('focusout',e=>{
  if(e.target.matches('input,select,textarea')) setTimeout(()=>{
    if(!kitchenRoot.querySelector('input:focus,select:focus,textarea:focus')) kitchenEditing=false;
  },150);
});
kitchenRoot.addEventListener('submit',async e=>{
  const form=e.target.closest('form'); if(!form)return;
  e.preventDefault();
  if(kitchenBusy)return;
  kitchenBusy=true;
  const button=form.querySelector('button'); if(button)button.disabled=true;
  try{
    const response=await fetch(form.action,{
      method:'POST',
      body:new FormData(form),
      cache:'no-store',
      credentials:'same-origin',
      headers:{'X-Requested-With':'XMLHttpRequest'}
    });
    if(!response.ok) throw new Error('POST failed: '+response.status);
    await refreshKitchen();
  }catch(err){
    console.error('Mouzy control update failed:',err);
  }finally{
    kitchenBusy=false;
  }
});
refreshKitchen();setInterval(()=>{ if(!kitchenBusy) refreshKitchen(); },1000);
</script>

<script>
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function () {
    navigator.serviceWorker.register('/sw.js').catch(function () {});
  });
}
</script>
</body>
</html>
"""


KITCHEN_LIVE_HTML = """
<style>
.ingredient-alert{cursor:pointer;}
.ingredient-alert summary{list-style:none;display:flex;justify-content:space-between;align-items:center;gap:18px;cursor:pointer;user-select:none}.ingredient-alert summary .qty-number{margin-left:18px;min-width:32px;display:inline-block;text-align:center}
.ingredient-alert summary::-webkit-details-marker{display:none;}
.ingredient-alert[open] summary{margin-bottom:10px;}
.affected-title{font-weight:700;margin:8px 0;}
.dependency-group{margin:8px 0;padding:8px 10px;border-radius:10px;background:rgba(127,127,127,.08);}
.dependency-group>div{margin-top:5px;}
.ingredient-actions{margin:8px 0;}
</style>


<div class="section">
<h2>🔴 OUT OF STOCK</h2>
{% if out_items or menu_out_alerts %}
{% for x in out_items %}<details class="card out ingredient-alert" data-key="ingredient-out-{{ x["name"]|e }}" data-ingredient="{{ x["name"]|e }}"><summary><b>🔴 {{ x["name"] }}</b></summary><div class="ingredient-actions"><form method="POST" action="/update" style="display:inline"><input type="hidden" name="ingredient" value="{{ x["name"] }}"><input type="hidden" name="status" value="AVAILABLE"><button type="submit" onclick="event.stopPropagation()" class="back-btn">🟢 AVAILABLE</button></form></div>{% if x["affected_groups"] %}<div class="affected-title">Affected menu:</div>{% for g in x["affected_groups"] %}<div class="dependency-group"><b>{{ g["category"] }}</b>{% for mi in g["items"] %}<div>→ {{ mi }} <span class="red">🔴 CLOSED</span></div>{% endfor %}</div>{% endfor %}{% else %}<div class="small">No mapped menu dependency yet.</div>{% endif %}</details>{% endfor %}
{% for a in menu_out_alerts %}<details class="card out ingredient-alert" data-key="menu-out-{{ a["category"] }}">
<summary><b>🔴 {{ a["category"] }}</b><span>›</span></summary>
{% if a["item"] is none %}
<div class="affected-title">Category is OFF:</div>
<div class="small">All items in this category are closed.</div>
<div class="ingredient-actions"><form method="POST" action="/toggle-category"><input type="hidden" name="category" value="{{ a["category"] }}"><input type="hidden" name="action" value="ON"><button type="submit" onclick="event.stopPropagation()" class="back-btn">🟢 AVAILABLE / TURN CATEGORY ON</button></form></div>
{% else %}
{% for item_name in a["items"] %}<div style="margin-top:8px"><b>→ {{ item_name }}</b> <span class="red">🔴 CLOSED</span>
<form method="POST" action="/update-menu-item" style="display:inline"><input type="hidden" name="category" value="{{ a["category"] }}"><input type="hidden" name="item" value="{{ item_name }}"><input type="hidden" name="action" value="AVAILABLE"><button type="submit" onclick="event.stopPropagation()" class="back-btn">🟢 AVAILABLE</button></form></div>{% endfor %}
{% endif %}
</details>{% endfor %}
{% else %}<p>✅ No main ingredient or menu item is OUT.</p>{% endif %}
</div>

<div class="section">
<h2>🟡 LIMITED</h2>
{% if limited_items or menu_limited_alerts %}
{% for x in limited_items %}<details class="card limited ingredient-alert" data-key="ingredient-limited-{{ x["name"]|e }}" data-ingredient="{{ x["name"]|e }}"><summary><b>🟡 {{ x["name"] }}</b> <span class="qty-number">{{ x["qty"] }}</span></summary><div class="qty-row"><form method="POST" action="/update" style="display:inline"><input type="hidden" name="ingredient" value="{{ x["name"] }}"><input type="hidden" name="status" value="LIMITED"><input type="hidden" name="qty" value="{{ x["qty"]|int - 1 }}"><button type="submit" onclick="event.stopPropagation()" class="qty-btn">−</button></form><span class="qty-number">{{ x["qty"] }}</span><form method="POST" action="/update" style="display:inline"><input type="hidden" name="ingredient" value="{{ x["name"] }}"><input type="hidden" name="status" value="LIMITED"><input type="hidden" name="qty" value="{{ x["qty"]|int + 1 }}"><button type="submit" onclick="event.stopPropagation()" class="qty-btn">+</button></form></div>{% if x["affected_groups"] %}<div class="affected-title">Affected menu:</div>{% for g in x["affected_groups"] %}<div class="dependency-group"><b>{{ g["category"] }}</b>{% for mi in g["items"] %}<div>→ {{ mi }} <span class="yellow">🟡 LIMITED</span></div>{% endfor %}</div>{% endfor %}{% else %}<div class="small">No mapped menu dependency yet.</div>{% endif %}</details>{% endfor %}
{% for a in menu_limited_alerts %}<details class="card limited ingredient-alert" data-key="menu-limited-{{ a["category"] }}"><summary><b>🟡 {{ a["category"] }}</b><span>›</span></summary>{% for mi in a["items"] %}<div style="margin-top:8px"><b>→ {{ mi["item"] }}</b> <span class="yellow">🟡 LIMITED</span><div class="qty-row"><form method="POST" action="/update-menu-item" style="display:inline"><input type="hidden" name="category" value="{{ a["category"] }}"><input type="hidden" name="item" value="{{ mi["item"] }}"><input type="hidden" name="action" value="MINUS"><button type="submit" onclick="event.stopPropagation()" class="qty-btn">−</button></form><span class="qty-number">{{ mi["qty"] }}</span><form method="POST" action="/update-menu-item" style="display:inline"><input type="hidden" name="category" value="{{ a["category"] }}"><input type="hidden" name="item" value="{{ mi["item"] }}"><input type="hidden" name="action" value="PLUS"><button type="submit" onclick="event.stopPropagation()" class="qty-btn">+</button></form><form method="POST" action="/update-menu-item" style="display:inline"><input type="hidden" name="category" value="{{ a["category"] }}"><input type="hidden" name="item" value="{{ mi["item"] }}"><input type="hidden" name="action" value="AVAILABLE"><button type="submit" onclick="event.stopPropagation()" class="back-btn">🟢 AVAILABLE</button></form></div></div>{% endfor %}</details>{% endfor %}
{% else %}<p>✅ No main ingredient or menu item is LIMITED.</p>{% endif %}
</div>

<div class="section">
<h2>🧾 INGREDIENT MASTER</h2>
<p class="small">Tap a category to expand/collapse. Every ingredient has ON / LIMITED / OFF control.</p>
{% for cat, ingredients in ingredient_categories.items() %}
<details class="ingredient-master-category" data-key="ingredient-category-{{ cat|e }}">
<summary><b>{{ cat }}</b><span>›</span></summary>
<div class="category-items">
{% for name in ingredients %}
{% set st = stock[name]["status"] %}
{% set q = stock[name].get("qty","") %}
<div class="ingredient-master-row">
<div class="ingredient-name" onclick="event.stopPropagation(); this.closest('details').open=false" title="Tap to collapse category"><b>{{ name }}</b><br><span class="{{ 'green' if st == 'AVAILABLE' else 'yellow' if st == 'LIMITED' else 'red' }}">{{ '🟢 ON / AVAILABLE' if st == 'AVAILABLE' else '🟡 LIMITED' if st == 'LIMITED' else '🔴 OUT' }}</span>{% if st == 'LIMITED' %} <span class="qty-number">{{ q }}</span>{% endif %}</div>
<div class="item-controls">
{% if st != 'AVAILABLE' %}<form method="POST" action="/update" style="display:inline"><input type="hidden" name="ingredient" value="{{ name }}"><input type="hidden" name="status" value="AVAILABLE"><button type="submit" onclick="event.stopPropagation()" class="item-on-btn">🟢 ON</button></form>{% endif %}
{% if st == 'LIMITED' %}<form method="POST" action="/update" style="display:inline"><input type="hidden" name="ingredient" value="{{ name }}"><input type="hidden" name="status" value="LIMITED"><input type="hidden" name="qty" value="{{ q|int + 1 }}"><button type="submit" onclick="event.stopPropagation()" class="item-limited-btn">＋</button></form><form method="POST" action="/update" style="display:inline"><input type="hidden" name="ingredient" value="{{ name }}"><input type="hidden" name="status" value="LIMITED"><input type="hidden" name="qty" value="{{ q|int - 1 }}"><button type="submit" onclick="event.stopPropagation()" class="qty-btn">−</button></form>{% else %}<form method="POST" action="/update" style="display:inline"><input type="hidden" name="ingredient" value="{{ name }}"><input type="hidden" name="status" value="LIMITED"><input type="hidden" name="qty" value="1"><button type="submit" onclick="event.stopPropagation()" class="item-limited-btn">🟡 LIMITED</button></form>{% endif %}
{% if st != 'OUT' %}<form method="POST" action="/update" style="display:inline"><input type="hidden" name="ingredient" value="{{ name }}"><input type="hidden" name="status" value="OUT"><button type="submit" onclick="event.stopPropagation()" class="out-btn">🔴 OFF</button></form>{% endif %}
</div>
</div>
{% endfor %}
</div>
</details>
{% endfor %}
</div>

<div class="section">
<h2>🥤 MENU STRUCTURE</h2>
<p class="small">All categories are collapsed by default. Changes update live every 1 second.</p>
{% for category,data in menu_status.items() %}
<details class="menu-category" data-key="menu-{{ category|e }}" data-category="{{ category }}">
<summary><span>{{ category }}</span> <span class="category-state {{ 'cat-on' if data["enabled"] else 'cat-off' }}">{{ '🟢 ON' if data["enabled"] else '🔴 OUT OF STOCK' }}</span></summary>
<div class="category-items">
<div class="control-row"><form method="POST" action="/toggle-category" class="menu-control-form"><input type="hidden" name="category" value="{{ category }}"><input type="hidden" name="action" value="{{ 'OFF' if data["enabled"] else 'ON' }}"><button class="{{ 'category-off-btn' if data["enabled"] else 'category-on-btn' }}">{{ '🔴 TURN CATEGORY OFF' if data["enabled"] else '🟢 TURN CATEGORY ON' }}</button></form></div>
{% for item in data["items"] %}
<div class="menu-item">
<div class="menu-item-name" onclick="this.closest('details').open=false" title="Tap item name to collapse category"><b>{{ item["name"] }}</b><br><span class="{{ 'green' if item["status"] == 'AVAILABLE' else 'yellow' if item["status"] == 'LIMITED' else 'red' }}">{{ '🟢 AVAILABLE' if item["status"] == 'AVAILABLE' else '🟡 LIMITED' if item["status"] == 'LIMITED' else '🔴 OUT OF STOCK' }}</span>{% if item["status"] == "LIMITED" %} <span class="qty-number">{{ item["qty"] }}</span>{% endif %}</div>
<div class="item-controls">
{% if item["status"] == "LIMITED" %}
<form method="POST" action="/update-menu-item" class="menu-control-form" style="display:inline"><input type="hidden" name="category" value="{{ category }}"><input type="hidden" name="item" value="{{ item["name"] }}"><input type="hidden" name="action" value="MINUS"><button type="submit" class="qty-btn">−</button></form>
<span class="qty-number">{{ item["qty"] }}</span>
<form method="POST" action="/update-menu-item" class="menu-control-form" style="display:inline"><input type="hidden" name="category" value="{{ category }}"><input type="hidden" name="item" value="{{ item["name"] }}"><input type="hidden" name="action" value="PLUS"><button type="submit" class="qty-btn">＋</button></form>
<form method="POST" action="/update-menu-item" class="menu-control-form" style="display:inline"><input type="hidden" name="category" value="{{ category }}"><input type="hidden" name="item" value="{{ item["name"] }}"><input type="hidden" name="action" value="AVAILABLE"><button type="submit" class="back-btn">🟢 AVAILABLE</button></form>
<form method="POST" action="/toggle-item" class="menu-control-form" style="display:inline"><input type="hidden" name="category" value="{{ category }}"><input type="hidden" name="item" value="{{ item["name"] }}"><input type="hidden" name="action" value="OFF"><button type="submit" class="item-off-btn">🔴 OFF</button></form>
{% else %}
<form method="POST" action="/toggle-item" class="menu-control-form" style="display:inline"><input type="hidden" name="category" value="{{ category }}"><input type="hidden" name="item" value="{{ item["name"] }}"><input type="hidden" name="action" value="ON"><button type="submit" class="item-on-btn">🟢 ON</button></form>
<form method="POST" action="/toggle-item" class="menu-control-form" style="display:inline"><input type="hidden" name="category" value="{{ category }}"><input type="hidden" name="item" value="{{ item["name"] }}"><input type="hidden" name="action" value="LIMITED"><button type="submit" class="item-limited-btn">🟡 LIMITED</button></form>
<form method="POST" action="/toggle-item" class="menu-control-form" style="display:inline"><input type="hidden" name="category" value="{{ category }}"><input type="hidden" name="item" value="{{ item["name"] }}"><input type="hidden" name="action" value="OFF"><button type="submit" class="item-off-btn">🔴 OFF</button></form>
{% if item["status"] == "OUT OF STOCK" or item["status"] == "CLOSED" %}
<form method="POST" action="/toggle-item" class="menu-control-form" style="display:inline"><input type="hidden" name="category" value="{{ category }}"><input type="hidden" name="item" value="{{ item["name"] }}"><input type="hidden" name="action" value="ON"><button type="submit" class="back-btn">🟢 AVAILABLE</button></form>
{% endif %}
{% endif %}
</div></div>
{% endfor %}
</div></details>
{% endfor %}
</div>

"""
STAFF_HTML = """
<!DOCTYPE html>
<html><head>
<link rel="manifest" href="/manifest.json">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mouzy Edappally Staff View</title>
<style>
body{font-family:Arial,sans-serif;background:#f3f5f7;margin:0;padding:15px}.section{background:white;padding:15px;margin-bottom:18px;border-radius:15px;box-shadow:0 3px 10px rgba(0,0,0,.08)}.card{background:#f8f8f8;padding:12px;margin:10px 0;border-radius:10px}.red{color:red;font-weight:bold}.yellow{color:#e69500;font-weight:bold}.green{color:green;font-weight:bold}.small{color:#777;font-size:13px}.ingredient-alert .qty-number{margin-left:18px;min-width:32px;display:inline-block;text-align:center}.dependency-line{margin-top:7px;padding-left:4px;color:#444;font-size:14px}.menu-category{background:#f8f8f8;margin:10px 0;border-radius:12px;overflow:hidden;border:1px solid #eee}.menu-category summary{cursor:pointer;padding:15px;font-weight:bold;font-size:17px;list-style:none}.menu-category summary::-webkit-details-marker{display:none}.menu-category summary::after{content:" ▼";float:right}.menu-category[open] summary::after{content:" ▲"}.category-items{padding:0 12px 8px}.menu-item-name{cursor:pointer;flex:1}.menu-item{display:flex;justify-content:space-between;padding:10px 3px;border-bottom:1px solid #eee}.category-state{float:right;font-size:13px}.cat-on{color:green}.cat-off{color:red}
</style></head><body>
<h1 style="text-align:center">🥤 MOUZY EDAPPALLY STAFF VIEW</h1>
<div style="text-align:center;margin-bottom:12px"><b>⚡ LIVE STAFF VIEW</b><br><span class="small">Updates every 1 second. Open menu categories stay open.</span></div>
<div id="staff-live-root">Loading...</div>
<p style="text-align:center;color:#777">👀 Staff View — Only View<br>⚡ Live update — no page refresh needed</p>
<script>
async function refreshStaff(){
 try{
  const r=await fetch('/staff-live',{cache:'no-store'});if(!r.ok)return;
  const root=document.getElementById('staff-live-root');
  const open=Array.from(root.querySelectorAll('details[open]'))
     .map(d=>d.dataset.key || d.dataset.category || d.dataset.ingredient)
     .filter(Boolean);
  root.innerHTML=await r.text();
  open.forEach(key=>{
    const d=Array.from(root.querySelectorAll('details')).find(x=>
      (x.dataset.key || x.dataset.category || x.dataset.ingredient)===key
    );
    if(d)d.open=true;
   });
 }catch(e){}
}
refreshStaff();setInterval(refreshStaff,1000);
</script>
<div style="text-align:center;margin:12px 0">
<button id="notify-btn" type="button" style="background:#111;color:white;border:none;border-radius:9px;padding:10px 16px;font-weight:bold">🔔 ENABLE MOBILE NOTIFICATIONS</button>
<div id="notify-status" style="font-size:13px;color:#777;margin-top:6px"></div>
</div>
<script>
function b64ToBytes(s){const p='='.repeat((4-s.length%4)%4);const b=atob((s+p).replace(/-/g,'+').replace(/_/g,'/'));const a=new Uint8Array(b.length);for(let i=0;i<b.length;i++)a[i]=b.charCodeAt(i);return a;}
async function enableMouzyPush(){
 const st=document.getElementById('notify-status');
 if(!('serviceWorker' in navigator)&&!('PushManager' in window)){st.textContent='Push notifications are not supported here.';return;}
 try{
  const permission=await Notification.requestPermission();
  if(permission!=='granted'){st.textContent='Notification permission was not granted.';return;}
  const reg=await navigator.serviceWorker.ready;
  const key=(await (await fetch('/push/public-key',{cache:'no-store'})).json()).publicKey;
  let sub=await reg.pushManager.getSubscription();
  if(!sub) sub=await reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:b64ToBytes(key)});
  const r=await fetch('/push/subscribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(sub)});
  if(!r.ok) throw new Error('subscribe failed');
  st.textContent='✅ Notifications enabled on this phone.';document.getElementById('notify-btn').textContent='🔔 NOTIFICATIONS ON';
 }catch(e){console.error(e);st.textContent='Could not enable notifications. Try again.';}
}
document.getElementById('notify-btn').addEventListener('click',enableMouzyPush);
</script>
<script>
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function () {
    navigator.serviceWorker.register('/sw.js').catch(function () {});
  });
}
</script>
</body></html>
"""

STAFF_LIVE_HTML = """
<div class="section"><h2 class="red">🔴 OUT OF STOCK</h2>
{% if out_items or menu_out_alerts %}{% for x in out_items %}<details class="card out ingredient-alert" data-key="staff-ingredient-out-{{ x["name"]|e }}"><summary><b>❌ {{ x["name"] }}</b><span>›</span></summary>{% if x["affected_groups"] %}<div class="affected-title">Affected menu:</div>{% for g in x["affected_groups"] %}<div class="dependency-group"><b>{{ g["category"] }}</b>{% for mi in g["items"] %}<div>→ {{ mi }} <span class="red">🔴 CLOSED</span></div>{% endfor %}</div>{% endfor %}{% else %}<div class="small">No mapped menu dependency yet.</div>{% endif %}</details>{% endfor %}{% for a in menu_out_alerts %}
<details class="card out ingredient-alert" data-key="staff-menu-out-{{ a["category"] }}">
<summary><b>🔴 {{ a["category"] }}</b><span>›</span></summary>
{% if a["item"] is none %}
<div class="dependency-line">→ CATEGORY OFF — all items closed</div>
{% else %}
{% for item_name in a["items"] %}<div class="dependency-line">→ {{ item_name }} <span class="red">🔴 CLOSED</span></div>{% endfor %}
{% endif %}
</details>
{% endfor %}{% else %}<p>✅ Nothing is OUT.</p>{% endif %}</div>

<div class="section"><h2 class="yellow">🟡 LIMITED</h2>
{% if limited_items or menu_limited_alerts %}{% for x in limited_items %}<details class="card limited ingredient-alert" data-key="staff-ingredient-limited-{{ x["name"]|e }}"><summary><b>⚠️ {{ x["name"] }}</b><span class="qty-number">{{ x["qty"] }}</span></summary>{% if x["affected_groups"] %}<div class="affected-title">Affected menu:</div>{% for g in x["affected_groups"] %}<div class="dependency-group"><b>{{ g["category"] }}</b>{% for mi in g["items"] %}<div>→ {{ mi }} <span class="yellow">🟡 LIMITED</span></div>{% endfor %}</div>{% endfor %}{% else %}<div class="small">No mapped menu dependency yet.</div>{% endif %}</details>{% endfor %}{% for a in menu_limited_alerts %}
<details class="card limited ingredient-alert" data-key="staff-menu-limited-{{ a["category"] }}"><summary><b>🟡 {{ a["category"] }}</b><span>›</span></summary>
{% for mi in a["items"] %}
<div class="dependency-line">→ {{ mi["item"] }} — LIMITED {{ mi["qty"] }}</div>
{% endfor %}
</details>
{% endfor %}{% else %}<p>✅ Nothing is LIMITED.</p>{% endif %}</div>

<div class="section"><h2>🥤 MENU STRUCTURE</h2><p class="small">Tap a category to see its items. Live updates do not reload the page.</p>
{% for category,data in menu_status.items() %}<details class="menu-category" data-key="menu-{{ category|e }}" data-category="{{ category }}"><summary><span>{{ category }}</span> <span class="category-state {{ 'cat-on' if data["enabled"] else 'cat-off' }}">{{ '🟢 ON' if data["enabled"] else '🔴 OUT OF STOCK' }}</span></summary><div class="category-items">
{% for item in data["items"] %}<div class="menu-item"><span><b>{{ item["name"] }}</b></span><span class="{{ 'green' if item["status"] == 'AVAILABLE' else 'yellow' if item["status"] == 'LIMITED' else 'red' }}">{{ '🟢 AVAILABLE' if item["status"] == 'AVAILABLE' else '🟡 LIMITED' if item["status"] == 'LIMITED' else '🔴 OUT OF STOCK' }}</span></div>{% endfor %}
</div></details>{% endfor %}</div>
"""


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )