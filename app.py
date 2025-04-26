# app.py - Main application file

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///money_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Add context processor to make now() available in templates
@app.context_processor
def utility_processor():
    return {'now': datetime.now}


# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    expenses = db.relationship('Expense', backref='user', lazy=True)
    incomes = db.relationship('Income', backref='user', lazy=True)
    savings_goals = db.relationship('SavingsGoal', backref='user', lazy=True)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class SavingsGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, nullable=False, default=0)
    target_date = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    year = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    @property
    def period_name(self):
        import calendar
        return f"{calendar.month_name[self.month]} {self.year}"


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'expense' or 'income'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationship with User model
    user = db.relationship('User', backref=db.backref('categories', lazy=True))

    def __repr__(self):
        return f"<Category {self.name} ({self.type})>"

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        user_exists = User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first()

        if user_exists:
            flash('Username or email already exists!')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        except:
            flash('Something went wrong. Please try again.')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out.')
    return redirect(url_for('index'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Get period filter
    period = request.args.get('period', 'this_month')
    custom_start_date = request.args.get('start_date')
    custom_end_date = request.args.get('end_date')

    # Determine date range based on period
    today = datetime.now()
    start_date = None
    end_date = None
    period_label = "This Month"

    if period == 'this_month':
        start_date = datetime(today.year, today.month, 1)
        if today.month == 12:
            end_date = datetime(today.year + 1, 1, 1)
        else:
            end_date = datetime(today.year, today.month + 1, 1)
        period_label = f"{today.strftime('%B %Y')}"
    elif period == 'last_month':
        if today.month == 1:
            start_date = datetime(today.year - 1, 12, 1)
            end_date = datetime(today.year, 1, 1)
            period_label = f"December {today.year - 1}"
        else:
            start_date = datetime(today.year, today.month - 1, 1)
            end_date = datetime(today.year, today.month, 1)
            period_label = f"{start_date.strftime('%B %Y')}"
    elif period == '3months':
        if today.month > 3:
            start_date = datetime(today.year, today.month - 3, 1)
        else:
            start_date = datetime(today.year - 1, 12 - (3 - today.month), 1)
        end_date = datetime(today.year, today.month, today.day + 1)
        period_label = f"Last 3 Months"
    elif period == '6months':
        if today.month > 6:
            start_date = datetime(today.year, today.month - 6, 1)
        else:
            start_date = datetime(today.year - 1, 12 - (6 - today.month), 1)
        end_date = datetime(today.year, today.month, today.day + 1)
        period_label = f"Last 6 Months"
    elif period == 'year':
        start_date = datetime(today.year, 1, 1)
        end_date = datetime(today.year + 1, 1, 1)
        period_label = f"Year {today.year}"
    elif period == 'all':
        # Using a very old start date for "all time"
        start_date = datetime(2000, 1, 1)
        end_date = datetime(today.year, today.month, today.day + 1)
        period_label = "All Time"

    # Override with custom dates if provided
    if custom_start_date:
        start_date = datetime.strptime(custom_start_date, '%Y-%m-%d')
        period_label = f"Custom Period"
    if custom_end_date:
        end_date = datetime.strptime(custom_end_date, '%Y-%m-%d') + timedelta(days=1)  # Include the end date
        period_label = f"Custom Period"

    # Query expenses and incomes for the selected period
    expenses = Expense.query.filter_by(user_id=user_id).filter(
        Expense.date >= start_date,
        Expense.date < end_date
    ).order_by(Expense.date.desc()).all()

    incomes = Income.query.filter_by(user_id=user_id).filter(
        Income.date >= start_date,
        Income.date < end_date
    ).order_by(Income.date.desc()).all()

    # Calculate summary figures
    total_expense = sum(expense.amount for expense in expenses)
    total_income = sum(income.amount for income in incomes)
    balance = total_income - total_expense

    # Calculate savings rate (if income > 0)
    savings_rate = (balance / total_income * 100) if total_income > 0 else 0

    # Get expense by categories
    expense_categories = {}
    for expense in expenses:
        if expense.category in expense_categories:
            expense_categories[expense.category] += expense.amount
        else:
            expense_categories[expense.category] = expense.amount

    # Get savings goals
    savings_goals = SavingsGoal.query.filter_by(user_id=user_id).all()

    # Prepare data for time series chart (monthly data)
    # Group expenses and incomes by month
    monthly_expenses = {}
    monthly_incomes = {}

    # Use at most 12 data points for the chart
    chart_start_date = max(start_date, datetime(today.year - 1, today.month, 1))

    current = chart_start_date
    while current < end_date:
        month_key = current.strftime('%Y-%m')
        monthly_expenses[month_key] = 0
        monthly_incomes[month_key] = 0

        # Move to next month
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)

    # Fill in actual values
    for expense in expenses:
        month_key = expense.date.strftime('%Y-%m')
        if month_key in monthly_expenses:
            monthly_expenses[month_key] += expense.amount

    for income in incomes:
        month_key = income.date.strftime('%Y-%m')
        if month_key in monthly_incomes:
            monthly_incomes[month_key] += income.amount

    # Prepare chart data
    time_labels = []
    expense_data = []
    income_data = []

    for month_key in sorted(monthly_expenses.keys()):
        # Format as "Jan 2023", "Feb 2023", etc.
        year, month = month_key.split('-')
        month_name = datetime(int(year), int(month), 1).strftime('%b %Y')
        time_labels.append(month_name)
        expense_data.append(monthly_expenses[month_key])
        income_data.append(monthly_incomes[month_key])

    # Get budget data if available
    budget_summary = {}

    # Check if Budget model exists
    try:
        # Get current month's budgets
        current_month = today.month
        current_year = today.year

        budgets = Budget.query.filter_by(
            user_id=user_id,
            month=current_month,
            year=current_year
        ).all()

        # Get current month's expenses by category
        month_start = datetime(current_year, current_month, 1)
        if current_month == 12:
            month_end = datetime(current_year + 1, 1, 1)
        else:
            month_end = datetime(current_year, current_month + 1, 1)

        month_expenses = Expense.query.filter_by(user_id=user_id).filter(
            Expense.date >= month_start,
            Expense.date < month_end
        ).all()

        # Calculate spending by category
        category_spending = {}
        for expense in month_expenses:
            if expense.category in category_spending:
                category_spending[expense.category] += expense.amount
            else:
                category_spending[expense.category] = expense.amount

        # Create budget summary
        for budget in budgets:
            actual_spent = category_spending.get(budget.category, 0)
            budget_summary[budget.category] = {
                'budget': budget.amount,
                'actual': actual_spent
            }
    except:
        # Budget model might not exist yet
        budget_summary = {}

    return render_template('dashboard.html',
                           expenses=expenses[:5],  # Limit to 5 recent transactions
                           incomes=incomes[:5],  # Limit to 5 recent transactions
                           savings_goals=savings_goals,
                           total_expense=total_expense,
                           total_income=total_income,
                           balance=balance,
                           expense_categories=expense_categories,
                           period=period,
                           custom_start_date=custom_start_date,
                           custom_end_date=custom_end_date,
                           period_label=period_label,
                           savings_rate=savings_rate,
                           time_labels=time_labels,
                           expense_data=expense_data,
                           income_data=income_data,
                           budget_summary=budget_summary)


# Expense routes
@app.route('/expenses')
def expenses():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Get filter parameters
    category = request.args.get('category')
    min_amount = request.args.get('min_amount', type=float)
    max_amount = request.args.get('max_amount', type=float)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search_term = request.args.get('search')

    # Base query
    query = Expense.query.filter_by(user_id=user_id)

    # Apply filters if provided
    if category and category != 'all':
        query = query.filter_by(category=category)
    if min_amount:
        query = query.filter(Expense.amount >= min_amount)
    if max_amount:
        query = query.filter(Expense.amount <= max_amount)
    if start_date:
        query = query.filter(Expense.date >= datetime.strptime(start_date, "%Y-%m-%d"))
    if end_date:
        query = query.filter(Expense.date <= datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1))
    if search_term:
        query = query.filter(Expense.description.contains(search_term))

    # Get categories for filter dropdown
    categories = db.session.query(Expense.category).filter_by(user_id=user_id).distinct().all()
    categories = [cat[0] for cat in categories]

    # Execute query with order
    expenses = query.order_by(Expense.date.desc()).all()

    return render_template('expenses.html',
                           expenses=expenses,
                           categories=categories,
                           filter_category=category,
                           filter_min_amount=min_amount,
                           filter_max_amount=max_amount,
                           filter_start_date=start_date,
                           filter_end_date=end_date,
                           filter_search=search_term)


