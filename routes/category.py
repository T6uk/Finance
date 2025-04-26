
# routes/category.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..extensions import db
from ..models import Category, Expense, Income

category_bp = Blueprint('category', __name__)

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