from flask import Flask, render_template_string, request, redirect, session
from datetime import datetime
from zoneinfo import ZoneInfo
import sqlite3 #import
import os
import psycopg2
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

    conn.commit()
    conn.close()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

# =========================
# STOCK
# =========================

stock = { 
    "Mango": {"status": "AVAILABLE", "qty": ""},
    "Boost": {"status": "AVAILABLE", "qty": ""},
    "Strawberry": {"status": "AVAILABLE", "qty": ""},
    "Dates": {"status": "AVAILABLE", "qty": ""},
    "Kiwi": {"status": "AVAILABLE", "qty": ""},
    "Blueberry Dry": {"status": "AVAILABLE", "qty": ""},
    "Tender": {"status": "AVAILABLE", "qty": ""},
    "Dry Fruits": {"status": "AVAILABLE", "qty": ""},

    "Vanilla Ice Cream": {"status": "AVAILABLE", "qty": ""},
    "Strawberry Ice Cream": {"status": "AVAILABLE", "qty": ""},
    "Pista Ice Cream": {"status": "AVAILABLE", "qty": ""},
    "Mango Ice Cream": {"status": "AVAILABLE", "qty": ""},
    "Butterscotch Ice Cream": {"status": "AVAILABLE", "qty": ""},
    "Chocolate Ice Cream": {"status": "AVAILABLE", "qty": ""},
    "Dates Ice Cream": {"status": "AVAILABLE", "qty": ""},
    "Spanish Ice Cream": {"status": "AVAILABLE", "qty": ""},
    "Tender Ice Cream": {"status": "AVAILABLE", "qty": ""},
    "Blueberry Ice Cream": {"status": "AVAILABLE", "qty": ""},
    "Chocolate": {"status": "AVAILABLE", "qty": ""},
    "Fruit Mix": {"status": "AVAILABLE", "qty": ""},
    "Cashew / Nuts": {"status": "AVAILABLE", "qty": ""},
    "Badam": {"status": "AVAILABLE", "qty": ""},
}
init_db()
def load_stock_from_db():
    global stock

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT ingredient, status, qty FROM stock")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    stock = {
        row["ingredient"]: {
            "status": row["status"],
            "qty": row["qty"]
        }
        for row in rows
    }


load_stock_from_db()

# =========================
# MAIN INGREDIENTS
# =========================

MAIN_INGREDIENTS = [
    "Boost",
    "Mango",
    "Strawberry",
    "Dates",
    "Kiwi",
    "Blueberry Dry",
    "Tender",
    "Dry Fruits",
    # Fruit Mix and Vanilla Ice Cream are dependencies, not main ingredient buttons.
]


# =========================
# MENU DEPENDENCIES
# =========================

