# routes/recurring.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta
from extensions import db
from models import RecurringTransaction, Expense, Income
from utils import calculate_next_date
from collections import namedtuple

recurring_bp = Blueprint('recurring', __name__)


@recurring_bp.route('/recurring')
def recurring_transactions():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    recurring = RecurringTransaction.query.filter_by(user_id=user_id).order_by(RecurringTransaction.next_date).all()

    # Calculate recurring statistics
    recurring_stats = calculate_recurring_stats(recurring)

    # Generate upcoming transactions for the next 30 days
    upcoming_transactions = generate_upcoming_transactions(recurring, days=30)

    return render_template('recurring.html',
                           recurring=recurring,
                           recurring_stats=recurring_stats,
                           upcoming_transactions=upcoming_transactions)


def calculate_recurring_stats(recurring_transactions):
    """Calculate statistics for recurring transactions"""
    stats = {
        'expenses': {'count': 0, 'amount': 0},
        'income': {'count': 0, 'amount': 0}
    }

    # Calculate monthly amounts for each recurring transaction
    for transaction in recurring_transactions:
        monthly_amount = calculate_monthly_amount(transaction)

        if transaction.type == 'expense':
            stats['expenses']['count'] += 1
            stats['expenses']['amount'] += monthly_amount
        else:
            stats['income']['count'] += 1
            stats['income']['amount'] += monthly_amount

    return stats


def calculate_monthly_amount(transaction):
    """Calculate the monthly equivalent amount for a recurring transaction"""
    amount = transaction.amount

    if transaction.frequency == 'daily':
        # Approximate 30 days per month
        return amount * 30
    elif transaction.frequency == 'weekly':
        # Approximate 4.33 weeks per month
        return amount * 4.33
    elif transaction.frequency == 'monthly':
        # Already monthly
        return amount
    elif transaction.frequency == 'yearly':
        # Divide by 12 for monthly amount
        return amount / 12

    return amount


def generate_upcoming_transactions(recurring_transactions, days=30):
    """Generate a list of upcoming transactions for the next N days"""
    UpcomingTransaction = namedtuple('UpcomingTransaction',
                                     ['date', 'type', 'category', 'amount', 'description', 'frequency'])

    upcoming = []
    today = datetime.now()
    end_date = today + timedelta(days=days)

    for transaction in recurring_transactions:
        # Skip if transaction has an end date before today
        if transaction.end_date and transaction.end_date < today:
            continue

        # Start with the next occurrence
        current_date = transaction.next_date

        # Add all occurrences within the period
        while current_date <= end_date:
            upcoming.append(UpcomingTransaction(
                date=current_date,
                type=transaction.type,
                category=transaction.category,
                amount=transaction.amount,
                description=transaction.description,
                frequency=transaction.frequency
            ))

            # Calculate next occurrence date
            if transaction.frequency == 'daily':
                current_date += timedelta(days=1)
            elif transaction.frequency == 'weekly':
                current_date += timedelta(days=7)
            elif transaction.frequency == 'monthly':
                # Move to next month (same day)
                month = current_date.month % 12 + 1
                year = current_date.year + (1 if current_date.month == 12 else 0)
                day = min(current_date.day, get_days_in_month(year, month))
                current_date = datetime(year, month, day)
            elif transaction.frequency == 'yearly':
                # Move to next year (same month and day if possible)
                try:
                    current_date = datetime(current_date.year + 1, current_date.month, current_date.day)
                except ValueError:  # Handle Feb 29 in leap years
                    current_date = datetime(current_date.year + 1, current_date.month, 28)

    # Sort by date
    upcoming.sort(key=lambda x: x.date)
    return upcoming


def get_days_in_month(year, month):
    """Get the number of days in a month, accounting for leap years"""
    if month == 2:  # February
        if (year % 4 == 0 and year % 100 != 0) or year % 400 == 0:
            return 29  # Leap year
        else:
            return 28
    elif month in [4, 6, 9, 11]:  # April, June, September, November
        return 30
    else:
        return 31


