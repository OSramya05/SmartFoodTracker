from flask import Flask, render_template, request, redirect, url_for, session
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'

USERS_FILE = 'users.json'
FOOD_FILE = 'food_data.json'

def load_data(file):
    if os.path.exists(file):
        with open(file, 'r') as f:
            return json.load(f)
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

@app.route('/add_food', methods=['GET', 'POST'])
def add_food():
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    food_data = load_data(FOOD_FILE)
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
        if username not in food_data:
            food_data[username] = []
        food_data[username].append(item)
        save_data(FOOD_FILE, food_data)
        return redirect('/view_food')
    return render_template('add_food.html')

@app.route('/view_food')
def view_food():
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    food_data = load_data(FOOD_FILE).get(username, [])
    return render_template('view_food.html', foods=food_data)

@app.route('/notifications')
def notifications():
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    food_data = load_data(FOOD_FILE).get(username, [])
    notifications = []
    today = datetime.today().date()
    for food in food_data:
        expiry_date = datetime.strptime(food['expiry'], '%Y-%m-%d').date()
        if (expiry_date - today).days <= 2:
            notifications.append(food)
    return render_template('notifications.html', notifications=notifications)

@app.route('/delete_food/<int:index>')
def delete_food(index):
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    food_data = load_data(FOOD_FILE)
    if username in food_data and index < len(food_data[username]):
        food_data[username].pop(index)
        save_data(FOOD_FILE, food_data)
    return redirect('/view_food')

@app.route('/delete_notification/<int:index>')
def delete_notification(index):
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    food_data = load_data(FOOD_FILE)
    today = datetime.today().date()
    if username in food_data:
        expiry_date = datetime.strptime(food_data[username][index]['expiry'], '%Y-%m-%d').date()
        if (expiry_date - today).days <= 2:
            food_data[username].pop(index)
            save_data(FOOD_FILE, food_data)
    return redirect('/notifications')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
