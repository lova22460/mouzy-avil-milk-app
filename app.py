from flask import Flask, render_template_string, request, redirect, session
from datetime import datetime
import sqlite3 #import
import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL")
KITCHEN_PIN = "2246"
DB_NAME = "mouzy.db" #DB functions


class DBWrapper:
    def __init__(self, conn, is_postgres=False):
        self.conn = conn
        self.is_postgres = is_postgres

    def execute(self, sql, params=()):
        return self.conn.cursor().execute(sql, params)

    def commit(self):
        return self.conn.commit()

    def close(self):
        return self.conn.close()


def get_db():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return DBWrapper(conn, is_postgres=True)

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return DBWrapper(conn, is_postgres=False)

def init_db():
    conn = get_db()

    if DATABASE_URL:
        # PostgreSQL
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock (
                ingredient TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                qty TEXT DEFAULT ''
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_history (
                id SERIAL PRIMARY KEY,
                item TEXT NOT NULL,
                status TEXT NOT NULL,
                qty TEXT DEFAULT '',
                time TEXT NOT NULL
            )
        """)

        for ingredient, data in stock.items():
            conn.execute("""
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock (
                ingredient TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                qty TEXT DEFAULT ''
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT NOT NULL,
                status TEXT NOT NULL,
                qty TEXT DEFAULT '',
                time TEXT NOT NULL
            )
        """)

        for ingredient, data in stock.items():
            conn.execute("""
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
    rows = conn.execute(
        "SELECT ingredient, status, qty FROM stock"
    ).fetchall()
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
    "Fruit Mix",
    "Vanilla Ice Cream"
]


# =========================
# MENU DEPENDENCIES
# =========================

menu = {

    "REGULAR AVIL MILK": {
        "Mini": [],
        "Normal": [],
        "Normal Boost": ["Boost"],
        "Fruit": ["Fruit Mix"],
        "Mango Passion": ["Mango"],
        "White": ["Vanilla Ice Cream"],
        "Special": ["Fruit Mix", "Vanilla Ice Cream"],
        "SP Boost": ["Boost", "Vanilla Ice Cream"],
    },

    "LITTLE COMBO": {
        "Little Strawberry": ["Strawberry Ice Cream", "Strawberry"],
        "Little Pista": ["Pista Ice Cream"],
        "Little Mango": ["Mango Ice Cream", "Mango"],
        "Little Arabian": ["Dates Ice Cream", "Dates"],
        "Little Butterscotch": ["Butterscotch Ice Cream"],
        "Little Choco": ["Chocolate Ice Cream", "Chocolate"],
    },

    "FUSION": {
        "Watermelon": ["Vanilla Ice Cream"],
        "Rooh Afza": ["Vanilla Ice Cream"],
        "Butterscotch": ["Butterscotch Ice Cream"],
        "Pista": ["Pista Ice Cream"],
        "Kiwi": ["Vanilla Ice Cream", "Kiwi"],
        "Chocolate": ["Chocolate Ice Cream", "Chocolate"],
        "Strawberry": ["Strawberry Ice Cream", "Strawberry"],
        "Mango": ["Mango Ice Cream", "Mango"],
        "Dates": ["Dates Ice Cream", "Dates"],
    },

    "SUPREME": {
        "Nuts": ["Butterscotch Ice Cream", "Cashew / Nuts", "Badam"],
        "Fruit Nut": ["Fruit Mix", "Vanilla Ice Cream", "Cashew / Nuts", "Badam"],
        "Royal": ["Fruit Mix", "Mango Ice Cream", "Cashew / Nuts", "Badam"],

        "Redberry Nut": [
            "Fruit Mix",
            "Vanilla Ice Cream",
            "Strawberry Ice Cream",
            "Cashew / Nuts",
            "Badam",
            "Strawberry"
        ],

        "Malgoa Nut": [
            "Mango Ice Cream",
            "Mango",
            "Cashew / Nuts",
            "Badam"
        ],

        "Pista Nut": [
            "Fruit Mix",
            "Vanilla Ice Cream",
            "Pista Ice Cream",
            "Cashew / Nuts",
            "Badam"
        ],

        "Choco Nut": [
            "Chocolate Ice Cream",
            "Chocolate",
            "Cashew / Nuts",
            "Badam"
        ],

        "Rio Nut": [
            "Fruit Mix",
            "Pista Ice Cream",
            "Mango Ice Cream",
            "Cashew / Nuts",
            "Badam"
        ],

        "Spanish Nut": [
            "Spanish Ice Cream",
            "Cashew / Nuts",
            "Badam"
        ],

        "Tender Coconut": [
            "Tender Ice Cream",
            "Cashew / Nuts",
            "Badam"
        ],

        "Blueberry Nut": [
            "Blueberry Ice Cream",
            "Cashew / Nuts",
            "Badam"
        ],

        "Arabian Nut": [
            "Dates Ice Cream",
            "Dates",
            "Cashew / Nuts",
            "Badam"
        ],

        "Dry Fruits": [
            "Mango Ice Cream",
            "Dry Fruits",
            "Cashew / Nuts",
            "Badam"
        ],

        "Special Nut": [
            "Spanish Ice Cream",
            "Cashew / Nuts",
            "Badam"
        ],
    },

    "DIET": {
        "Normal Diet": [],
        "Fruit Diet": ["Fruit Mix"],
        "Fruit Nut Diet": ["Fruit Mix", "Cashew / Nuts", "Badam"],
        "Nuts Diet": ["Cashew / Nuts", "Badam"],
        "Dry Fruits Diet": ["Cashew / Nuts", "Dry Fruits", "Badam"],
    }
}