menu = {
    "REGULAR AVIL MILK": {"Mini": [], "Normal": [], "Normal Boost": ["Boost"], "Fruit": ["Fruit Mix"], "Mango Passion": ["Mango"], "White": ["Vanilla Ice Cream"], "Special": ["Fruit Mix", "Vanilla Ice Cream"], "SP Boost": ["Boost", "Vanilla Ice Cream"]},
    "LITTLE COMBO AVIL MILK": {"Little Strawberry": ["Strawberry Ice Cream", "Strawberry"], "Little Pista": ["Pista Ice Cream"], "Little Mango": ["Mango Ice Cream", "Mango"], "Little Arabian": ["Dates Ice Cream", "Dates"], "Little Butterscotch": ["Butterscotch Ice Cream"], "Little Choco": ["Chocolate Ice Cream", "Chocolate"]},
    "FUSION AVIL MILK": {"Watermelon": ["Vanilla Ice Cream"], "Rooh Afza": ["Vanilla Ice Cream"], "Butterscotch": ["Butterscotch Ice Cream"], "Pista": ["Pista Ice Cream"], "Kiwi": ["Vanilla Ice Cream", "Kiwi"], "Chocolate": ["Chocolate Ice Cream", "Chocolate"], "Strawberry": ["Strawberry Ice Cream", "Strawberry"], "Mango": ["Mango Ice Cream", "Mango"], "Dates": ["Dates Ice Cream", "Dates"]},
    "SUPREME AVIL MILK": {"Nuts": ["Butterscotch Ice Cream", "Cashew / Nuts", "Badam"], "Fruit Nut": ["Fruit Mix", "Vanilla Ice Cream", "Cashew / Nuts", "Badam"], "Royal": ["Fruit Mix", "Mango Ice Cream", "Cashew / Nuts", "Badam"], "Redberry Nut": ["Fruit Mix", "Vanilla Ice Cream", "Strawberry Ice Cream", "Cashew / Nuts", "Badam", "Strawberry"], "Malgoa Nut": ["Mango Ice Cream", "Mango", "Cashew / Nuts", "Badam"], "Pista Nut": ["Fruit Mix", "Vanilla Ice Cream", "Pista Ice Cream", "Cashew / Nuts", "Badam"], "Choco Nut": ["Chocolate Ice Cream", "Chocolate", "Cashew / Nuts", "Badam"], "Rio Nut": ["Fruit Mix", "Pista Ice Cream", "Mango Ice Cream", "Cashew / Nuts", "Badam"], "Spanish Nut": ["Spanish Ice Cream", "Cashew / Nuts", "Badam"], "Tender Coconut": ["Tender Ice Cream", "Cashew / Nuts", "Badam"], "Blueberry Nut": ["Blueberry Ice Cream", "Cashew / Nuts", "Badam"], "Arabian Nut": ["Dates Ice Cream", "Dates", "Cashew / Nuts", "Badam"], "Dry Fruits": ["Mango Ice Cream", "Dry Fruits", "Cashew / Nuts", "Badam"], "Special Nut": ["Spanish Ice Cream", "Cashew / Nuts", "Badam"]},
    "DIET AVIL MIX": {"Normal Diet": [], "Fruit Diet": ["Fruit Mix"], "Fruit Nut Diet": ["Fruit Mix", "Cashew / Nuts", "Badam"], "Nuts Diet": ["Cashew / Nuts", "Badam"], "Dry Fruits Diet": ["Cashew / Nuts", "Dry Fruits", "Badam"]},
    "CHEESEY CHIKEN": {"Chicken Club Sandwich": [], "Chicken Mini Sandwich": [], "Samoona": [], "Cheesy Chick Bake - Classic Medium": [], "Cheesy Chick Bake - Classic Large": [], "Cheesy Chick Bake - Schezwan Medium": [], "Cheesy Chick Bake - Schezwan Large": [], "Cheesy Chick Bake - BBQ Medium": [], "Cheesy Chick Bake - BBQ Large": [], "Cheesy Chick Bake - Mexican Medium": [], "Cheesy Chick Bake - Mexican Large": []},
    "LIME": {"Fresh Lime": [], "Mexican Mint Lime": [], "Mint Lime": [], "Pineapple Lime": [], "Orange Lime": [], "Ginger Lime": []},
    "MOJITO": {"Classic Mojito": [], "Mango Mojito": [], "Grapes Mojito": [], "Passion Mojito": [], "Pineapple Mojito": [], "Strawberry Mojito": []},
    "FRUIT SHAKE": {"Banago": [], "Mangopass": [], "Chikudates": [], "Banatend": [], "Tendates": [], "Datifig": []},
    "FRESH JUICE": {"Orange": [], "Watermelon": [], "Pineapple": [], "Pappaya": [], "Muskmelon": [], "Mosambi": []},
    "FALOODA": {"Royal Banaloooda": [], "Strawberry Banaloooda": [], "Chocolate Banaloooda": [], "Mango Banaloooda": [], "Pista Banaloooda": [], "Dry Fruit Banaloooda": []},
    "CHOCOLATE SHAKE": {"Mississippi Mud": [], "Oreo Wonder": [], "Pie Melt": [], "Kitkat Smash": [], "Boost Blast": [], "Choco Coffee Charge": []},
    "DOODH MALAI": {"Mix Fruit Malai": [], "Mango Magic Malai": [], "Chocolate Malai": [], "Seetaphal Malai": [], "Kiwi Malai": []},
    "LASSI": {"Plain Lassi": [], "Mango Lassi": [], "Chocolate Lassi": [], "Mix Fruit Lassi": [], "Dry Nuts Lassi": [], "Dry Fruit Lassi": []}
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
                PRIMARY KEY (category, item)
            )
        """)

        # Migration: older Phase 2 databases may already have item_controls
        # without the manual_status column. Add it before any INSERT uses it.
        cur.execute("SELECT 1 FROM information_schema.columns WHERE table_name = 'item_controls' AND column_name = 'manual_status'")
        if cur.fetchone() is None:
            cur.execute("ALTER TABLE item_controls ADD COLUMN manual_status TEXT NOT NULL DEFAULT 'AUTO'")

        for category, items in menu.items():
            cur.execute("""
                INSERT INTO category_controls (category, enabled)
                VALUES (%s, TRUE)
                ON CONFLICT (category) DO NOTHING
            """, (category,))
            for item in items:
                cur.execute("""
                    INSERT INTO item_controls (category, item, enabled, manual_status)
                    VALUES (%s, %s, TRUE, 'AUTO')
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
                PRIMARY KEY (category, item)
            )
        """)

        # Migration: older local databases may already have item_controls
        # without the manual_status column. Add it before any INSERT uses it.
        cur.execute("PRAGMA table_info(item_controls)")
        cols = [r[1] for r in cur.fetchall()]
        if "manual_status" not in cols:
            cur.execute("ALTER TABLE item_controls ADD COLUMN manual_status TEXT NOT NULL DEFAULT 'AUTO'")

        for category, items in menu.items():
            cur.execute("""
                INSERT OR IGNORE INTO category_controls (category, enabled)
                VALUES (?, 1)
            """, (category,))
            for item in items:
                cur.execute("""
                    INSERT OR IGNORE INTO item_controls (category, item, enabled, manual_status)
                    VALUES (?, ?, 1, 'AUTO')
                """, (category, item))

    conn.commit()
    cur.close()
    conn.close()


def load_menu_controls():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT category, enabled FROM category_controls")
    category_rows = cur.fetchall()
    cur.execute("SELECT category, item, enabled, manual_status FROM item_controls")
    item_rows = cur.fetchall()
    cur.close()
    conn.close()

    categories = {row["category"]: bool(row["enabled"]) for row in category_rows}
    items = {(row["category"], row["item"]): {"enabled": bool(row["enabled"]), "manual_status": row["manual_status"]} for row in item_rows}
    return categories, items


init_menu_controls()


def effective_item_status(category, item, dependencies, category_enabled=None, item_control=None):
    """Calculate menu status without repeatedly opening the database."""
    if category_enabled is None or item_control is None:
        category_controls, item_controls = load_menu_controls()
        category_enabled = category_controls.get(category, True)
        item_control = item_controls.get((category, item), {"enabled": True, "manual_status": "AUTO"})

    if not category_enabled:
        return "CLOSED"

    if isinstance(item_control, bool):
        item_control = {"enabled": item_control, "manual_status": "AUTO"}

    if not item_control.get("enabled", True):
        return "CLOSED"

    if item_control.get("manual_status") == "LIMITED":
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
    """Return menu-level OUT/LIMITED alerts caused by manual controls.

    Ingredient-driven alerts are already handled by affected_menu().
    Keeping these lists focused on manual controls prevents duplicate alerts.
    """
    category_controls, item_controls = load_menu_controls()
    out_alerts = []
    limited_alerts = []

    for category, items in menu.items():
        # A category manually switched OFF is represented by the category only.
        if not category_controls.get(category, True):
            out_alerts.append({"category": category, "item": None})
            continue

        for item in items:
            control = item_controls.get(
                (category, item),
                {"enabled": True, "manual_status": "AUTO"}
            )

            if not control.get("enabled", True):
                out_alerts.append({"category": category, "item": item})
            elif control.get("manual_status") == "LIMITED":
                limited_alerts.append({"category": category, "item": item})

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
                control = item_controls.get((category, item), {"enabled": True, "manual_status": "AUTO"})
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
        >
            🔓 ANDAR JANE K LIYE AAPKA DALIYEN NAA😁🤩
        </button>

    </form>

    <br>

    <a href="/staff">
        👀 Staff View OHH HELLO IDHAR DEKHO IDHAR
    </a>

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

        <style>
            body {
                font-family: Arial;
                padding: 20px;
                background: #f5f5f5;
            }

            h2 {
                text-align: center;
            }

            .history {
                background: white;
                padding: 12px;
                margin: 10px 0;
                border-radius: 10px;
            }

            .item {
                font-weight: bold;
                font-size: 18px;
            }

            .time {
                color: #777;
                font-size: 13px;
                margin-top: 5px;
            }
        </style>
    </head>
    <meta http-equiv="refresh" content="1">
    </head>

    <body>

        <h2>📋 Stock History</h2>
        <form method="POST" action="/clear-history"
      onsubmit="return confirm('Clear all history?');"
      style="text-align:center; margin-bottom:20px;">

    <button type="submit">
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
    return render_template_string(STAFF_LIVE_HTML,out_items=out_items,limited_items=limited_items,menu_status=menu_status,menu_out_alerts=menu_out_alerts,menu_limited_alerts=menu_limited_alerts)


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

            ctrl = item_controls.get((category, item), {"enabled": True, "manual_status": "AUTO"})
            menu_status[category]["items"].append({
                "name": item,
                "status": item_status(dependencies, category, item, category_controls.get(category, True), ctrl),
                "enabled": item_controls.get((category, item), {"enabled": True}).get("enabled", True),
                "manual_status": item_controls.get((category, item), {"manual_status": "AUTO"}).get("manual_status", "AUTO")
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
        history=latest_history
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
    enabled = action != "OFF"
    manual_status = "AUTO" if action == "ON" else action
    conn = get_db(); cur = conn.cursor()
    if DATABASE_URL:
        cur.execute("UPDATE item_controls SET enabled = %s, manual_status = %s WHERE category = %s AND item = %s", (enabled, manual_status, category, item))
    else:
        cur.execute("UPDATE item_controls SET enabled = ?, manual_status = ? WHERE category = ? AND item = ?", (1 if enabled else 0, manual_status, category, item))
    conn.commit(); cur.close(); conn.close()
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
            ctrl = item_controls.get((category, item), {"enabled": True, "manual_status": "AUTO"})
            menu_status[category]["items"].append({
                "name": item,
                "status": item_status(dependencies, category, item, category_controls.get(category, True), ctrl),
                "enabled": ctrl.get("enabled", True),
                "manual_status": ctrl.get("manual_status", "AUTO")
            })

    return render_template_string(KITCHEN_LIVE_HTML,
        out_items=out_items, limited_items=limited_items, available_main=available_main,
        menu_status=menu_status, menu_out_alerts=menu_out_alerts,
        menu_limited_alerts=menu_limited_alerts)


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

            ctrl = item_controls.get((category, item), {"enabled": True, "manual_status": "AUTO"})
            menu_status[category]["items"].append({
                "name": item,
                "status": item_status(dependencies, category, item, category_controls.get(category, True), ctrl),
                "enabled": item_controls.get((category, item), {"enabled": True}).get("enabled", True),
                "manual_status": item_controls.get((category, item), {"manual_status": "AUTO"}).get("manual_status", "AUTO")
            })


    return render_template_string(
        HTML,
        out_items=out_items,
        limited_items=limited_items,
        available_main=available_main,
        menu_status=menu_status,
        menu_out_alerts=menu_out_alerts,
        menu_limited_alerts=menu_limited_alerts
    )


# ==================================================
# KITCHEN HEAD HTML
# ==================================================

HTML = """
<!DOCTYPE html>
<html>
<head>
<link rel="manifest" href="/static/manifest.json">
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
.category-items{padding:0 12px 8px}.menu-item{display:flex;justify-content:space-between;gap:10px;align-items:center;padding:10px 3px;border-bottom:1px solid #eee}
.green{color:green;font-weight:bold}.yellow{color:#e69500;font-weight:bold}.red{color:red;font-weight:bold}.small{color:#777;font-size:13px}
.category-state{float:right;font-size:13px}.cat-on{color:green}.cat-off{color:red}
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
    const open=Array.from(root.querySelectorAll('details[open]')).map(d=>d.dataset.category);
    root.innerHTML=await r.text();
    open.forEach(cat=>{const d=root.querySelector('details[data-category="'+CSS.escape(cat)+'"]');if(d)d.open=true;});
  }catch(e){}
}
const kitchenRoot=document.getElementById('kitchen-live-root');
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
  const button=form.querySelector('button'); if(button)button.disabled=true;
  try{await fetch(form.action,{method:'POST',body:new FormData(form),cache:'no-store'});await refreshKitchen();}catch(err){await refreshKitchen();}
});
refreshKitchen();setInterval(refreshKitchen,1000);
</script>
</body>
</html>
"""

KITCHEN_LIVE_HTML = """

