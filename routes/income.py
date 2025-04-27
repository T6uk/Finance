# routes/income.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta
from sqlalchemy import func, extract
from extensions import db
from models import Income

income_bp = Blueprint('income', __name__)


@income_bp.route('/incomes')
def incomes():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    # Get filter parameters
    source = request.args.get('source')
    min_amount = request.args.get('min_amount', type=float)
    max_amount = request.args.get('max_amount', type=float)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search_term = request.args.get('search')

    # Base query
    query = Income.query.filter_by(user_id=user_id)

    # Apply filters if provided
    if source and source != 'all':
        query = query.filter_by(source=source)
    if min_amount:
        query = query.filter(Income.amount >= min_amount)
    if max_amount:
        query = query.filter(Income.amount <= max_amount)
    if start_date:
        query = query.filter(Income.date >= datetime.strptime(start_date, "%Y-%m-%d"))
    if end_date:
        query = query.filter(Income.date <= datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1))
    if search_term:
        query = query.filter(Income.description.contains(search_term))

    # Get sources for filter dropdown
    sources = db.session.query(Income.source).filter_by(user_id=user_id).distinct().all()
    sources = [src[0] for src in sources]

    # Execute query with order
    incomes = query.order_by(Income.date.desc()).all()

    # Calculate income statistics
    today = datetime.now()

    # This month's total
    start_of_month = datetime(today.year, today.month, 1)
    if today.month == 12:
        end_of_month = datetime(today.year + 1, 1, 1)
    else:
        end_of_month = datetime(today.year, today.month + 1, 1)

    month_incomes = Income.query.filter_by(user_id=user_id).filter(
        Income.date >= start_of_month,
        Income.date < end_of_month
    ).all()

    monthly_total = sum(income.amount for income in month_incomes)

    # Average monthly income (from the last 6 months)
    six_months_ago = datetime(today.year, today.month - 6, 1) if today.month > 6 else datetime(today.year - 1,
                                                                                               today.month + 6, 1)

    # Group by month and calculate average
    monthly_incomes = {}

    all_incomes = Income.query.filter_by(user_id=user_id).filter(Income.date >= six_months_ago).all()

    for income in all_incomes:
        month_key = f"{income.date.year}-{income.date.month}"
        if month_key in monthly_incomes:
            monthly_incomes[month_key] += income.amount
        else:
            monthly_incomes[month_key] = income.amount

    monthly_avg = sum(monthly_incomes.values()) / len(monthly_incomes) if monthly_incomes else 0

    # Top income source
    source_totals = {}
    for income in all_incomes:
        if income.source in source_totals:
            source_totals[income.source] += income.amount
        else:
            source_totals[income.source] = income.amount

    top_source = max(source_totals.items(), key=lambda x: x[1])[0] if source_totals else "None"

    return render_template('incomes.html',
                           incomes=incomes,
                           sources=sources,
                           filter_source=source,
                           filter_min_amount=min_amount,
                           filter_max_amount=max_amount,
                           filter_start_date=start_date,
                           filter_end_date=end_date,
                           filter_search=search_term,
                           monthly_total=monthly_total,
                           monthly_avg=monthly_avg,
                           top_source=top_source)


@income_bp.route('/incomes/add', methods=['POST'])
def add_income():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

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
    except:
        db.session.rollback()
        flash('Something went wrong. Please try again.')

    return redirect(url_for('income.incomes'))


@income_bp.route('/incomes/edit/<int:id>', methods=['GET', 'POST'])
def edit_income(id):
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

    income = Income.query.get_or_404(id)

    # Make sure the income entry belongs to the logged-in user
    if income.user_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('income.incomes'))

    if request.method == 'POST':
        income.amount = float(request.form['amount'])
        income.source = request.form['source']
        income.description = request.form['description']
        date_str = request.form['date']
        income.date = datetime.strptime(date_str, '%Y-%m-%d')

        try:
            db.session.commit()
            flash('Income updated successfully!')
            return redirect(url_for('income.incomes'))
        except:
            flash('Something went wrong. Please try again.')

    return render_template('edit_income.html', income=income)


@income_bp.route('/incomes/delete/<int:id>')
def delete_income(id):
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

    income = Income.query.get_or_404(id)

    # Make sure the income entry belongs to the logged-in user
    if income.user_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('income.incomes'))

    try:
        db.session.delete(income)
        db.session.commit()
        flash('Income deleted successfully!')
    except:
        flash('Something went wrong. Please try again.')

    return redirect(url_for('income.incomes'))