@recurring_bp.route('/recurring/add', methods=['POST'])
def add_recurring():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

    type = request.form['type']
    amount = float(request.form['amount'])
    category = request.form['category']
    description = request.form['description']
    frequency = request.form['frequency']
    start_date_str = request.form['start_date']
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date_str = request.form.get('end_date', '')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None

    # Calculate next date based on frequency and start date
    next_date = calculate_next_date(start_date, frequency)

    new_recurring = RecurringTransaction(
        type=type,
        amount=amount,
        category=category,
        description=description,
        frequency=frequency,
        start_date=start_date,
        end_date=end_date,
        next_date=next_date,
        user_id=session['user_id']
    )

    try:
        db.session.add(new_recurring)
        db.session.commit()
        flash('Recurring transaction added successfully!')
    except Exception as e:
        db.session.rollback()
        flash(f'Something went wrong: {str(e)}')

    return redirect(url_for('recurring.recurring_transactions'))


@recurring_bp.route('/recurring/edit/<int:id>', methods=['GET', 'POST'])
def edit_recurring(id):
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

    recurring = RecurringTransaction.query.get_or_404(id)

    # Make sure the recurring transaction belongs to the logged-in user
    if recurring.user_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('recurring.recurring_transactions'))

    if request.method == 'POST':
        recurring.type = request.form['type']
        recurring.amount = float(request.form['amount'])
        recurring.category = request.form['category']
        recurring.description = request.form['description']
        recurring.frequency = request.form['frequency']

        start_date_str = request.form['start_date']
        recurring.start_date = datetime.strptime(start_date_str, '%Y-%m-%d')

        end_date_str = request.form.get('end_date', '')
        recurring.end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None

        # Recalculate next date if needed
        if recurring.next_date < datetime.now():
            recurring.next_date = calculate_next_date(recurring.start_date, recurring.frequency)

        try:
            db.session.commit()
            flash('Recurring transaction updated successfully!')
            return redirect(url_for('recurring.recurring_transactions'))
        except Exception as e:
            db.session.rollback()
            flash(f'Something went wrong: {str(e)}')

    return render_template('edit_recurring.html', recurring=recurring)


@recurring_bp.route('/recurring/delete/<int:id>')
def delete_recurring(id):
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

    recurring = RecurringTransaction.query.get_or_404(id)

    # Make sure the recurring transaction belongs to the logged-in user
    if recurring.user_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('recurring.recurring_transactions'))

    try:
        db.session.delete(recurring)
        db.session.commit()
        flash('Recurring transaction deleted successfully!')
    except Exception as e:
        db.session.rollback()
        flash(f'Something went wrong: {str(e)}')

    return redirect(url_for('recurring.recurring_transactions'))


@recurring_bp.route('/process_recurring_transactions')
def process_recurring_transactions():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

    today = datetime.now()
    recurring_transactions = RecurringTransaction.query.filter(
        RecurringTransaction.next_date <= today
    ).all()

    transactions_created = 0

    for transaction in recurring_transactions:
        # Skip if end date is set and we've passed it
        if transaction.end_date and transaction.end_date < today:
            continue

        # Create the appropriate transaction type
        if transaction.type == 'expense':
            new_transaction = Expense(
                amount=transaction.amount,
                category=transaction.category,
                description=transaction.description,
                date=transaction.next_date,
                user_id=transaction.user_id
            )
        else:  # income
            new_transaction = Income(
                amount=transaction.amount,
                source=transaction.category,
                description=transaction.description,
                date=transaction.next_date,
                user_id=transaction.user_id
            )

        db.session.add(new_transaction)

        # Update next date for the recurring transaction
        transaction.last_created = transaction.next_date
        transaction.next_date = calculate_next_date(transaction.next_date, transaction.frequency)

        transactions_created += 1

    try:
        db.session.commit()
        if transactions_created > 0:
            flash(f'Successfully created {transactions_created} transactions!')
        else:
            flash('No transactions were due for processing.')
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing recurring transactions: {str(e)}')

    return redirect(url_for('recurring.recurring_transactions'))