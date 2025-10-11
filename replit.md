# Smart Food Expiry Tracker

## Overview
A Flask-based web application that helps users track food items and their expiry dates to reduce food waste. The app features user authentication, food inventory management, expiry notifications, and waste analytics.

## Project Status
- **Current State**: Fully operational in Replit environment
- **Last Updated**: October 11, 2025
- **Environment**: Python 3.11 with Flask 3.0

## Features
- User registration and authentication with secure sessions
- Add and manage food items with expiry dates
- Smart notifications for items expiring within 2 days
- Waste analytics to track and categorize wasted food
- Modern, responsive UI with green theme
- Mobile and desktop friendly design

## Technical Architecture

### Backend
- **Framework**: Flask 3.0.0
- **Storage**: JSON files (users.json, food_data.json)
- **Session Management**: Flask sessions with secure secret key
- **Security**: Password hashing with Werkzeug's security utilities
- **Production Server**: Gunicorn 21.2.0

### Frontend
- **Templates**: Jinja2 HTML templates
- **Styling**: Separate CSS files for each page
- **Static Assets**: Logo and styling resources

### Data Structure
```json
{
  "username": {
    "items": [
      {
        "name": "Food item",
        "quantity": "1",
        "unit": "kg",
        "category": "vegetables",
        "expiry": "2025-10-15"
      }
    ],
    "wasted_items": [
      {
        "name": "Wasted item",
        "quantity": "1",
        "unit": "kg",
        "category": "fruits",
        "expiry": "2025-10-10",
        "wasted_date": "2025-10-11"
      }
    ]
  }
}
```

## Project Structure
```
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── gunicorn_config.py    # Gunicorn configuration for production
├── Procfile              # Process configuration
├── templates/            # HTML templates
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── add_food.html
│   ├── view_food.html
│   ├── notifications.html
│   └── waste_analytics.html
├── static/
│   ├── css/             # Page-specific stylesheets
│   └── images/          # Logo and other images
├── users.json           # User data storage
└── food_data.json       # Food items storage
```

## Configuration

### Development
- Host: 0.0.0.0
- Port: 5000
- Debug: Enabled
- Cache Control: Disabled for development

### Production (Deployment)
- Server: Gunicorn with autoscale
- Workers: 2 (configured in gunicorn_config.py)
- Port: Uses PORT environment variable (defaults to 5000)
- Deployment Type: Autoscale (stateless)
- Debug Mode: Disabled in production

## Environment Variables
- `SECRET_KEY`: Flask session secret key (auto-generated if not set)

## Recent Changes

### October 11, 2025 - Replit Migration
- Updated requirements.txt to use Flask 3.0 and modern dependencies
- Configured Flask app for Replit environment (0.0.0.0:5000)
- Added cache control headers to prevent caching issues
- Set up secure session key using environment variable
- **Security Enhancement**: Implemented password hashing using Werkzeug's security utilities
- Configured workflow for development server
- Set up Gunicorn deployment configuration with autoscale
- Fixed gunicorn_config.py to use PORT environment variable for proper deployment
- Updated .gitignore to exclude Python library paths

## User Preferences
- No specific preferences documented yet

## Routes
- `/` - Redirects to login
- `/register` - User registration
- `/login` - User login
- `/dashboard` - Main dashboard (requires authentication)
- `/add_food` - Add new food items
- `/view_food` - View all food items
- `/notifications` - View expiring items (within 2 days)
- `/waste_analytics` - View and log wasted food items
- `/delete_food/<index>` - Delete food item
- `/delete_notification/<index>` - Mark item as wasted
- `/logout` - User logout

## Development Notes
- The app uses JSON files for data persistence (users.json and food_data.json)
- Session management uses Flask's built-in session system
- Cache control headers are added to all responses to prevent caching issues in Replit's iframe environment
- The app automatically migrates old data format (list) to new format (dict with items and wasted_items)
- **Password Security**: All new user passwords are hashed using Werkzeug's generate_password_hash. Existing users with plaintext passwords will need to re-register or have their passwords migrated manually.