@app.route('/expenses/add', methods=['GET', 'POST'])
def add_expense():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        amount = float(request.form['amount'])
        category = request.form['category']
        description = request.form['description']
        date_str = request.form['date']
        date = datetime.strptime(date_str, '%Y-%m-%d')

        new_expense = Expense(
            amount=amount,
            category=category,
            description=description,
            date=date,
            user_id=session['user_id']
        )

        try:
            db.session.add(new_expense)
            db.session.commit()
            flash('Expense added successfully!')
            return redirect(url_for('expenses'))
        except:
            flash('Something went wrong. Please try again.')

    return render_template('add_expense.html')


@app.route('/expenses/edit/<int:id>', methods=['GET', 'POST'])
def edit_expense(id):
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    expense = Expense.query.get_or_404(id)

    # Make sure the expense belongs to the logged-in user
    if expense.user_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('expenses'))

    if request.method == 'POST':
        expense.amount = float(request.form['amount'])
        expense.category = request.form['category']
        expense.description = request.form['description']
        date_str = request.form['date']
        expense.date = datetime.strptime(date_str, '%Y-%m-%d')

        try:
            db.session.commit()
            flash('Expense updated successfully!')
            return redirect(url_for('expenses'))
        except:
            flash('Something went wrong. Please try again.')

    return render_template('edit_expense.html', expense=expense)