<div class="section">
<h2>🔴 OUT OF STOCK</h2>
{% if out_items or menu_out_alerts %}
{% for x in out_items %}<div class="card out"><b>❌ {{ x["name"] }}</b><form method="POST" action="/update" style="display:inline"><input type="hidden" name="ingredient" value="{{ x["name"] }}"><input type="hidden" name="status" value="AVAILABLE"><button class="back-btn">🟢 AVAILABLE</button></form>{% for g in x["affected_groups"] %}<div class="dependency-line">{{ g["category"] }} → {{ g["items"]|join(", ") }}</div>{% endfor %}</div>{% endfor %}
{% for a in menu_out_alerts %}<div class="card out"><b>🔴 {{ a["category"] }}{% if a["item"] %} → {{ a["item"] }}{% endif %}</b></div>{% endfor %}
{% else %}<p>✅ No main ingredient or menu item is OUT.</p>{% endif %}
</div>

<div class="section">
<h2>🟡 LIMITED</h2>
{% if limited_items or menu_limited_alerts %}
{% for x in limited_items %}<div class="card limited"><b>⚠️ {{ x["name"] }}</b><div class="qty-row"><form method="POST" action="/update" style="display:inline"><input type="hidden" name="ingredient" value="{{ x["name"] }}"><input type="hidden" name="status" value="LIMITED"><input type="hidden" name="qty" value="{{ x["qty"]|int - 1 }}"><button class="qty-btn">−</button></form><span class="qty-number">{{ x["qty"] }}</span><form method="POST" action="/update" style="display:inline"><input type="hidden" name="ingredient" value="{{ x["name"] }}"><input type="hidden" name="status" value="LIMITED"><input type="hidden" name="qty" value="{{ x["qty"]|int + 1 }}"><button class="qty-btn">+</button></form></div>{% for g in x["affected_groups"] %}<div class="dependency-line">{{ g["category"] }} → {{ g["items"]|join(", ") }}</div>{% endfor %}</div>{% endfor %}
{% for a in menu_limited_alerts %}<div class="card limited"><b>🟡 {{ a["category"] }} → {{ a["item"] }}</b></div>{% endfor %}
{% else %}<p>✅ No main ingredient or menu item is LIMITED.</p>{% endif %}
</div>