# =========================
# MENU STATUS
# =========================

def item_status(dependencies):
    

    for ingredient in dependencies:

        if stock[ingredient]["status"] == "OUT":
            return "CLOSED"

    for ingredient in dependencies:

        if stock[ingredient]["status"] == "LIMITED":
            return "LIMITED"

    return "AVAILABLE"


# =========================
# AFFECTED MENU
# =========================

def affected_menu(ingredient):

    result = []

    for category, items in menu.items():

        for item, dependencies in items.items():

            if ingredient in dependencies:

                result.append({
                    "category": category,
                    "item": item,
                    "status": item_status(dependencies)
                })

    return result


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
    conn.execute("DELETE FROM stock_history")
    conn.commit()
    conn.close()

    return redirect("/history")

@app.route("/history")
def history():

    if not session.get("kitchen"):
        return redirect("/login")

    conn = get_db()

    rows = conn.execute("""
        SELECT item, status, qty, time
        FROM stock_history
        ORDER BY id DESC
    """).fetchall()

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



@app.route("/staff")
def staff():

    out_items = []
    limited_items = []
    available_main = []

    for ingredient in MAIN_INGREDIENTS:

        data = stock[ingredient]

        if data["status"] == "OUT":

            out_items.append({
                "name": ingredient,
                "affected": affected_menu(ingredient)
            })

        elif data["status"] == "LIMITED":

            limited_items.append({
                "name": ingredient,
                "qty": data["qty"],
                "affected": affected_menu(ingredient)
            })

        else:

            available_main.append({
                "name": ingredient
            })


    menu_status = {}

    for category, items in menu.items():

        menu_status[category] = []

        for item, dependencies in items.items():

            menu_status[category].append({
                "name": item,
                "status": item_status(dependencies)
            })

    conn = get_db()

    latest_history = conn.execute("""
        SELECT item, status, qty, time
        FROM stock_history
        ORDER BY id DESC
        LIMIT 1
    """).fetchall()

    conn.close()

    return render_template_string(
        STAFF_HTML,
        out_items=out_items,
        limited_items=limited_items,
        available_main=available_main,
        menu_status=menu_status,
        history=latest_history
    )


# =========================
# UPDATE STOCK
# =========================

