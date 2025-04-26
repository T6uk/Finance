# routes/dashboard.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta
from ..extensions import db
from ..models import Expense, Income, SavingsGoal, Budget

dashboard_bp = Blueprint('dashboard', __name__)
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