<div class="section">
<h2>🟢 AVAILABLE</h2>
{% for x in available_main %}<div class="card available"><b>🟢 {{ x["name"] }}</b><form method="POST" action="/update" style="display:inline"><input type="hidden" name="ingredient" value="{{ x["name"] }}"><input type="hidden" name="status" value="OUT"><button class="out-btn">🔴 OUT</button></form><form method="POST" action="/update" style="display:inline"><input type="hidden" name="ingredient" value="{{ x["name"] }}"><input type="hidden" name="status" value="LIMITED"><input type="hidden" name="qty" value="1"><button class="limited-btn">🟡 LIMITED (1)</button></form></div>{% endfor %}
</div>

<div class="section">
<h2>🥤 MENU STRUCTURE</h2>
<p class="small">All categories are collapsed by default. Changes update live every 1 second.</p>
{% for category,data in menu_status.items() %}
<details class="menu-category" data-category="{{ category }}">
<summary><span>{{ category }}</span> <span class="category-state {{ 'cat-on' if data["enabled"] else 'cat-off' }}">{{ '🟢 ON' if data["enabled"] else '🔴 OUT OF STOCK' }}</span></summary>
<div class="category-items">
<div class="control-row"><form method="POST" action="/toggle-category"><input type="hidden" name="category" value="{{ category }}"><input type="hidden" name="action" value="{{ 'OFF' if data["enabled"] else 'ON' }}"><button class="{{ 'category-off-btn' if data["enabled"] else 'category-on-btn' }}">{{ '🔴 TURN CATEGORY OFF' if data["enabled"] else '🟢 TURN CATEGORY ON' }}</button></form></div>
{% for item in data["items"] %}
<div class="menu-item">
<div><b>{{ item["name"] }}</b><br><span class="{{ 'green' if item["status"] == 'AVAILABLE' else 'yellow' if item["status"] == 'LIMITED' else 'red' }}">{{ '🟢 AVAILABLE' if item["status"] == 'AVAILABLE' else '🟡 LIMITED' if item["status"] == 'LIMITED' else '🔴 OUT OF STOCK' }}</span></div>
<div class="item-controls">
<form method="POST" action="/toggle-item" style="display:inline"><input type="hidden" name="category" value="{{ category }}"><input type="hidden" name="item" value="{{ item["name"] }}"><input type="hidden" name="action" value="ON"><button class="item-on-btn">🟢 ON</button></form>
<form method="POST" action="/toggle-item" style="display:inline"><input type="hidden" name="category" value="{{ category }}"><input type="hidden" name="item" value="{{ item["name"] }}"><input type="hidden" name="action" value="LIMITED"><button class="item-limited-btn">🟡 LIMITED</button></form>
<form method="POST" action="/toggle-item" style="display:inline"><input type="hidden" name="category" value="{{ category }}"><input type="hidden" name="item" value="{{ item["name"] }}"><input type="hidden" name="action" value="OFF"><button class="item-off-btn">🔴 OFF</button></form>
</div></div>
{% endfor %}
</div></details>
{% endfor %}
</div>

