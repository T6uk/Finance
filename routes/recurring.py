# routes/recurring.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from extensions import db
from models import RecurringTransaction, Expense, Income
from utils import calculate_next_date

recurring_bp = Blueprint('recurring', __name__)
@recurring_bp.route('/recurring')
def recurring_transactions():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    user_id = session['user_id']
    recurring = RecurringTransaction.query.filter_by(user_id=user_id).all()
    return render_template('recurring.html', recurring=recurring)


@recurring_bp.route('/recurring/add', methods=['GET', 'POST'])
def add_recurring():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    if request.method == 'POST':
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
            return redirect(url_for('recurring_transactions'))
        except:
            flash('Something went wrong. Please try again.')

    return render_template('add_recurring.html')


@recurring_bp.route('/recurring/edit/<int:id>', methods=['GET', 'POST'])
def edit_recurring(id):
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    recurring = RecurringTransaction.query.get_or_404(id)

    # Make sure the recurring transaction belongs to the logged-in user
    if recurring.user_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('recurring_transactions'))

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
            return redirect(url_for('recurring_transactions'))
        except:
            flash('Something went wrong. Please try again.')

    return render_template('edit_recurring.html', recurring=recurring)


@recurring_bp.route('/recurring/delete/<int:id>')
def delete_recurring(id):
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    recurring = RecurringTransaction.query.get_or_404(id)

    # Make sure the recurring transaction belongs to the logged-in user
    if recurring.user_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('recurring_transactions'))

    try:
        db.session.delete(recurring)
        db.session.commit()
        flash('Recurring transaction deleted successfully!')
    except:
        flash('Something went wrong. Please try again.')

    return redirect(url_for('recurring_transactions'))


@recurring_bp.route('/process_recurring_transactions')
def process_recurring_transactions():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

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
        flash(f'Successfully created {transactions_created} transactions.')
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing recurring transactions: {str(e)}')

    return redirect(url_for('recurring_transactions'))