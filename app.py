from flask import Flask, render_template, request, redirect, url_for, session, make_response, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
import secrets
from datetime import datetime, timedelta
from collections import Counter

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

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
        users[username] = {'password': generate_password_hash(password)}
        save_data(USERS_FILE, users)
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_data(USERS_FILE)
        username = request.form['username']
        password = request.form['password']
        
        if username in users:
            stored_password = users[username]['password']
            
            # Check if password is hashed (starts with pbkdf2:sha256: or similar)
            if stored_password.startswith(('pbkdf2:', 'scrypt:', 'argon2:')):
                # Hashed password - use check_password_hash
                if check_password_hash(stored_password, password):
                    session['username'] = username
                    return redirect('/dashboard')
            else:
                # Legacy plaintext password - check directly and migrate
                if stored_password == password:
                    # Migrate to hashed password
                    users[username]['password'] = generate_password_hash(password)
                    save_data(USERS_FILE, users)
                    session['username'] = username
                    return redirect('/dashboard')
        
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

    # Monthly grouping
    monthly_waste = {}
    total_weight_wasted = 0
    
    for item in valid_wasted_items:
        waste_date = datetime.strptime(item['wasted_date'], '%Y-%m-%d')
        month_key = waste_date.strftime('%B %Y')
        
        if month_key not in monthly_waste:
            monthly_waste[month_key] = {
                'count': 0,
                'items': [],
                'categories': Counter()
            }
        
        monthly_waste[month_key]['count'] += 1
        monthly_waste[month_key]['items'].append(item)
        monthly_waste[month_key]['categories'][item.get('category', 'Unknown')] += 1
        
        # Calculate total weight
        try:
            if item.get('unit') == 'kg':
                total_weight_wasted += float(item.get('quantity', 0))
        except (ValueError, TypeError):
            pass

    analytics = {
        'total_wasted': total_wasted,
        'waste_by_category': dict(waste_by_category),
        'monthly_waste': monthly_waste,
        'total_weight_kg': round(total_weight_wasted, 2)
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

@app.route('/ngo_finder', methods=['GET', 'POST'])
def ngo_finder():
    if 'username' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        # Handle donation request
        username = session['username']
        ngo_name = request.form.get('ngo_name')
        item_indices = request.form.getlist('items')
        
        # You can implement email/SMS notification to NGO here
        return render_template('ngo_finder.html', message=f'Donation request sent to {ngo_name}')
    
    # Sample NGOs (can be moved to database later)
    ngos = [
        {'name': 'Akshaya Patra Foundation', 'location': 'Nearby', 'contact': '+91-80-30143400', 'email': 'info@akshayapatra.org', 'address': 'Bengaluru, Karnataka'},
        {'name': 'Feeding India', 'location': '5 km away', 'contact': '+91-11-40564444', 'email': 'contact@feedingindia.org', 'address': 'Delhi NCR'},
        {'name': 'Robin Hood Army', 'location': '3 km away', 'contact': '+91-98765-43210', 'email': 'local@robinhoodarmy.com', 'address': 'Mumbai, Maharashtra'},
        {'name': 'Annakshetra Foundation', 'location': '7 km away', 'contact': '+91-22-12345678', 'email': 'help@annakshetra.org', 'address': 'Pune, Maharashtra'},
    ]
    
    # Get expiring items for donation
    username = session['username']
    all_data = load_data(FOOD_FILE)
    user_data_raw = all_data.get(username)
    
    food_data = []
    if isinstance(user_data_raw, dict):
        food_data = user_data_raw.get('items', [])
    
    expiring_items = []
    today = datetime.today().date()
    
    for index, food in enumerate(food_data):
        try:
            expiry_date = datetime.strptime(food['expiry'], '%Y-%m-%d').date()
            if (expiry_date - today).days <= 2 and (expiry_date - today).days >= 0:
                food_with_index = food.copy()
                food_with_index['index'] = index
                expiring_items.append(food_with_index)
        except (ValueError, KeyError):
            continue
    
    return render_template('ngo_finder.html', ngos=ngos, expiring_items=expiring_items)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/login')

# IoT API Endpoints for Hardware Integration
@app.route('/api/update_weight', methods=['POST'])
def update_weight():
    try:
        data = request.get_json()
        username = data.get('username')
        item_name = data.get('item_name')
        new_weight = float(data.get('weight', 0))
        
        if not username or not item_name:
            return jsonify({'error': 'Missing required fields'}), 400
        
        all_data = load_data(FOOD_FILE)
        user_data = all_data.get(username)
        
        if isinstance(user_data, dict) and 'items' in user_data:
            for item in user_data['items']:
                if item['name'].lower() == item_name.lower() and item['unit'] == 'kg':
                    item['quantity'] = str(new_weight)
                    save_data(FOOD_FILE, all_data)
                    return jsonify({'success': True, 'message': f'Updated {item_name} to {new_weight}kg'}), 200
            
            return jsonify({'error': 'Item not found'}), 404
        
        return jsonify({'error': 'User not found or invalid data format'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_food_items', methods=['GET'])
def get_food_items():
    try:
        username = request.args.get('username')
        
        if not username:
            return jsonify({'error': 'Username required'}), 400
        
        all_data = load_data(FOOD_FILE)
        user_data = all_data.get(username)
        
        if isinstance(user_data, dict):
            items = user_data.get('items', [])
            return jsonify({'success': True, 'items': items}), 200
        
        return jsonify({'success': True, 'items': []}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sensor_data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.get_json()
        username = data.get('username')
        sensor_readings = {
            'temperature': data.get('temperature'),
            'humidity': data.get('humidity'),
            'methane': data.get('methane'),
            'air_quality': data.get('air_quality'),
            'timestamp': datetime.now().isoformat()
        }
        
        # Store sensor data (you can extend this to save to a separate file)
        return jsonify({'success': True, 'message': 'Sensor data received'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