"""
STAFF_HTML = """
<!DOCTYPE html>
<html><head>
<link rel="manifest" href="/static/manifest.json">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mouzy Edappally Staff View</title>
<style>
body{font-family:Arial,sans-serif;background:#f3f5f7;margin:0;padding:15px}.section{background:white;padding:15px;margin-bottom:18px;border-radius:15px;box-shadow:0 3px 10px rgba(0,0,0,.08)}.card{background:#f8f8f8;padding:12px;margin:10px 0;border-radius:10px}.red{color:red;font-weight:bold}.yellow{color:#e69500;font-weight:bold}.green{color:green;font-weight:bold}.small{color:#777;font-size:13px}.dependency-line{margin-top:7px;padding-left:4px;color:#444;font-size:14px}.menu-category{background:#f8f8f8;margin:10px 0;border-radius:12px;overflow:hidden;border:1px solid #eee}.menu-category summary{cursor:pointer;padding:15px;font-weight:bold;font-size:17px;list-style:none}.menu-category summary::-webkit-details-marker{display:none}.menu-category summary::after{content:" ▼";float:right}.menu-category[open] summary::after{content:" ▲"}.category-items{padding:0 12px 8px}.menu-item{display:flex;justify-content:space-between;padding:10px 3px;border-bottom:1px solid #eee}.category-state{float:right;font-size:13px}.cat-on{color:green}.cat-off{color:red}
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
  const open=Array.from(root.querySelectorAll('details[open]')).map(d=>d.dataset.category);
  root.innerHTML=await r.text();
  open.forEach(cat=>{const d=root.querySelector('details[data-category="'+CSS.escape(cat)+'"]');if(d)d.open=true;});
 }catch(e){}
}
refreshStaff();setInterval(refreshStaff,1000);
</script></body></html>
"""

STAFF_LIVE_HTML = """
<div class="section"><h2 class="red">🔴 OUT OF STOCK</h2>
{% if out_items or menu_out_alerts %}{% for x in out_items %}<div class="card"><b>❌ {{ x["name"] }}</b>{% for g in x["affected_groups"] %}<div class="dependency-line">{{ g["category"] }} → {{ g["items"]|join(", ") }}</div>{% endfor %}</div>{% endfor %}{% for a in menu_out_alerts %}<div class="card"><b>🔴 {{ a["category"] }}{% if a["item"] %} → {{ a["item"] }}{% endif %}</b></div>{% endfor %}{% else %}<p>✅ Nothing is OUT.</p>{% endif %}</div>

<div class="section"><h2 class="yellow">🟡 LIMITED</h2>
{% if limited_items or menu_limited_alerts %}{% for x in limited_items %}<div class="card"><b>⚠️ {{ x["name"] }}</b>{% if x["qty"] %} | Quantity: <b>{{ x["qty"] }}</b>{% endif %}{% for g in x["affected_groups"] %}<div class="dependency-line">{{ g["category"] }} → {{ g["items"]|join(", ") }}</div>{% endfor %}</div>{% endfor %}{% for a in menu_limited_alerts %}<div class="card"><b>🟡 {{ a["category"] }} → {{ a["item"] }}</b></div>{% endfor %}{% else %}<p>✅ Nothing is LIMITED.</p>{% endif %}</div>

<div class="section"><h2>🥤 MENU STRUCTURE</h2><p class="small">Tap a category to see its items. Live updates do not reload the page.</p>
{% for category,data in menu_status.items() %}<details class="menu-category" data-category="{{ category }}"><summary><span>{{ category }}</span> <span class="category-state {{ 'cat-on' if data["enabled"] else 'cat-off' }}">{{ '🟢 ON' if data["enabled"] else '🔴 OUT OF STOCK' }}</span></summary><div class="category-items">
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