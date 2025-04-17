from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime, timedelta
import json
import os
import uuid

app = Flask(__name__)

# Create data directory if it doesn't exist
if not os.path.exists('data'):
    os.makedirs('data')

# Path to the food items JSON file
FOOD_ITEMS_FILE = 'data/food_items.json'

# Initialize food items file if it doesn't exist
if not os.path.exists(FOOD_ITEMS_FILE):
    with open(FOOD_ITEMS_FILE, 'w') as f:
        json.dump([], f)

def load_food_items():
    """Load food items from JSON file"""
    try:
        with open(FOOD_ITEMS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_food_items(food_items):
    """Save food items to JSON file"""
    with open(FOOD_ITEMS_FILE, 'w') as f:
        json.dump(food_items, f, indent=4)

def calculate_days_until_expiry(expiry_date_str):
    """Calculate days until expiry"""
    today = datetime.now().date()
    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
    return (expiry_date - today).days

# Add template context processor to make functions available in templates
@app.context_processor
def utility_processor():
    return {
        'now': datetime.now,
        'calculate_days_until_expiry': calculate_days_until_expiry
    }

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/add_food')
def add_food():
    """Render the add food page"""
    return render_template('add_food.html')

@app.route('/view_food')
def view_food():
    """Render the view food page"""
    food_items = load_food_items()
    
    # Add days_left to each item
    for item in food_items:
        item['days_left'] = calculate_days_until_expiry(item['expiry_date'])
    
    return render_template('view_food.html', food_items=food_items)

@app.route('/notifications')
def notifications():
    """Render the notifications page"""
    food_items = load_food_items()
    today = datetime.now().date()
    
    # Filter items expiring within 2 days
    expiring_soon = []
    for item in food_items:
        days_left = calculate_days_until_expiry(item['expiry_date'])
        
        if 0 <= days_left <= 2:
            item['days_left'] = days_left
            expiring_soon.append(item)
    
    return render_template('notifications.html', expiring_items=expiring_soon)

@app.route('/api/add_food', methods=['POST'])
def api_add_food():
    """API endpoint to add a new food item"""
    food_items = load_food_items()
    
    new_item = {
        'id': str(uuid.uuid4()),
        'name': request.form.get('food-name'),
        'expiry_date': request.form.get('expiry-date'),
        'quantity': request.form.get('quantity'),
        'added_date': datetime.now().strftime('%Y-%m-%d')
    }
    
    food_items.append(new_item)
    save_food_items(food_items)
    
    return redirect(url_for('view_food'))

@app.route('/api/delete_food/<item_id>', methods=['POST'])
def api_delete_food(item_id):
    """API endpoint to delete a food item"""
    food_items = load_food_items()
    food_items = [item for item in food_items if item['id'] != item_id]
    save_food_items(food_items)
    
    return redirect(url_for('view_food'))

@app.route('/api/get_expiring_count')
def get_expiring_count():
    """API endpoint to get the count of items expiring soon"""
    food_items = load_food_items()
    
    # Count items expiring within 2 days
    expiring_count = 0
    for item in food_items:
        days_left = calculate_days_until_expiry(item['expiry_date'])
        
        if 0 <= days_left <= 2:
            expiring_count += 1
    
    return jsonify({'count': expiring_count})

if __name__ == '__main__':
    # Changed from debug=True to debug=False for production
    # Added host='0.0.0.0' to make it accessible from other devices if needed
    app.run(host='0.0.0.0', port=5000, debug=False)
