from flask import Flask, render_template_string, request, redirect

app = Flask(__name__)

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
    "Dry Fruits"
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
            "Fruit Mix", "Vanilla Ice Cream", "Strawberry Ice Cream",
            "Cashew / Nuts", "Badam", "Strawberry"
        ],
        "Malgoa Nut": [
            "Mango Ice Cream", "Mango", "Cashew / Nuts", "Badam"
        ],
        "Pista Nut": [
            "Fruit Mix", "Vanilla Ice Cream", "Pista Ice Cream",
            "Cashew / Nuts", "Badam"
        ],
        "Choco Nut": [
            "Chocolate Ice Cream", "Chocolate",
            "Cashew / Nuts", "Badam"
        ],
        "Rio Nut": [
            "Fruit Mix", "Pista Ice Cream", "Mango Ice Cream",
            "Cashew / Nuts", "Badam"
        ],
        "Spanish Nut": [
            "Spanish Ice Cream", "Cashew / Nuts", "Badam"
        ],
        "Tender Coconut": [
            "Tender Ice Cream", "Cashew / Nuts", "Badam"
        ],
        "Blueberry Nut": [
            "Blueberry Ice Cream", "Cashew / Nuts", "Badam"
        ],
        "Arabian Nut": [
            "Dates Ice Cream", "Dates", "Cashew / Nuts", "Badam"
        ],
        "Dry Fruits": [
            "Mango Ice Cream", "Dry Fruits",
            "Cashew / Nuts", "Badam"
        ],
        "Special Nut": [
            "Spanish Ice Cream", "Cashew / Nuts", "Badam"
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


# =========================
# UPDATE STOCK
# =========================

@app.route("/update", methods=["POST"])
def update():

    ingredient = request.form["ingredient"]
    status = request.form["status"]
    qty = request.form.get("qty", "")

    if ingredient in stock:

        stock[ingredient]["status"] = status

        if status == "LIMITED":
            stock[ingredient]["qty"] = qty
        else:
            stock[ingredient]["qty"] = ""

    return redirect("/")


# =========================
# HOME
# =========================

@app.route("/")
def home():

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


# =========================
# HTML
# =========================

HTML = """

<!DOCTYPE html>

<html>

<head>

<meta name="viewport" content="width=device-width, initial-scale=1">

<title>Mouzy Avil Milk</title>

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

<h1>🥤 MOUZY AVIL MILK</h1>


<!-- ==================================================
     1. OUT OF STOCK
     ================================================== -->

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


<!-- ==================================================
     2. LIMITED
     ================================================== -->

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


<!-- ==================================================
     3. AVAILABLE
     ================================================== -->

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


<!-- ==================================================
     4. MENU STATUS
     ================================================== -->

<div class="section">

    <h2>🥤 MENU STATUS</h2>

    {% for category, items in menu_status.items() %}

        <h3>{{ category }}</h3>

        <!-- AVAILABLE -->
        <div class="status-group">
            <h4 class="green">🟢 AVAILABLE</h4>

            {% for item in items %}
                {% if item.status == "AVAILABLE" %}
                    <div class="menu-item">
                        <span>{{ item.name }}</span>
                        <span class="green">🟢 AVAILABLE</span>
                    </div>
                {% endif %}
            {% endfor %}
        </div>

        <!-- LIMITED -->
        <div class="status-group">
            <h4 class="yellow">🟡 LIMITED</h4>

            {% for item in items %}
                {% if item.status == "LIMITED" %}
                    <div class="menu-item">
                        <span>{{ item.name }}</span>
                        <span class="yellow">🟡 LIMITED</span>
                    </div>
                {% endif %}
            {% endfor %}
        </div>

        <!-- CLOSED -->
        <div class="status-group">
            <h4 class="red">🔴 CLOSED</h4>

            {% for item in items %}
                {% if item.status == "CLOSED" %}
                    <div class="menu-item">
                        <span>{{ item.name }}</span>
                        <span class="red">🔴 CLOSED</span>
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
# RUN
# ==================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)