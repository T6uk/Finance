
# routes/budget.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from ..extensions import db
from ..models import Budget, Expense

budget_bp = Blueprint('budget', __name__)

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