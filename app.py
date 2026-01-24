from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import requests
import os

app = Flask(__name__)

# --- CONFIGURATION ---
app.config['SECRET_KEY'] = 'dev_key_123' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

SERP_API_KEY = os.getenv("SERP_API_KEY")

# --- DATABASE MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    history = db.relationship('SearchHistory', backref='user', lazy=True)

class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # RENAMED 'query' to 'search_query' to fix the error
    search_query = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Create Tables
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- HELPER FUNCTIONS ---
def get_logo(store):
    if not store: return "default.png"
    s = store.lower()
    if "amazon" in s: return "amazon.png"
    if "flipkart" in s: return "flipkart.png"
    if "reliance" in s: return "reliance.png"
    return "default.png"

def extract_price(p):
    if not p: return 0
    try:
        clean_price = p.replace("₹", "").replace(",", "").strip()
        return int(float(clean_price.split()[0])) 
    except:
        return 0

# --- ROUTES ---

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == "POST":
        action = request.form.get('action')
        
        # REGISTER
        if action == 'register':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            
            # Check for existing users to prevent crashes
            user_email = User.query.filter_by(email=email).first()
            user_name = User.query.filter_by(username=username).first()

            if user_email:
                flash('Email already exists.', 'error')
            elif user_name:
                flash('Username already exists.', 'error')
            else:
                hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
                new_user = User(username=username, email=email, password=hashed_pw)
                db.session.add(new_user)
                db.session.commit()
                flash('Account created! Please sign in.', 'success')
                return redirect(url_for('login'))
                
        # LOGIN
        elif action == 'login':
            username = request.form.get('username')
            password = request.form.get('password')
            user = User.query.filter_by(username=username).first()
            
            if user and check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('index'))
            else:
                flash('Invalid credentials.', 'error')

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/")
@login_required
def index():
    return render_template("index.html", user=current_user)

@app.route("/account")
@login_required
def account():
    # Fetch history
    user_history = SearchHistory.query.filter_by(user_id=current_user.id).order_by(SearchHistory.timestamp.desc()).all()
    return render_template("account.html", user=current_user, history=user_history)

@app.route("/update_profile", methods=["POST"])
@login_required
def update_profile():
    new_username = request.form.get("username")
    new_email = request.form.get("email")
    new_password = request.form.get("password")

    if new_username: current_user.username = new_username
    if new_email: current_user.email = new_email
    if new_password: 
        current_user.password = generate_password_hash(new_password, method='pbkdf2:sha256')

    try:
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    except:
        flash('Error updating profile. Username taken.', 'error')
    
    return redirect(url_for('account'))

@app.route("/search", methods=["POST"])
@login_required
def search():
    product = request.form.get("product")
    sort_order = request.form.get("sort")

    # Save History (Using the new column name 'search_query')
    if product:
        new_search = SearchHistory(user_id=current_user.id, search_query=product)
        db.session.add(new_search)
        db.session.commit()

    params = {
        "engine": "google_shopping",
        "q": product,
        "hl": "en",
        "gl": "in",
        "api_key": SERP_API_KEY
    }

    try:
        response = requests.get("https://serpapi.com/search", params=params)
        data = response.json()
    except Exception as e:
        print(f"Error: {e}")
        return render_template("index.html", error="Failed to fetch results", user=current_user)

    results = []
    shopping_results = data.get("shopping_results", [])

    for item in shopping_results:
        store = item.get("source", "Unknown")
        price = item.get("price", "N/A")
        link = item.get("link")
        
        if not link: link = item.get("product_link")
        if link and link.startswith("/"): link = f"https://www.google.co.in{link}"

        results.append({
            "title": item.get("title"),
            "store": store,
            "price": price,
            "price_value": extract_price(price),
            "link": link,
            "thumbnail": item.get("thumbnail"),
            "logo": get_logo(store)
        })

    results.sort(key=lambda x: x["price_value"], reverse=(sort_order == "high"))

    return render_template("results.html", product=product, results=results, sort_order=sort_order, user=current_user)

if __name__ == "__main__":
    app.run(debug=True)