@app.route('/expenses/delete/<int:id>')
def delete_expense(id):
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    expense = Expense.query.get_or_404(id)

    # Make sure the expense belongs to the logged-in user
    if expense.user_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('expenses'))

    try:
        db.session.delete(expense)
        db.session.commit()
        flash('Expense deleted successfully!')
    except:
        flash('Something went wrong. Please try again.')

    return redirect(url_for('expenses'))


# Income routes
@app.route('/incomes')
def incomes():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    user_id = session['user_id']
    incomes = Income.query.filter_by(user_id=user_id).order_by(Income.date.desc()).all()
    return render_template('incomes.html', incomes=incomes)


@app.route('/incomes/add', methods=['GET', 'POST'])
def add_income():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        amount = float(request.form['amount'])
        source = request.form['source']
        description = request.form['description']
        date_str = request.form['date']
        date = datetime.strptime(date_str, '%Y-%m-%d')

        new_income = Income(
            amount=amount,
            source=source,
            description=description,
            date=date,
            user_id=session['user_id']
        )

        try:
            db.session.add(new_income)
            db.session.commit()
            flash('Income added successfully!')
            return redirect(url_for('incomes'))
        except:
            flash('Something went wrong. Please try again.')

    return render_template('add_income.html')


@app.route('/incomes/edit/<int:id>', methods=['GET', 'POST'])
def edit_income(id):
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    income = Income.query.get_or_404(id)

    # Make sure the income entry belongs to the logged-in user
    if income.user_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('incomes'))

    if request.method == 'POST':
        income.amount = float(request.form['amount'])
        income.source = request.form['source']
        income.description = request.form['description']
        date_str = request.form['date']
        income.date = datetime.strptime(date_str, '%Y-%m-%d')

        try:
            db.session.commit()
            flash('Income updated successfully!')
            return redirect(url_for('incomes'))
        except:
            flash('Something went wrong. Please try again.')

    return render_template('edit_income.html', income=income)


@app.route('/incomes/delete/<int:id>')
def delete_income(id):
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    income = Income.query.get_or_404(id)

    # Make sure the income entry belongs to the logged-in user
    if income.user_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('incomes'))

    try:
        db.session.delete(income)
        db.session.commit()
        flash('Income deleted successfully!')
    except:
        flash('Something went wrong. Please try again.')

    return redirect(url_for('incomes'))


# Savings Goals routes
@app.route('/savings')
def savings():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    user_id = session['user_id']
    savings_goals = SavingsGoal.query.filter_by(user_id=user_id).all()
    return render_template('savings.html', savings_goals=savings_goals)


@app.route('/savings/add', methods=['GET', 'POST'])
def add_savings_goal():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        target_amount = float(request.form['target_amount'])
        current_amount = float(request.form['current_amount'])
        target_date_str = request.form['target_date']
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d') if target_date_str else None

        new_savings_goal = SavingsGoal(
            name=name,
            target_amount=target_amount,
            current_amount=current_amount,
            target_date=target_date,
            user_id=session['user_id']
        )

        try:
            db.session.add(new_savings_goal)
            db.session.commit()
            flash('Savings goal added successfully!')
            return redirect(url_for('savings'))
        except:
            flash('Something went wrong. Please try again.')

    return render_template('add_savings_goal.html')


@app.route('/savings/update/<int:id>', methods=['POST'])
def update_savings_progress(id):
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    savings_goal = SavingsGoal.query.get_or_404(id)

    # Make sure the savings goal belongs to the logged-in user
    if savings_goal.user_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('savings'))

    if request.method == 'POST':
        amount = float(request.form['amount'])
        savings_goal.current_amount += amount

        try:
            db.session.commit()
            flash('Savings progress updated successfully!')
        except:
            flash('Something went wrong. Please try again.')

    return redirect(url_for('savings'))


