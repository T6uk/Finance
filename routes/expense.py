# routes/expense.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta
from extensions import db
from models import Expense
from sqlalchemy import func

expense_bp = Blueprint('expense', __name__)


@expense_bp.route('/expenses')
def expenses():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

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

    # Calculate expense statistics for the current month
    today = datetime.now()
    start_of_month = datetime(today.year, today.month, 1)
    if today.month == 12:
        end_of_month = datetime(today.year + 1, 1, 1)
    else:
        end_of_month = datetime(today.year, today.month + 1, 1)

    # Monthly total
    month_expenses = Expense.query.filter_by(user_id=user_id).filter(
        Expense.date >= start_of_month,
        Expense.date < end_of_month
    ).all()
    monthly_total = sum(expense.amount for expense in month_expenses)

    # Daily average
    days_in_month = (end_of_month - start_of_month).days
    days_passed = min((today - start_of_month).days + 1, days_in_month)
    daily_avg = monthly_total / days_passed if days_passed > 0 else 0

    # Top category
    category_totals = {}
    for expense in month_expenses:
        if expense.category in category_totals:
            category_totals[expense.category] += expense.amount
        else:
            category_totals[expense.category] = expense.amount

    top_category = max(category_totals.items(), key=lambda x: x[1])[0] if category_totals else "None"

    return render_template('expenses.html',
                           expenses=expenses,
                           categories=categories,
                           filter_category=category,
                           filter_min_amount=min_amount,
                           filter_max_amount=max_amount,
                           filter_start_date=start_date,
                           filter_end_date=end_date,
                           filter_search=search_term,
                           monthly_total=monthly_total,
                           daily_avg=daily_avg,
                           top_category=top_category)


@expense_bp.route('/expenses/add', methods=['POST'])
def add_expense():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

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
    except:
        db.session.rollback()
        flash('Something went wrong. Please try again.')

    return redirect(url_for('expense.expenses'))


@expense_bp.route('/expenses/edit/<int:id>', methods=['GET', 'POST'])
def edit_expense(id):
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

    expense = Expense.query.get_or_404(id)

    # Make sure the expense belongs to the logged-in user
    if expense.user_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('expense.expenses'))

    if request.method == 'POST':
        expense.amount = float(request.form['amount'])
        expense.category = request.form['category']
        expense.description = request.form['description']
        date_str = request.form['date']
        expense.date = datetime.strptime(date_str, '%Y-%m-%d')

        try:
            db.session.commit()
            flash('Expense updated successfully!')
            return redirect(url_for('expense.expenses'))
        except:
            flash('Something went wrong. Please try again.')

    return render_template('edit_expense.html', expense=expense)


@expense_bp.route('/expenses/delete/<int:id>')
def delete_expense(id):
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

    expense = Expense.query.get_or_404(id)

    # Make sure the expense belongs to the logged-in user
    if expense.user_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('expense.expenses'))

    try:
        db.session.delete(expense)
        db.session.commit()
        flash('Expense deleted successfully!')
    except:
        flash('Something went wrong. Please try again.')

    return redirect(url_for('expense.expenses'))