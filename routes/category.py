# routes/category.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from extensions import db
from models import Category, Expense, Income
from sqlalchemy import func

category_bp = Blueprint('category', __name__)


@category_bp.route('/categories')
def categories():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    expense_categories = Category.query.filter_by(user_id=user_id, type='expense').all()
    income_categories = Category.query.filter_by(user_id=user_id, type='income').all()

    # Get category usage statistics
    expense_stats = {}
    income_stats = {}

    # Query expense counts by category
    expense_counts = db.session.query(
        Expense.category, func.count(Expense.id)
    ).filter_by(user_id=user_id).group_by(Expense.category).all()

    for category, count in expense_counts:
        expense_stats[category] = {'count': count}

    # Query income counts by category/source
    income_counts = db.session.query(
        Income.source, func.count(Income.id)
    ).filter_by(user_id=user_id).group_by(Income.source).all()

    for source, count in income_counts:
        income_stats[source] = {'count': count}

    # Add a template helper for icon selection based on category name
    def get_category_icon(name):
        name = name.lower()

        # Define some common mappings
        if 'food' in name or 'dining' in name or 'restaurant' in name or 'grocery' in name:
            return 'bi-egg-fried'
        elif 'transport' in name or 'car' in name or 'gas' in name or 'fuel' in name:
            return 'bi-car-front'
        elif 'home' in name or 'house' in name or 'rent' in name or 'mortgage' in name:
            return 'bi-house-door'
        elif 'utilities' in name or 'electric' in name or 'water' in name or 'gas' in name:
            return 'bi-lightbulb'
        elif 'entertain' in name or 'fun' in name or 'movie' in name or 'game' in name:
            return 'bi-controller'
        elif 'shop' in name or 'retail' in name or 'clothes' in name:
            return 'bi-bag'
        elif 'health' in name or 'medical' in name or 'doctor' in name:
            return 'bi-hospital'
        elif 'education' in name or 'school' in name or 'college' in name or 'book' in name:
            return 'bi-mortarboard'
        elif 'travel' in name or 'vacation' in name or 'holiday' in name:
            return 'bi-airplane'
        elif 'salary' in name or 'wage' in name or 'pay' in name:
            return 'bi-briefcase'
        elif 'freelance' in name or 'contract' in name:
            return 'bi-laptop'
        elif 'business' in name:
            return 'bi-shop'
        elif 'invest' in name or 'dividend' in name or 'stock' in name:
            return 'bi-graph-up-arrow'
        elif 'gift' in name or 'present' in name:
            return 'bi-gift'
        else:
            return 'bi-tag'

    return render_template('categories.html',
                           expense_categories=expense_categories,
                           income_categories=income_categories,
                           expense_stats=expense_stats,
                           income_stats=income_stats,
                           get_category_icon=get_category_icon)


@category_bp.route('/categories/add', methods=['POST'])
def add_category():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

    name = request.form['name']
    category_type = request.form['type']
    category_id = request.form.get('id', '')
    icon = request.form.get('icon', 'bi-tag')
    user_id = session['user_id']

    if category_id:
        # Update existing category
        category = Category.query.get(int(category_id))

        # Make sure the category belongs to the current user
        if category and category.user_id == user_id:
            category.name = name
            category.type = category_type
            # Store icon if we add that field to the model

            flash(f'Category "{name}" updated successfully!')
        else:
            flash('Category not found or unauthorized.')
            return redirect(url_for('category.categories'))
    else:
        # Check if category exists
        existing = Category.query.filter_by(
            name=name,
            type=category_type,
            user_id=user_id
        ).first()

        if existing:
            flash(f'Category "{name}" already exists!')
            return redirect(url_for('category.categories'))

        # Create new category
        new_category = Category(
            name=name,
            type=category_type,
            user_id=user_id
        )
        db.session.add(new_category)
        flash(f'Category "{name}" added successfully!')

    try:
        db.session.commit()
    except:
        db.session.rollback()
        flash('Something went wrong. Please try again.')

    return redirect(url_for('category.categories'))


@category_bp.route('/categories/delete/<int:id>')
def delete_category(id):
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('auth.login'))

    category = Category.query.get_or_404(id)

    # Make sure it belongs to the current user
    if category.user_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('category.categories'))

    # Check if category is in use
    if category.type == 'expense':
        in_use = Expense.query.filter_by(category=category.name, user_id=session['user_id']).first()
    else:
        in_use = Income.query.filter_by(source=category.name, user_id=session['user_id']).first()

    if in_use:
        flash(f'Cannot delete category "{category.name}" as it is in use.')
        return redirect(url_for('category.categories'))

    try:
        db.session.delete(category)
        db.session.commit()
        flash(f'Category "{category.name}" deleted successfully!')
    except:
        db.session.rollback()
        flash('Something went wrong. Please try again.')

    return redirect(url_for('category.categories'))


@category_bp.route('/categories/stats', methods=['GET'])
def category_stats():
    """API endpoint to get category usage statistics"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']

    # Get expense stats
    expense_stats = db.session.query(
        Expense.category,
        func.count(Expense.id).label('count'),
        func.sum(Expense.amount).label('total')
    ).filter_by(user_id=user_id).group_by(Expense.category).all()

    # Get income stats
    income_stats = db.session.query(
        Income.source,
        func.count(Income.id).label('count'),
        func.sum(Income.amount).label('total')
    ).filter_by(user_id=user_id).group_by(Income.source).all()

    # Format the results
    result = {
        'expense': {cat: {'count': count, 'total': float(total)} for cat, count, total in expense_stats},
        'income': {src: {'count': count, 'total': float(total)} for src, count, total in income_stats}
    }

    return jsonify(result)