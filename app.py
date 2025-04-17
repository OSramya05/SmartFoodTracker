from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
import json
import os
import uuid

app = Flask(__name__)

# Paths
DATA_FOLDER = 'data'
FOOD_ITEMS_FILE = os.path.join(DATA_FOLDER, 'food_items.json')

# Setup
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

if not os.path.exists(FOOD_ITEMS_FILE):
    with open(FOOD_ITEMS_FILE, 'w') as f:
        json.dump([], f)

def load_food_items():
    try:
        with open(FOOD_ITEMS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_food_items(items):
    with open(FOOD_ITEMS_FILE, 'w') as f:
        json.dump(items, f, indent=4)

def calculate_days_until_expiry(expiry_date_str):
    today = datetime.now().date()
    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
    return (expiry_date - today).days

@app.context_processor
def utility_processor():
    return {'now': datetime.now, 'calculate_days_until_expiry': calculate_days_until_expiry}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_food')
def add_food():
    return render_template('add_food.html')

@app.route('/view_food')
def view_food():
    items = load_food_items()
    for item in items:
        item['days_left'] = calculate_days_until_expiry(item['expiry_date'])
    return render_template('view_food.html', food_items=items)

@app.route('/notifications')
def notifications():
    items = load_food_items()
    expiring_soon = []
    for item in items:
        days_left = calculate_days_until_expiry(item['expiry_date'])
        if 0 <= days_left <= 2:
            item['days_left'] = days_left
            expiring_soon.append(item)
    return render_template('notifications.html', expiring_items=expiring_soon)

@app.route('/api/add_food', methods=['POST'])
def api_add_food():
    items = load_food_items()
    new_item = {
        'id': str(uuid.uuid4()),
        'name': request.form.get('name'),
        'category': request.form.get('category'),
        'expiry_date': request.form.get('expiry_date'),
        'quantity': f"{request.form.get('quantity')} {request.form.get('quantity_unit')}",
        'notes': request.form.get('notes'),
        'added_date': datetime.now().strftime('%Y-%m-%d')
    }
    items.append(new_item)
    save_food_items(items)
    return redirect(url_for('view_food'))

@app.route('/api/delete_food/<item_id>', methods=['POST'])
def api_delete_food(item_id):
    items = load_food_items()
    items = [item for item in items if item['id'] != item_id]
    save_food_items(items)
    return redirect(url_for('view_food'))

@app.route('/api/get_expiring_count')
def get_expiring_count():
    items = load_food_items()
    return jsonify({'count': sum(0 <= calculate_days_until_expiry(item['expiry_date']) <= 2 for item in items)})

if __name__ == '__main__':
    app.run(debug=True)
