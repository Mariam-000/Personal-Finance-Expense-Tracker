from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ─── MODELS ───────────────────────────────────────────

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    expenses = db.relationship('Expense', backref='owner', lazy=True)
    budgets = db.relationship('Budget', backref='owner', lazy=True)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    limit = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ─── CONSTANTS ─────────────────────────────────────────

CATEGORIES = ['Food', 'Transport', 'Shopping', 'Health',
              'Education', 'Entertainment', 'Bills', 'Other']

CATEGORY_COLORS = {
    'Food': '#f472b6',
    'Transport': '#a78bfa',
    'Shopping': '#fb7185',
    'Health': '#34d399',
    'Education': '#60a5fa',
    'Entertainment': '#fbbf24',
    'Bills': '#f87171',
    'Other': '#94a3b8'
}

# ─── AUTH ROUTES ───────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return redirect(url_for('register'))
        new_user = User(
            username=username, email=email,
            password=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            flash('Invalid credentials.', 'error')
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ─── MAIN ROUTES ───────────────────────────────────────

@app.route('/')
@login_required
def dashboard():
    expenses = Expense.query.filter_by(
        user_id=current_user.id
    ).order_by(Expense.date.desc()).all()
    category_totals = {}
    for exp in expenses:
        category_totals[exp.category] = category_totals.get(exp.category, 0) + exp.amount
    monthly_totals = {}
    for exp in expenses:
        month = exp.date.strftime('%b %Y')
        monthly_totals[month] = monthly_totals.get(month, 0) + exp.amount
    total = sum(e.amount for e in expenses)
    colors = [CATEGORY_COLORS.get(cat, '#94a3b8') for cat in category_totals.keys()]
    return render_template('dashboard.html',
                           expenses=expenses,
                           categories=CATEGORIES,
                           category_totals=category_totals,
                           monthly_totals=monthly_totals,
                           total=total,
                           colors=colors)

@app.route('/add', methods=['POST'])
@login_required
def add_expense():
    title = request.form.get('title')
    amount = request.form.get('amount')
    category = request.form.get('category')
    note = request.form.get('note')
    if not title or not amount or not category:
        flash('Please fill all required fields.', 'error')
        return redirect(url_for('dashboard'))
    new_expense = Expense(
        title=title, amount=float(amount),
        category=category, note=note,
        user_id=current_user.id
    )
    db.session.add(new_expense)
    db.session.commit()
    flash('Expense added!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete/<int:id>')
@login_required
def delete_expense(id):
    expense = Expense.query.get_or_404(id)
    if expense.user_id == current_user.id:
        db.session.delete(expense)
        db.session.commit()
        flash('Expense deleted!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/statistics')
@login_required
def statistics():
    expenses = Expense.query.filter_by(
        user_id=current_user.id
    ).order_by(Expense.date.desc()).all()
    category_totals = {}
    for exp in expenses:
        category_totals[exp.category] = category_totals.get(exp.category, 0) + exp.amount
    monthly_totals = {}
    for exp in expenses:
        month = exp.date.strftime('%b %Y')
        monthly_totals[month] = monthly_totals.get(month, 0) + exp.amount
    total = sum(e.amount for e in expenses)
    avg_daily = total / 30 if total > 0 else 0
    top_category = max(category_totals, key=category_totals.get) if category_totals else 'None'
    colors = [CATEGORY_COLORS.get(cat, '#94a3b8') for cat in category_totals.keys()]
    return render_template('statistics.html',
                           expenses=expenses,
                           category_totals=category_totals,
                           monthly_totals=monthly_totals,
                           total=total,
                           avg_daily=avg_daily,
                           top_category=top_category,
                           colors=colors)

@app.route('/budget', methods=['GET', 'POST'])
@login_required
def budget():
    if request.method == 'POST':
        category = request.form.get('category')
        limit = request.form.get('limit')
        existing = Budget.query.filter_by(
            user_id=current_user.id, category=category
        ).first()
        if existing:
            existing.limit = float(limit)
        else:
            new_budget = Budget(
                category=category,
                limit=float(limit),
                user_id=current_user.id
            )
            db.session.add(new_budget)
        db.session.commit()
        flash('Budget updated!', 'success')
        return redirect(url_for('budget'))
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    category_spent = {}
    for exp in expenses:
        category_spent[exp.category] = category_spent.get(exp.category, 0) + exp.amount
    budget_data = []
    for b in budgets:
        spent = category_spent.get(b.category, 0)
        percentage = (spent / b.limit * 100) if b.limit > 0 else 0
        percentage = min(percentage, 100)
        status = 'safe' if percentage < 70 else ('warning' if percentage < 100 else 'danger')
        budget_data.append({
            'category': b.category,
            'limit': b.limit,
            'spent': spent,
            'percentage': round(percentage, 1),
            'status': status
        })
    return render_template('budget.html',
                           budget_data=budget_data,
                           categories=CATEGORIES)

@app.route('/profile')
@login_required
def profile():
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    total = sum(e.amount for e in expenses)
    total_count = len(expenses)
    top_category = {}
    for exp in expenses:
        top_category[exp.category] = top_category.get(exp.category, 0) + exp.amount
    fav = max(top_category, key=top_category.get) if top_category else 'None'
    return render_template('profile.html',
                           total=total,
                           total_count=total_count,
                           fav=fav)

# ─── RUN ───────────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)