@app.route("/update", methods=["POST"])
def update():

    if not session.get("kitchen"):
        return redirect("/login")

    ingredient = request.form["ingredient"]
    status = request.form["status"]
    qty = request.form.get("qty", "")

    # Save stock status to database
    conn = get_db()
    saved_qty = qty if status == "LIMITED" else ""

    if DATABASE_URL:
        conn.execute("""
            UPDATE stock
            SET status = %s, qty = %s
            WHERE ingredient = %s
        """, (status, saved_qty, ingredient))

        conn.execute("""
            INSERT INTO stock_history
            (item, status, qty, time)
            VALUES (%s, %s, %s, %s)
        """, (ingredient, status, saved_qty,
               datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")))
    else:
        conn.execute("""
            UPDATE stock
            SET status = ?, qty = ?
            WHERE ingredient = ?
        """, (status, saved_qty, ingredient))

        conn.execute("""
            INSERT INTO stock_history
            (item, status, qty, time)
            VALUES (?, ?, ?, ?)
        """, (ingredient, status, saved_qty,
               datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")))

    conn.commit()
    conn.close()

    # Reload latest stock from database
    load_stock_from_db()

    return redirect("/")


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

    for ingredient in MAIN_INGREDIENTS:

        data = stock[ingredient]

        if data["status"] == "OUT":

            out_items.append({
                "name": ingredient,
                "qty": data["qty"],
                "affected": affected_menu(ingredient)
            })

        elif data["status"] == "LIMITED":

            limited_items.append({
                "name": ingredient,
                "qty": data["qty"],
                "affected": affected_menu(ingredient)
            })

        else:

            available_main.append({
                "name": ingredient
            })


    menu_status = {}

    for category, items in menu.items():

        menu_status[category] = []

        for item, dependencies in items.items():

            menu_status[category].append({
                "name": item,
                "status": item_status(dependencies)
            })


    return render_template_string(
        HTML,
        out_items=out_items,
        limited_items=limited_items,
        available_main=available_main,
        menu_status=menu_status
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

body {
    font-family: Arial, sans-serif;
    background: #f3f5f7;
    margin: 0;
    padding: 15px;
}

h1 {
    text-align: center;
}

.section {
    background: white;
    padding: 15px;
    margin-bottom: 18px;
    border-radius: 15px;
    box-shadow: 0 3px 10px rgba(0,0,0,0.08);
}

.card {
    background: #f8f8f8;
    padding: 12px;
    margin: 10px 0;
    border-radius: 10px;
}

.available {
    border-left: 6px solid green;
}

.out {
    border-left: 6px solid red;
}

.limited {
    border-left: 6px solid orange;
}

button {
    border: none;
    padding: 8px 12px;
    border-radius: 8px;
    margin: 5px 3px;
    font-weight: bold;
}

.out-btn {
    background: #dc3545;
    color: white;
}

.limited-btn {
    background: #ffc107;
    color: black;
}

.back-btn {
    background: #28a745;
    color: white;
}

input {
    padding: 8px;
    border: 1px solid #ccc;
    border-radius: 7px;
    width: 110px;
}

.menu-item {
    display: flex;
    justify-content: space-between;
    padding: 9px 3px;
    border-bottom: 1px solid #eee;
}

.green {
    color: green;
    font-weight: bold;
}

.yellow {
    color: #e69500;
    font-weight: bold;
}

.red {
    color: red;
    font-weight: bold;
}

.small {
    color: #777;
    font-size: 13px;
}

</style>

</head>


<body>

<h1>🥤 MOUZY BANANA AVIL MILK</h1>

<div style="text-align:center; margin-bottom:15px;">
    <a href="/history"
       style="
       display:inline-block;
       background:#343a40;
       color:white;
       padding:10px 18px;
       border-radius:8px;
       text-decoration:none;
       font-weight:bold;
       ">
       📋 STOCK HISTORY
    </a>
</div>

<div style="text-align:center; margin-bottom:15px;">

<a href="/logout"
   style="
   display:inline-block;
   background:#dc3545;
   color:white;
   padding:10px 18px;
   border-radius:8px;
   text-decoration:none;
   font-weight:bold;
   ">
   🔒 BAND KARO HAAT JODKAR BINTI KARTA HUU🙏
</a>

</div>


<!-- OUT OF STOCK -->

<div class="section">

<h2>🔴 OUT OF STOCK</h2>

{% if out_items %}

{% for x in out_items %}

<div class="card out">

<b>❌ {{ x.name }}</b>

<br>

<form method="POST" action="/update">

<input type="hidden"
       name="ingredient"
       value="{{ x.name }}">

<input type="hidden"
       name="status"
       value="AVAILABLE">

<button class="back-btn">
↩️ BACK IN STOCK
</button>

</form>


{% if x.affected %}

<br>

<b>Closed Menu:</b>

{% for item in x.affected %}

{% if item.status == "CLOSED" %}

<div>
🔴 {{ item.item }}
<span class="small">
({{ item.category }})
</span>
</div>

{% endif %}

{% endfor %}

{% endif %}

</div>

{% endfor %}

{% else %}

<p>✅ No main ingredient is OUT.</p>

{% endif %}

</div>


<!-- LIMITED -->

<div class="section">

<h2>🟡 LIMITED</h2>

{% if limited_items %}

{% for x in limited_items %}

<div class="card limited">

<b>⚠️ {{ x.name }}</b>

{% if x.qty %}

<div>
Quantity: <b>{{ x.qty }}</b>
</div>

{% endif %}

<br>

<form method="POST" action="/update">

<input type="hidden"
       name="ingredient"
       value="{{ x.name }}">

<input type="hidden"
       name="status"
       value="AVAILABLE">

<button class="back-btn">
↩️ BACK IN STOCK
</button>

</form>


{% if x.affected %}

<br>

<b>Limited Menu:</b>

{% for item in x.affected %}

{% if item.status == "LIMITED" %}

<div>
🟡 {{ item.item }}
<span class="small">
({{ item.category }})
</span>
</div>

{% endif %}

{% endfor %}

{% endif %}

</div>

{% endfor %}

{% else %}

<p>✅ No main ingredient is LIMITED.</p>

{% endif %}

</div>


<!-- AVAILABLE -->

<div class="section">

<h2>🟢 AVAILABLE</h2>

<h3>Main Ingredients</h3>

{% for x in available_main %}

<div class="card available">

<b>🟢 {{ x.name }}</b>

<br>

<form method="POST"
      action="/update"
      style="display:inline;">

<input type="hidden"
       name="ingredient"
       value="{{ x.name }}">

<input type="hidden"
       name="status"
       value="OUT">

<button class="out-btn">
🔴 OUT
</button>

</form>


<form method="POST"
      action="/update"
      style="display:inline;">

<input type="hidden"
       name="ingredient"
       value="{{ x.name }}">

<input type="hidden"
       name="status"
       value="LIMITED">

<input type="text"
       name="qty"
       placeholder="Qty">

<button class="limited-btn">
🟡 LIMITED
</button>

</form>

</div>

{% endfor %}

</div>


<!-- MENU STATUS -->

<div class="section">

<h2>🥤 MENU STATUS</h2>

{% for category, items in menu_status.items() %}

<h3>{{ category }}</h3>

<div>

<h4 class="green">🟢 AVAILABLE</h4>

{% for item in items %}

{% if item.status == "AVAILABLE" %}

<div class="menu-item">

<span>{{ item.name }}</span>

<span class="green">
🟢 AVAILABLE
</span>

</div>

{% endif %}

{% endfor %}

</div>


<div>

<h4 class="yellow">🟡 LIMITED</h4>

{% for item in items %}

{% if item.status == "LIMITED" %}

<div class="menu-item">

<span>{{ item.name }}</span>

<span class="yellow">
🟡 LIMITED
</span>

</div>

{% endif %}

{% endfor %}

</div>


<div>

<h4 class="red">🔴 CLOSED</h4>

{% for item in items %}

{% if item.status == "CLOSED" %}

<div class="menu-item">

<span>{{ item.name }}</span>

<span class="red">
🔴 CLOSED
</span>

</div>

{% endif %}

{% endfor %}

</div>

{% endfor %}

</div>


</body>

</html>

"""


# ==================================================
# STAFF HTML
# ==================================================

STAFF_HTML = """

<!DOCTYPE html>

<html>

<head>
<link rel="manifest" href="/static/manifest.json">
<meta name="viewport"
      content="width=device-width, initial-scale=1">

<meta http-equiv="refresh" content="1">

<title>Mouzy Edappally Staff View</title>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<title>Mouzy Edappally Staff View</title>

<style>

body {
    font-family: Arial, sans-serif;
    background: #f3f5f7;
    margin: 0;
    padding: 15px;
}

h1 {
    text-align: center;
}

.section {
    background: white;
    padding: 15px;
    margin-bottom: 18px;
    border-radius: 15px;
    box-shadow: 0 3px 10px rgba(0,0,0,0.08);
}

.card {
    background: #f8f8f8;
    padding: 12px;
    margin: 10px 0;
    border-radius: 10px;
}

.menu-item {
    display: flex;
    justify-content: space-between;
    padding: 10px 3px;
    border-bottom: 1px solid #eee;
}

.green {
    color: green;
    font-weight: bold;
}

.yellow {
    color: #e69500;
    font-weight: bold;
}

.red {
    color: red;
    font-weight: bold;
}

.small {
    color: #777;
    font-size: 13px;
}

</style>

</head>


<body>

<div style="
    background:#fff3cd;
    padding:15px;
    margin-bottom:15px;
    border-radius:10px;
    border:2px solid #ffc107;
">
    <b>🔔 LATEST STOCK UPDATE</b><br>

    {% if history %}
        <b>{{ history[-1].item }}</b>
        → {{ history[-1].status }}

        {% if history[-1].qty %}
        | Qty: {{ history[-1].qty }}
        {% endif %}

        <br>
        🕐 {{ history[-1].time }}
    {% else %}
        No new stock update.
    {% endif %}
</div>

<h1>🥤 MOUZY EDAPPALLY STAFF VIEW</h1>


<!-- OUT -->

<div class="section">

<h2 class="red">
🔴 OUT OF STOCK
</h2>

{% if out_items %}

{% for x in out_items %}

<div class="card">

<b>❌ {{ x.name }}</b>

{% if x.affected %}

<br><br>

<b>Closed Menu:</b>

{% for item in x.affected %}

{% if item.status == "CLOSED" %}

<div>

🔴 {{ item.item }}

<span class="small">
({{ item.category }})
</span>

</div>

{% endif %}

{% endfor %}

{% endif %}

</div>

{% endfor %}

{% else %}

<p>✅ Nothing is OUT.</p>

{% endif %}

</div>


<!-- LIMITED -->

<div class="section">

<h2 class="yellow">
🟡 LIMITED
</h2>

{% if limited_items %}

{% for x in limited_items %}

<div class="card">

<b>⚠️ {{ x.name }}</b>

{% if x.qty %}

<br>

Quantity:
<b>{{ x.qty }}</b>

{% endif %}

{% if x.affected %}

<br><br>

<b>Limited Menu:</b>

{% for item in x.affected %}

{% if item.status == "LIMITED" %}

<div>

🟡 {{ item.item }}

<span class="small">
({{ item.category }})
</span>

</div>

{% endif %}

{% endfor %}

{% endif %}

</div>

{% endfor %}

{% else %}

<p>✅ Nothing is LIMITED.</p>

{% endif %}

</div>


<!-- MENU STATUS -->

<div class="section">

<h2>
🥤 MENU STATUS
</h2>

{% for category, items in menu_status.items() %}

<h3>{{ category }}</h3>

{% for item in items %}

<div class="menu-item">

<span>
{{ item.name }}
</span>


{% if item.status == "AVAILABLE" %}

<span class="green">
🟢 AVAILABLE
</span>

{% elif item.status == "LIMITED" %}

<span class="yellow">
🟡 LIMITED
</span>

{% else %}

<span class="red">
🔴 CLOSED
</span>

{% endif %}

</div>

{% endfor %}

{% endfor %}

</div>


<p style="text-align:center;color:#777;">

👀 Staff View — Only View

<br>

🔄 Refresh page to see latest status

</p>


</body>

</html>

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