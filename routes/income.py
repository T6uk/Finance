from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from ..extensions import db
from ..models import Income

income_bp = Blueprint('income', __name__)

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