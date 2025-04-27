# routes/savings.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from extensions import db
from models import SavingsGoal

savings_bp = Blueprint('savings', __name__)


@savings_bp.route('/savings')
def savings():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    savings_goals = SavingsGoal.query.filter_by(user_id=user_id).all()

    # Calculate summary statistics
    total_saved = sum(goal.current_amount for goal in savings_goals)
    total_target = sum(goal.target_amount for goal in savings_goals)
    total_remaining = total_target - total_saved

    # Calculate overall progress percentage
    overall_progress = (total_saved / total_target * 100) if total_target > 0 else 0

    return render_template('savings.html',
                           savings_goals=savings_goals,
                           total_saved=total_saved,
                           total_remaining=total_remaining,
                           overall_progress=overall_progress)


@savings_bp.route('/savings/add', methods=['GET', 'POST'])
def add_savings_goal():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

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
            return redirect(url_for('savings.savings'))
        except:
            flash('Something went wrong. Please try again.')

    return render_template('add_savings_goal.html')


@savings_bp.route('/savings/edit/<int:id>', methods=['GET', 'POST'])
def edit_savings_goal(id):
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

    savings_goal = SavingsGoal.query.get_or_404(id)

    # Make sure the savings goal belongs to the logged-in user
    if savings_goal.user_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('savings.savings'))

    if request.method == 'POST':
        savings_goal.name = request.form['name']
        savings_goal.target_amount = float(request.form['target_amount'])
        savings_goal.current_amount = float(request.form['current_amount'])

        target_date_str = request.form['target_date']
        savings_goal.target_date = datetime.strptime(target_date_str, '%Y-%m-%d') if target_date_str else None

        try:
            db.session.commit()
            flash('Savings goal updated successfully!')
            return redirect(url_for('savings.savings'))
        except:
            flash('Something went wrong. Please try again.')

    return render_template('edit_savings_goal.html', goal=savings_goal)


@savings_bp.route('/savings/update/<int:id>', methods=['POST'])
def update_savings_progress(id):
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

    savings_goal = SavingsGoal.query.get_or_404(id)

    # Make sure the savings goal belongs to the logged-in user
    if savings_goal.user_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('savings.savings'))

    if request.method == 'POST':
        amount = float(request.form['amount'])
        savings_goal.current_amount += amount

        try:
            db.session.commit()
            flash('Savings progress updated successfully!')
        except:
            flash('Something went wrong. Please try again.')

    return redirect(url_for('savings.savings'))


@savings_bp.route('/savings/delete/<int:id>')
def delete_savings_goal(id):
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

    savings_goal = SavingsGoal.query.get_or_404(id)

    # Make sure the savings goal belongs to the logged-in user
    if savings_goal.user_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('savings.savings'))

    try:
        db.session.delete(savings_goal)
        db.session.commit()
        flash('Savings goal deleted successfully!')
    except:
        flash('Something went wrong. Please try again.')

    return redirect(url_for('savings.savings'))