@app.route('/budgets')
def budgets():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Get current month and year
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Get requested month and year, defaulting to current
    month = request.args.get('month', current_month, type=int)
    year = request.args.get('year', current_year, type=int)

    # Get budgets for selected month/year
    budgets = Budget.query.filter_by(
        user_id=user_id,
        month=month,
        year=year
    ).all()

    # Get actual spending for each category
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    # Get all expenses for this period
    period_expenses = Expense.query.filter_by(user_id=user_id).filter(
        Expense.date >= start_date,
        Expense.date < end_date
    ).all()

    # Calculate spending by category
    category_spending = {}
    for expense in period_expenses:
        if expense.category in category_spending:
            category_spending[expense.category] += expense.amount
        else:
            category_spending[expense.category] = expense.amount

    # Predefined expense categories (get unique categories from expenses)
    all_categories = set([e.category for e in Expense.query.filter_by(user_id=user_id).distinct(Expense.category)])
    if not all_categories:
        all_categories = {"Food", "Transportation", "Housing", "Utilities", "Entertainment",
                          "Shopping", "Healthcare", "Education", "Other"}

    return render_template('budgets.html',
                           budgets=budgets,
                           category_spending=category_spending,
                           all_categories=all_categories,
                           selected_month=month,
                           selected_year=year,
                           current_month=current_month,
                           current_year=current_year)


@app.route('/budgets/set', methods=['POST'])
def set_budget():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    user_id = session['user_id']
    category = request.form['category']
    amount = float(request.form['amount'])
    month = int(request.form['month'])
    year = int(request.form['year'])

    # Check if a budget for this category/month/year already exists
    existing_budget = Budget.query.filter_by(
        user_id=user_id,
        category=category,
        month=month,
        year=year
    ).first()

    if existing_budget:
        # Update existing budget
        existing_budget.amount = amount
        flash(f'Budget for {category} updated successfully!')
    else:
        # Create new budget
        new_budget = Budget(
            category=category,
            amount=amount,
            month=month,
            year=year,
            user_id=user_id
        )
        db.session.add(new_budget)
        flash(f'Budget for {category} set successfully!')

    try:
        db.session.commit()
    except:
        db.session.rollback()
        flash('Something went wrong. Please try again.')

    return redirect(url_for('budgets', month=month, year=year))


@app.route('/budgets/delete/<int:id>')
def delete_budget(id):
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    budget = Budget.query.get_or_404(id)

    # Ensure the budget belongs to current user
    if budget.user_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('budgets'))

    # Save month/year for redirect
    month = budget.month
    year = budget.year

    try:
        db.session.delete(budget)
        db.session.commit()
        flash('Budget deleted successfully!')
    except:
        flash('Something went wrong. Please try again.')

    return redirect(url_for('budgets', month=month, year=year))


@app.route('/categories')
def categories():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    user_id = session['user_id']
    expense_categories = Category.query.filter_by(user_id=user_id, type='expense').all()
    income_categories = Category.query.filter_by(user_id=user_id, type='income').all()

    return render_template('categories.html',
                           expense_categories=expense_categories,
                           income_categories=income_categories)


@app.route('/categories/add', methods=['POST'])
def add_category():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    name = request.form['name']
    category_type = request.form['type']
    user_id = session['user_id']

    # Check if category exists
    existing = Category.query.filter_by(
        name=name,
        type=category_type,
        user_id=user_id
    ).first()

    if existing:
        flash(f'Category "{name}" already exists!')
        return redirect(url_for('categories'))

    new_category = Category(
        name=name,
        type=category_type,
        user_id=user_id
    )

    try:
        db.session.add(new_category)
        db.session.commit()
        flash(f'Category "{name}" added successfully!')
    except:
        db.session.rollback()
        flash('Something went wrong. Please try again.')

    return redirect(url_for('categories'))


@app.route('/categories/delete/<int:id>')
def delete_category(id):
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    category = Category.query.get_or_404(id)

    # Make sure it belongs to the current user
    if category.user_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('categories'))

    # Check if category is in use
    if category.type == 'expense':
        in_use = Expense.query.filter_by(category=category.name, user_id=session['user_id']).first()
    else:
        in_use = Income.query.filter_by(source=category.name, user_id=session['user_id']).first()

    if in_use:
        flash(f'Cannot delete category "{category.name}" as it is in use.')
        return redirect(url_for('categories'))

    try:
        db.session.delete(category)
        db.session.commit()
        flash(f'Category "{category.name}" deleted successfully!')
    except:
        db.session.rollback()
        flash('Something went wrong. Please try again.')

    return redirect(url_for('categories'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
