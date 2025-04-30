from flask import Flask, render_template, request, redirect, url_for, session
import json
import os
from datetime import datetime, timedelta
from collections import Counter

app = Flask(__name__)
app.secret_key = 'your_secret_key'

USERS_FILE = 'users.json'
FOOD_FILE = 'food_data.json'

def load_data(file):
    if os.path.exists(file):
        try:
            with open(file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {} # Return empty dict if file is empty or invalid JSON
    return {}

def save_data(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/')
def home():
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = load_data(USERS_FILE)
        username = request.form['username']
        password = request.form['password']
        if username in users:
            return "Username already exists!"
        users[username] = {'password': password}
        save_data(USERS_FILE, users)
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_data(USERS_FILE)
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            session['username'] = username
            return redirect('/dashboard')
        else:
            return "Invalid credentials!"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/login')
    return render_template('dashboard.html')

@app.route('/notifications')
def notifications():
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    all_data = load_data(FOOD_FILE)
    user_data_raw = all_data.get(username)

    food_data = []
    if isinstance(user_data_raw, dict):
        food_data = user_data_raw.get('items', [])
    elif isinstance(user_data_raw, list): # Handle old format
        food_data = user_data_raw
        # Optional: Migrate data on read
        # all_data[username] = {'items': user_data_raw, 'wasted_items': []}
        # save_data(FOOD_FILE, all_data)

    notifications_list = [] # Renamed to avoid conflict
    today = datetime.today().date()
    # Create a list of tuples (food_item, original_index)
    indexed_food_data = list(enumerate(food_data))

    for index, food in indexed_food_data:
        try:
            expiry_date = datetime.strptime(food['expiry'], '%Y-%m-%d').date()
            # Notify if expiry is today, tomorrow, or has passed
            if (expiry_date - today).days <= 2:
                # Add original index to the notification item
                food_with_index = food.copy()
                food_with_index['original_index'] = index
                notifications_list.append(food_with_index)
        except (ValueError, KeyError):
            # Handle potential errors if expiry date format is wrong or key missing
            continue # Skip this item

    # Sort notifications by expiry date (soonest first)
    notifications_list.sort(key=lambda x: datetime.strptime(x['expiry'], '%Y-%m-%d').date())

    return render_template('notifications.html', notifications=notifications_list)


@app.route('/delete_food/<int:index>')
def delete_food(index):
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    all_data = load_data(FOOD_FILE)
    user_data = all_data.get(username)

    # Only modify if user_data is in the new dict format and index is valid
    if isinstance(user_data, dict) and 'items' in user_data and index < len(user_data['items']):
        user_data['items'].pop(index)
        save_data(FOOD_FILE, all_data)
    # If old list format, maybe delete? For now, only support new format deletion via this route.
    # Consider adding logic here if deletion from old list format is needed.

    return redirect('/view_food')

# Modified delete_notification to log waste
@app.route('/delete_notification/<int:original_index>')
def delete_notification(original_index):
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    all_data = load_data(FOOD_FILE)
    user_data = all_data.get(username)

    # Only modify if user_data is in the new dict format and index is valid
    if isinstance(user_data, dict) and 'items' in user_data and original_index < len(user_data['items']):
        # Get the item to be deleted/wasted
        wasted_item = user_data['items'].pop(original_index)
        wasted_item['wasted_date'] = datetime.today().strftime('%Y-%m-%d')

        # Initialize wasted_items list if it doesn't exist
        if 'wasted_items' not in user_data:
            user_data['wasted_items'] = []

        # Add to wasted items list
        user_data['wasted_items'].append(wasted_item)
        save_data(FOOD_FILE, all_data)
    # If old list format, cannot mark as wasted.

    return redirect('/notifications')

# New route for Waste Analytics
@app.route('/waste_analytics', methods=['GET', 'POST'])
def waste_analytics():
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    all_data = load_data(FOOD_FILE)
    user_data_raw = all_data.get(username) # Get raw data first

    user_data = {}
    wasted_items = []

    # Check if data is in the new dictionary format
    if isinstance(user_data_raw, dict):
        user_data = user_data_raw
        wasted_items = user_data.get('wasted_items', [])
    # If it's a list (old format) or None, wasted_items remains []

    if request.method == 'POST':
        # Ensure user_data is a dict before modifying
        if not isinstance(user_data_raw, dict):
             # If old format or new user, initialize structure
             user_data = {'items': user_data_raw if isinstance(user_data_raw, list) else [], 'wasted_items': []}
             all_data[username] = user_data # Add/update in all_data
        elif 'wasted_items' not in user_data: # Ensure wasted_items list exists
             user_data['wasted_items'] = []

        # Manually log wasted food
        name = request.form['name']
        quantity = request.form.get('quantity', 'N/A') # Use get with default
        unit = request.form.get('unit', '')
        category = request.form['category']
        # Use current date if not provided
        wasted_date = request.form.get('wasted_date') or datetime.today().strftime('%Y-%m-%d')

        manual_waste = {
            'name': name,
            'quantity': quantity,
            'unit': unit,
            'category': category,
            'wasted_date': wasted_date,
            'expiry': 'N/A' # Expiry might not be known for manually added waste
        }

        user_data['wasted_items'].append(manual_waste)
        # all_data[username] is already updated if it was initialized
        save_data(FOOD_FILE, all_data)
        return redirect('/waste_analytics') # Redirect to refresh page

    # Calculate analytics for GET request (using wasted_items derived earlier)
    total_wasted = len(wasted_items)
    waste_by_category = Counter(item['category'] for item in wasted_items if 'category' in item)

    # Sort wasted items by date, most recent first
    # Add check for date format before sorting
    valid_wasted_items = []
    for item in wasted_items:
        try:
            datetime.strptime(item['wasted_date'], '%Y-%m-%d')
            valid_wasted_items.append(item)
        except (ValueError, KeyError):
            continue # Skip items with invalid or missing date

    valid_wasted_items.sort(key=lambda x: datetime.strptime(x['wasted_date'], '%Y-%m-%d'), reverse=True)


    analytics = {
        'total_wasted': total_wasted,
        'waste_by_category': dict(waste_by_category)
    }
    # Pass the sorted, valid items to the template
    return render_template('waste_analytics.html', analytics=analytics, wasted_items=valid_wasted_items)


# Modify add_food and view_food to use the new data structure
@app.route('/add_food', methods=['GET', 'POST'])
def add_food():
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    all_data = load_data(FOOD_FILE)
    user_data_raw = all_data.get(username)

    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        unit = request.form['unit']
        category = request.form['category']
        expiry = request.form['expiry']
        item = {
            'name': name,
            'quantity': quantity,
            'unit': unit,
            'category': category,
            'expiry': expiry
        }

        # Check if user exists and data format
        if isinstance(user_data_raw, dict):
            if 'items' not in user_data_raw:
                 user_data_raw['items'] = []
            user_data_raw['items'].append(item)
        elif isinstance(user_data_raw, list): # Old format
             # Migrate to new format
             all_data[username] = {'items': user_data_raw + [item], 'wasted_items': []}
        else: # New user
             all_data[username] = {'items': [item], 'wasted_items': []}

        save_data(FOOD_FILE, all_data)
        return redirect('/view_food')
    return render_template('add_food.html')

@app.route('/view_food')
def view_food():
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    all_data = load_data(FOOD_FILE)
    user_data_raw = all_data.get(username)

    food_items = []
    if isinstance(user_data_raw, dict):
        food_items = user_data_raw.get('items', [])
    elif isinstance(user_data_raw, list): # Handle old format
        food_items = user_data_raw
        # Optional: Migrate data on read
        # all_data[username] = {'items': user_data_raw, 'wasted_items': []}
        # save_data(FOOD_FILE, all_data)

    return render_template('view_food.html', foods=food_items)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
